"""
Tests for position closing functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from daybot_mcp.utils import (
    close_with_verification,
    cancel_symbol_orders,
    flatten_all_positions,
    CloseResult
)
from daybot_mcp.alpaca_client import Position, Order


@pytest.fixture
def mock_position():
    """Create a mock position for testing."""
    return Position(
        symbol="AAPL",
        qty=100.0,
        side="long",
        market_value=15000.0,
        cost_basis=14500.0,
        unrealized_pl=500.0,
        unrealized_plpc=3.45,
        current_price=150.0
    )


@pytest.fixture
def mock_order():
    """Create a mock order for testing."""
    return Order(
        id="order_123",
        symbol="AAPL",
        qty=100.0,
        side="sell",
        order_type="market",
        time_in_force="day",
        status="filled",
        filled_qty=100.0,
        filled_avg_price=150.50
    )


@pytest.fixture
def mock_orders():
    """Create mock orders for testing."""
    return [
        Order(
            id="order_1",
            symbol="AAPL",
            qty=100.0,
            side="sell",
            order_type="stop",
            time_in_force="day",
            status="open",
            stop_price=145.0
        ),
        Order(
            id="order_2",
            symbol="MSFT",
            qty=50.0,
            side="buy",
            order_type="limit",
            time_in_force="day",
            status="open",
            limit_price=250.0
        )
    ]


@pytest.mark.asyncio
async def test_close_with_verification_success(mock_position, mock_order):
    """Test successful position close with verification."""
    mock_client = AsyncMock()
    
    # Mock the sequence of calls
    mock_client.get_position.side_effect = [
        mock_position,  # Initial position
        None  # Position closed after order
    ]
    mock_client.get_orders.return_value = []  # No existing orders
    mock_client.close_position.return_value = mock_order
    mock_client.get_order.return_value = mock_order  # Order filled
    
    result = await close_with_verification(mock_client, "AAPL")
    
    assert isinstance(result, CloseResult)
    assert result.success is True
    assert result.symbol == "AAPL"
    assert result.initial_qty == 100.0
    assert result.closed_qty == 100.0
    assert result.remaining_qty == 0.0
    assert result.close_price == 150.50


@pytest.mark.asyncio
async def test_close_with_verification_no_position():
    """Test close attempt when no position exists."""
    mock_client = AsyncMock()
    mock_client.get_position.return_value = None
    
    result = await close_with_verification(mock_client, "AAPL")
    
    assert isinstance(result, CloseResult)
    assert result.success is False
    assert result.symbol == "AAPL"
    assert result.initial_qty == 0.0
    assert "No position found" in result.error_message


@pytest.mark.asyncio
async def test_close_with_verification_partial(mock_position):
    """Test partial position close."""
    mock_client = AsyncMock()
    
    # Create a partial position after close
    partial_position = Position(
        symbol="AAPL",
        qty=50.0,  # Half remaining
        side="long",
        market_value=7500.0,
        cost_basis=7250.0,
        unrealized_pl=250.0,
        unrealized_plpc=3.45,
        current_price=150.0
    )
    
    mock_order = Order(
        id="order_123",
        symbol="AAPL",
        qty=50.0,
        side="sell",
        order_type="market",
        time_in_force="day",
        status="filled",
        filled_qty=50.0,
        filled_avg_price=150.50
    )
    
    mock_client.get_position.side_effect = [
        mock_position,  # Initial position
        partial_position  # Partial position remaining
    ]
    mock_client.get_orders.return_value = []
    mock_client.close_position.return_value = mock_order
    mock_client.get_order.return_value = mock_order
    
    result = await close_with_verification(mock_client, "AAPL", qty=50.0)
    
    assert isinstance(result, CloseResult)
    assert result.success is True
    assert result.symbol == "AAPL"
    assert result.initial_qty == 100.0
    assert result.closed_qty == 50.0
    assert result.remaining_qty == 50.0


@pytest.mark.asyncio
async def test_close_with_verification_error(mock_position):
    """Test close with error during execution."""
    mock_client = AsyncMock()
    mock_client.get_position.return_value = mock_position
    mock_client.get_orders.return_value = []
    mock_client.close_position.side_effect = Exception("API Error")
    
    result = await close_with_verification(mock_client, "AAPL")
    
    assert isinstance(result, CloseResult)
    assert result.success is False
    assert result.symbol == "AAPL"
    assert result.initial_qty == 100.0
    assert result.closed_qty == 0.0
    assert "API Error" in result.error_message


@pytest.mark.asyncio
async def test_cancel_symbol_orders(mock_orders):
    """Test cancelling orders for a specific symbol."""
    mock_client = AsyncMock()
    mock_client.get_orders.return_value = mock_orders
    mock_client.cancel_order.return_value = True
    
    cancelled_count = await cancel_symbol_orders(mock_client, "AAPL")
    
    assert cancelled_count == 1  # Only one AAPL order
    mock_client.cancel_order.assert_called_once_with("order_1")


@pytest.mark.asyncio
async def test_cancel_symbol_orders_no_orders():
    """Test cancelling orders when none exist."""
    mock_client = AsyncMock()
    mock_client.get_orders.return_value = []
    
    cancelled_count = await cancel_symbol_orders(mock_client, "AAPL")
    
    assert cancelled_count == 0


@pytest.mark.asyncio
async def test_cancel_symbol_orders_error():
    """Test cancelling orders with API error."""
    mock_client = AsyncMock()
    mock_client.get_orders.side_effect = Exception("API Error")
    
    cancelled_count = await cancel_symbol_orders(mock_client, "AAPL")
    
    assert cancelled_count == 0


@pytest.mark.asyncio
async def test_flatten_all_positions_success():
    """Test successful flattening of all positions."""
    positions = [
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
    
    orders = [
        Order(
            id="order_1",
            symbol="AAPL",
            qty=100.0,
            side="sell",
            order_type="stop",
            time_in_force="day",
            status="open"
        )
    ]
    
    mock_client = AsyncMock()
    mock_client.get_positions.return_value = positions
    mock_client.get_orders.return_value = orders
    mock_client.cancel_all_orders.return_value = True
    
    # Mock close_with_verification results
    def mock_close_verification(client, symbol, qty=None):
        return CloseResult(
            symbol=symbol,
            success=True,
            initial_qty=100.0 if symbol == "AAPL" else 50.0,
            closed_qty=100.0 if symbol == "AAPL" else 50.0,
            remaining_qty=0.0,
            close_price=150.0 if symbol == "AAPL" else 250.0,
            orders_cancelled=0,
            verification_attempts=1,
            error_message=None,
            timestamp="2023-01-01T00:00:00Z"
        )
    
    # Patch the close_with_verification function
    import daybot_mcp.utils
    original_close = daybot_mcp.utils.close_with_verification
    daybot_mcp.utils.close_with_verification = mock_close_verification
    
    try:
        result = await flatten_all_positions(mock_client)
        
        assert result["success"] is True
        assert result["positions_closed"] == 2
        assert result["total_positions"] == 2
        assert result["orders_cancelled"] == 1
        assert len(result["close_results"]) == 2
    finally:
        # Restore original function
        daybot_mcp.utils.close_with_verification = original_close


@pytest.mark.asyncio
async def test_flatten_all_positions_error():
    """Test flattening positions with error."""
    mock_client = AsyncMock()
    mock_client.get_positions.side_effect = Exception("API Error")
    
    result = await flatten_all_positions(mock_client)
    
    assert result["success"] is False
    assert "API Error" in result["error"]
    assert result["positions_closed"] == 0


@pytest.mark.asyncio
async def test_flatten_all_positions_empty():
    """Test flattening when no positions exist."""
    mock_client = AsyncMock()
    mock_client.get_positions.return_value = []
    mock_client.get_orders.return_value = []
    mock_client.cancel_all_orders.return_value = True
    
    result = await flatten_all_positions(mock_client)
    
    assert result["success"] is True
    assert result["positions_closed"] == 0
    assert result["total_positions"] == 0
    assert result["orders_cancelled"] == 0
