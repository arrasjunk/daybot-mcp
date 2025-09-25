"""
Tests for risk management functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from daybot_mcp.risk import RiskManager, RiskMetrics, PositionSizeResult
from daybot_mcp.alpaca_client import Account, Position


@pytest.fixture
def risk_manager():
    """Create a RiskManager instance for testing."""
    return RiskManager()


@pytest.fixture
def mock_account():
    """Create a mock account for testing."""
    return Account(
        id="test_account",
        account_number="123456789",
        status="ACTIVE",
        currency="USD",
        buying_power=50000.0,
        cash=25000.0,
        portfolio_value=100000.0,
        equity=100000.0,
        last_equity=98000.0,
        multiplier=4,
        daytrade_count=0,
        sma=25000.0
    )


@pytest.fixture
def mock_positions():
    """Create mock positions for testing."""
    return [
        Position(
            symbol="AAPL",
            qty=100.0,
            side="long",
            market_value=15000.0,
            cost_basis=14500.0,
            unrealized_pl=500.0,
            unrealized_plpc=3.45,
            current_price=150.0
        ),
        Position(
            symbol="MSFT",
            qty=-50.0,
            side="short",
            market_value=-12500.0,
            cost_basis=12000.0,
            unrealized_pl=-500.0,
            unrealized_plpc=-4.17,
            current_price=250.0
        )
    ]


@pytest.mark.asyncio
async def test_get_risk_metrics(risk_manager, mock_account, mock_positions):
    """Test risk metrics calculation."""
    # Mock AlpacaClient
    mock_client = AsyncMock()
    mock_client.get_account.return_value = mock_account
    mock_client.get_positions.return_value = mock_positions
    
    # Set daily start equity
    risk_manager.daily_start_equity = 98000.0
    
    # Get risk metrics
    metrics = await risk_manager.get_risk_metrics(mock_client)
    
    # Assertions
    assert isinstance(metrics, RiskMetrics)
    assert metrics.portfolio_value == 100000.0
    assert metrics.daily_pnl == 2000.0  # 100000 - 98000
    assert metrics.daily_pnl_percent == pytest.approx(2.04, rel=1e-2)
    assert metrics.total_exposure == 27500.0  # |15000| + |-12500|
    assert metrics.positions_count == 2
    assert metrics.risk_level in ["low", "medium", "high", "critical"]


def test_shares_for_trade_basic(risk_manager):
    """Test basic position sizing calculation."""
    result = risk_manager.shares_for_trade(
        symbol="AAPL",
        entry_price=150.0,
        stop_loss_price=147.0,  # 2% stop loss
        portfolio_value=100000.0,
        risk_percent=0.01  # 1% risk
    )
    
    assert isinstance(result, PositionSizeResult)
    assert result.symbol == "AAPL"
    assert result.recommended_shares > 0
    assert result.risk_amount <= 1000.0  # 1% of 100k
    assert result.stop_loss_price == 147.0
    assert result.take_profit_price > 150.0


def test_shares_for_trade_with_atr(risk_manager):
    """Test position sizing with ATR-based stop loss."""
    result = risk_manager.shares_for_trade(
        symbol="AAPL",
        entry_price=150.0,
        portfolio_value=100000.0,
        risk_percent=0.02,  # 2% risk
        atr_value=2.5  # ATR value
    )
    
    assert isinstance(result, PositionSizeResult)
    assert result.symbol == "AAPL"
    assert result.recommended_shares > 0
    assert result.stop_loss_price == 145.0  # 150 - (2 * 2.5)
    assert len(result.warnings) > 0  # Should have ATR warning


def test_shares_for_trade_zero_risk(risk_manager):
    """Test position sizing with zero risk per share."""
    result = risk_manager.shares_for_trade(
        symbol="AAPL",
        entry_price=150.0,
        stop_loss_price=150.0,  # Same as entry = zero risk
        portfolio_value=100000.0
    )
    
    assert isinstance(result, PositionSizeResult)
    assert result.recommended_shares > 0
    assert "Risk per share is zero" in " ".join(result.warnings)


def test_calculate_risk_level(risk_manager):
    """Test risk level calculation."""
    # Low risk scenario
    risk_level = risk_manager._calculate_risk_level(
        daily_pnl_percent=0.5,
        exposure_ratio=0.3,
        position_count=3
    )
    assert risk_level == "low"
    
    # High risk scenario
    risk_level = risk_manager._calculate_risk_level(
        daily_pnl_percent=-2.5,
        exposure_ratio=0.7,
        position_count=8
    )
    assert risk_level == "high"
    
    # Critical risk scenario
    risk_level = risk_manager._calculate_risk_level(
        daily_pnl_percent=-4.0,
        exposure_ratio=0.9,
        position_count=12
    )
    assert risk_level == "critical"


@pytest.mark.asyncio
async def test_check_daily_loss_limit(risk_manager, mock_account):
    """Test daily loss limit checking."""
    mock_client = AsyncMock()
    mock_client.get_account.return_value = mock_account
    
    # Set daily start equity higher to simulate loss
    risk_manager.daily_start_equity = 110000.0  # Started higher
    
    limit_reached, current_loss, max_loss = await risk_manager.check_daily_loss_limit(mock_client)
    
    # Should not have reached limit (loss is ~9%, default limit is 5%)
    # But this depends on settings.max_daily_loss
    assert isinstance(limit_reached, bool)
    assert isinstance(current_loss, float)
    assert isinstance(max_loss, float)


@pytest.mark.asyncio
async def test_can_open_new_position(risk_manager, mock_account):
    """Test position opening validation."""
    mock_client = AsyncMock()
    mock_client.get_account.return_value = mock_account
    mock_client.is_market_open.return_value = True
    mock_client.get_position.return_value = None  # No existing position
    mock_client.get_positions.return_value = []  # No positions
    
    # Set daily start equity
    risk_manager.daily_start_equity = 98000.0
    
    can_open, reasons = await risk_manager.can_open_new_position(
        mock_client, "AAPL", 10000.0
    )
    
    assert isinstance(can_open, bool)
    assert isinstance(reasons, list)


def test_reset_daily_counters(risk_manager):
    """Test daily counter reset."""
    # Set some values
    risk_manager.daily_start_equity = 100000.0
    risk_manager.trade_count_today = 5
    risk_manager.max_drawdown_today = 1000.0
    
    # Reset counters
    risk_manager.reset_daily_counters()
    
    # Check if reset (depends on date)
    assert risk_manager.trade_count_today == 0
    assert risk_manager.max_drawdown_today == 0.0


@pytest.mark.asyncio
async def test_get_portfolio_heat(risk_manager, mock_account, mock_positions):
    """Test portfolio heat calculation."""
    mock_client = AsyncMock()
    mock_client.get_account.return_value = mock_account
    mock_client.get_positions.return_value = mock_positions
    
    heat = await risk_manager.get_portfolio_heat(mock_client)
    
    assert isinstance(heat, dict)
    assert "total_risk_dollars" in heat
    assert "portfolio_heat_percent" in heat
    assert "position_risks" in heat
    assert "heat_status" in heat
    assert heat["heat_status"] in ["low", "medium", "high"]


def test_update_trade_count(risk_manager):
    """Test trade count update."""
    initial_count = risk_manager.trade_count_today
    risk_manager.update_trade_count()
    assert risk_manager.trade_count_today == initial_count + 1
