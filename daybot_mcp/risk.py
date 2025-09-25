"""
Risk management and position sizing functions.
Handles portfolio risk, position sizing, and drawdown tracking.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

from .config import settings
from .alpaca_client import AlpacaClient, Account, Position


class RiskMetrics(BaseModel):
    """Risk metrics for the trading account."""
    portfolio_value: float
    cash_available: float
    buying_power: float
    total_exposure: float
    max_position_size_dollars: float
    daily_pnl: float
    daily_pnl_percent: float
    max_daily_loss_dollars: float
    positions_count: int
    risk_level: str  # "low", "medium", "high", "critical"


class PositionSizeResult(BaseModel):
    """Result of position sizing calculation."""
    symbol: str
    recommended_shares: int
    dollar_amount: float
    risk_amount: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    risk_reward_ratio: Optional[float]
    position_risk_percent: float
    warnings: List[str]


class RiskManager:
    """Manages risk and position sizing for the trading account."""
    
    def __init__(self):
        self.daily_start_equity: Optional[float] = None
        self.max_drawdown_today: float = 0.0
        self.trade_count_today: int = 0
        self.last_reset_date: Optional[str] = None
    
    async def get_risk_metrics(self, alpaca_client: AlpacaClient) -> RiskMetrics:
        """Calculate current risk metrics for the account."""
        account = await alpaca_client.get_account()
        positions = await alpaca_client.get_positions()
        
        # Calculate total exposure
        total_exposure = sum(abs(pos.market_value) for pos in positions)
        
        # Calculate daily P&L
        if self.daily_start_equity is None:
            self.daily_start_equity = account.last_equity
        
        daily_pnl = account.equity - self.daily_start_equity
        daily_pnl_percent = (daily_pnl / self.daily_start_equity) * 100 if self.daily_start_equity > 0 else 0
        
        # Calculate max position size
        max_position_size_dollars = account.portfolio_value * settings.max_position_size
        
        # Calculate max daily loss
        max_daily_loss_dollars = account.portfolio_value * settings.max_daily_loss
        
        # Determine risk level
        risk_level = self._calculate_risk_level(
            daily_pnl_percent,
            total_exposure / account.portfolio_value if account.portfolio_value > 0 else 0,
            len(positions)
        )
        
        return RiskMetrics(
            portfolio_value=account.portfolio_value,
            cash_available=account.cash,
            buying_power=account.buying_power,
            total_exposure=total_exposure,
            max_position_size_dollars=max_position_size_dollars,
            daily_pnl=daily_pnl,
            daily_pnl_percent=daily_pnl_percent,
            max_daily_loss_dollars=max_daily_loss_dollars,
            positions_count=len(positions),
            risk_level=risk_level
        )
    
    def _calculate_risk_level(self, daily_pnl_percent: float, exposure_ratio: float, position_count: int) -> str:
        """Calculate overall risk level based on various factors."""
        risk_score = 0
        
        # Daily P&L risk
        if daily_pnl_percent < -3:
            risk_score += 3
        elif daily_pnl_percent < -1:
            risk_score += 2
        elif daily_pnl_percent < -0.5:
            risk_score += 1
        
        # Exposure risk
        if exposure_ratio > 0.8:
            risk_score += 3
        elif exposure_ratio > 0.6:
            risk_score += 2
        elif exposure_ratio > 0.4:
            risk_score += 1
        
        # Position count risk
        if position_count > 10:
            risk_score += 2
        elif position_count > 5:
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 6:
            return "critical"
        elif risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"
    
    def shares_for_trade(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: Optional[float] = None,
        portfolio_value: float = 0,
        risk_percent: float = None,
        atr_value: Optional[float] = None
    ) -> PositionSizeResult:
        """
        Calculate position size based on risk management rules.
        
        Args:
            symbol: Trading symbol
            entry_price: Intended entry price
            stop_loss_price: Stop loss price (optional)
            portfolio_value: Current portfolio value
            risk_percent: Risk percentage (defaults to config)
            atr_value: ATR value for dynamic stop loss
        """
        warnings = []
        
        # Use default risk if not provided
        if risk_percent is None:
            risk_percent = settings.default_stop_loss
        
        # Calculate stop loss if not provided
        if stop_loss_price is None and atr_value is not None:
            # Use 2x ATR for stop loss
            stop_loss_price = entry_price - (2 * atr_value)
            warnings.append(f"Using ATR-based stop loss: ${stop_loss_price:.2f}")
        elif stop_loss_price is None:
            # Use default percentage stop loss
            stop_loss_price = entry_price * (1 - settings.default_stop_loss)
            warnings.append(f"Using default {settings.default_stop_loss*100}% stop loss")
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share == 0:
            warnings.append("Risk per share is zero - using minimum position")
            risk_per_share = entry_price * 0.01  # 1% fallback
        
        # Ensure minimum risk per share for viable take-profit calculation
        min_risk_per_share = 0.01  # Minimum $0.01 risk per share
        if risk_per_share < min_risk_per_share:
            risk_per_share = min_risk_per_share
            stop_loss_price = entry_price - risk_per_share
            warnings.append(f"Risk per share too small, adjusted to ${min_risk_per_share:.2f}")
        
        # Calculate maximum risk amount
        max_risk_amount = portfolio_value * risk_percent
        max_position_value = portfolio_value * settings.max_position_size
        
        # Calculate shares based on risk
        shares_by_risk = int(max_risk_amount / risk_per_share)
        
        # Calculate shares based on position size limit
        shares_by_position_limit = int(max_position_value / entry_price)
        
        # Use the smaller of the two
        recommended_shares = min(shares_by_risk, shares_by_position_limit)
        
        # Ensure minimum viable position
        if recommended_shares < 1:
            recommended_shares = 1
            warnings.append("Position size below minimum - using 1 share")
        
        # Calculate actual dollar amount and risk
        dollar_amount = recommended_shares * entry_price
        actual_risk_amount = recommended_shares * risk_per_share
        position_risk_percent = (actual_risk_amount / portfolio_value) * 100 if portfolio_value > 0 else 0
        
        # Calculate take profit (default 2:1 risk/reward)
        take_profit_price = entry_price + (2 * risk_per_share)
        
        # Ensure minimum $0.01 profit for Alpaca compliance
        min_profit_required = 0.01
        if (take_profit_price - entry_price) < min_profit_required:
            take_profit_price = entry_price + min_profit_required
            warnings.append(f"Take profit adjusted to meet minimum $0.01 requirement")
        
        risk_reward_ratio = (take_profit_price - entry_price) / risk_per_share if risk_per_share > 0 else None
        
        # Add warnings for high risk
        if position_risk_percent > risk_percent * 100:
            warnings.append(f"Position risk ({position_risk_percent:.1f}%) exceeds target ({risk_percent*100:.1f}%)")
        
        if dollar_amount > max_position_value:
            warnings.append(f"Position size (${dollar_amount:.0f}) exceeds max position limit (${max_position_value:.0f})")
        
        return PositionSizeResult(
            symbol=symbol,
            recommended_shares=recommended_shares,
            dollar_amount=dollar_amount,
            risk_amount=actual_risk_amount,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_reward_ratio=risk_reward_ratio,
            position_risk_percent=position_risk_percent,
            warnings=warnings
        )
    
    async def check_daily_loss_limit(self, alpaca_client: AlpacaClient) -> Tuple[bool, float, float]:
        """
        Check if daily loss limit has been reached.
        
        Returns:
            (limit_reached, current_loss_percent, max_loss_percent)
        """
        account = await alpaca_client.get_account()
        
        if self.daily_start_equity is None:
            self.daily_start_equity = account.last_equity
        
        daily_pnl = account.equity - self.daily_start_equity
        daily_loss_percent = abs(daily_pnl / self.daily_start_equity) * 100 if self.daily_start_equity > 0 else 0
        max_loss_percent = settings.max_daily_loss * 100
        
        limit_reached = daily_pnl < 0 and daily_loss_percent >= max_loss_percent
        
        return limit_reached, daily_loss_percent, max_loss_percent
    
    async def can_open_new_position(
        self,
        alpaca_client: AlpacaClient,
        symbol: str,
        position_size_dollars: float
    ) -> Tuple[bool, List[str]]:
        """
        Check if a new position can be opened based on risk rules.
        
        Returns:
            (can_open, reasons_if_not)
        """
        reasons = []
        
        # Check daily loss limit
        loss_limit_reached, current_loss, max_loss = await self.check_daily_loss_limit(alpaca_client)
        if loss_limit_reached:
            reasons.append(f"Daily loss limit reached ({current_loss:.1f}% >= {max_loss:.1f}%)")
        
        # Check if market is open
        if not await alpaca_client.is_market_open():
            reasons.append("Market is closed")
        
        # Check account status
        account = await alpaca_client.get_account()
        if account.status != "ACTIVE":
            reasons.append(f"Account status is {account.status}")
        
        # Check buying power
        if position_size_dollars > account.buying_power:
            reasons.append(f"Insufficient buying power (${account.buying_power:.0f} < ${position_size_dollars:.0f})")
        
        # Check position limits
        positions = await alpaca_client.get_positions()
        if len(positions) >= 20:  # Arbitrary limit
            reasons.append("Maximum number of positions reached (20)")
        
        # Check if already have position in this symbol
        existing_position = await alpaca_client.get_position(symbol)
        if existing_position:
            reasons.append(f"Already have position in {symbol}")
        
        return len(reasons) == 0, reasons
    
    def reset_daily_counters(self):
        """Reset daily counters (call at market open)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        if self.last_reset_date != today:
            self.daily_start_equity = None
            self.max_drawdown_today = 0.0
            self.trade_count_today = 0
            self.last_reset_date = today
    
    def update_trade_count(self):
        """Increment the daily trade counter."""
        self.trade_count_today += 1
    
    async def get_portfolio_heat(self, alpaca_client: AlpacaClient) -> Dict[str, float]:
        """
        Calculate portfolio heat (total risk across all positions).
        
        Returns:
            Dictionary with heat metrics
        """
        positions = await alpaca_client.get_positions()
        account = await alpaca_client.get_account()
        
        total_risk = 0.0
        position_risks = {}
        
        for position in positions:
            # Estimate risk based on position size and typical stop loss
            position_value = abs(position.market_value)
            estimated_risk = position_value * settings.default_stop_loss
            total_risk += estimated_risk
            position_risks[position.symbol] = estimated_risk
        
        portfolio_heat_percent = (total_risk / account.portfolio_value) * 100 if account.portfolio_value > 0 else 0
        
        return {
            "total_risk_dollars": total_risk,
            "portfolio_heat_percent": portfolio_heat_percent,
            "position_risks": position_risks,
            "max_heat_percent": settings.max_daily_loss * 100,
            "heat_status": "high" if portfolio_heat_percent > 15 else "medium" if portfolio_heat_percent > 8 else "low"
        }
