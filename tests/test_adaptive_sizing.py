import math
import pytest

from daybot_mcp.risk import RiskManager
from daybot_mcp.config import settings


def test_volatility_sizing_low_and_high_atr():
    rm = RiskManager()
    portfolio_value = 100_000.0
    entry_price = 100.0

    # Low volatility: ATR% = 0.5%
    result_low = rm.shares_for_trade(
        symbol="TEST",
        entry_price=entry_price,
        portfolio_value=portfolio_value,
        atr_value=0.5,
        sizing_mode="volatility",
    )
    assert result_low.effective_risk_percent is not None
    # Expect up-weight vs base risk (default 1.2x)
    assert result_low.effective_risk_percent == pytest.approx(settings.default_risk_per_trade * settings.low_volatility_multiplier, rel=1e-3)

    # High volatility: ATR% = 5%
    result_high = rm.shares_for_trade(
        symbol="TEST",
        entry_price=entry_price,
        portfolio_value=portfolio_value,
        atr_value=5.0,
        sizing_mode="volatility",
    )
    assert result_high.effective_risk_percent == pytest.approx(settings.default_risk_per_trade * settings.high_volatility_multiplier, rel=1e-3)


def test_conviction_sizing_scaling():
    rm = RiskManager()
    pv = 100_000.0
    ep = 100.0

    # Minimum conviction -> min multiplier
    res_min = rm.shares_for_trade(
        symbol="TEST",
        entry_price=ep,
        portfolio_value=pv,
        sizing_mode="conviction",
        conviction_score=0.0,
    )
    assert res_min.effective_risk_percent == pytest.approx(
        settings.default_risk_per_trade * settings.conviction_min_multiplier, rel=1e-3
    )

    # Maximum conviction -> max multiplier
    res_max = rm.shares_for_trade(
        symbol="TEST",
        entry_price=ep,
        portfolio_value=pv,
        sizing_mode="conviction",
        conviction_score=1.0,
    )
    assert res_max.effective_risk_percent == pytest.approx(
        settings.default_risk_per_trade * settings.conviction_max_multiplier, rel=1e-3
    )


def test_kelly_sizing_fractional_and_ceiling():
    rm = RiskManager()
    pv = 100_000.0
    ep = 100.0

    # Kelly inputs that would yield > risk_ceiling after fractional multiplier -> expect ceiling
    kelly_params = {"win_rate": 60.0, "avg_win": 120.0, "avg_loss": -80.0}
    res_kelly = rm.shares_for_trade(
        symbol="TEST",
        entry_price=ep,
        portfolio_value=pv,
        sizing_mode="kelly",
        kelly_params=kelly_params,
    )
    assert res_kelly.effective_risk_percent == pytest.approx(settings.risk_ceiling, rel=1e-6)


def test_hybrid_sizing_blend_and_ceiling():
    rm = RiskManager()
    pv = 100_000.0
    ep = 100.0

    # Low vol and high conviction with strong Kelly -> blended result should hit ceiling
    kelly_params = {"win_rate": 60.0, "avg_win": 120.0, "avg_loss": -80.0}
    res_hybrid = rm.shares_for_trade(
        symbol="TEST",
        entry_price=ep,
        portfolio_value=pv,
        atr_value=0.5,  # low vol -> up-weight
        sizing_mode="hybrid",
        conviction_score=1.0,
        kelly_params=kelly_params,
    )
    assert res_hybrid.effective_risk_percent == pytest.approx(settings.risk_ceiling, rel=1e-6)
