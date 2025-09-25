"""
Advanced risk analytics and drawdown analysis for trading performance.
Provides detailed risk metrics, drawdown patterns, and portfolio heat analysis.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .analytics import Trade, TradeAnalyzer


class DrawdownType(str, Enum):
    """Types of drawdown analysis."""
    ABSOLUTE = "absolute"
    PERCENTAGE = "percentage"
    UNDERWATER = "underwater"


@dataclass
class DrawdownPeriod:
    """Represents a drawdown period with detailed metrics."""
    start_date: datetime
    end_date: datetime
    recovery_date: Optional[datetime]
    peak_value: float
    trough_value: float
    drawdown_amount: float
    drawdown_percent: float
    duration_days: int
    recovery_days: Optional[int]
    trades_in_drawdown: int
    is_recovered: bool = False
    
    @property
    def total_duration_days(self) -> int:
        """Total duration including recovery."""
        if self.recovery_date:
            return (self.recovery_date - self.start_date).days
        return (datetime.now() - self.start_date).days


@dataclass
class RiskMetrics:
    """Comprehensive risk analysis metrics."""
    # Drawdown metrics
    max_drawdown_absolute: float
    max_drawdown_percent: float
    avg_drawdown_percent: float
    drawdown_periods: List[DrawdownPeriod]
    
    # Volatility metrics
    daily_volatility: float
    annual_volatility: float
    downside_deviation: float
    
    # Risk-adjusted returns
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    sterling_ratio: float
    
    # Value at Risk
    var_95: float  # 95% VaR
    var_99: float  # 99% VaR
    cvar_95: float  # Conditional VaR (Expected Shortfall)
    
    # Tail risk
    skewness: float
    kurtosis: float
    tail_ratio: float
    
    # Time-based risk
    underwater_periods: int
    avg_recovery_time: float
    max_recovery_time: int
    
    # Portfolio heat
    current_heat: float
    max_heat: float
    avg_heat: float


class RiskAnalyzer:
    """Advanced risk analysis engine."""
    
    def __init__(self, analyzer: TradeAnalyzer):
        """Initialize risk analyzer."""
        self.analyzer = analyzer
    
    def analyze_drawdowns(
        self,
        trades: List[Trade],
        initial_capital: float = 100000.0
    ) -> List[DrawdownPeriod]:
        """Analyze all drawdown periods in detail."""
        if not trades:
            return []
        
        # Sort trades by exit time
        sorted_trades = sorted(trades, key=lambda t: t.exit_time)
        
        # Calculate equity curve
        equity_curve = []
        running_capital = initial_capital
        
        for trade in sorted_trades:
            running_capital += trade.pnl
            equity_curve.append({
                'date': trade.exit_time,
                'equity': running_capital,
                'trade': trade
            })
        
        # Find drawdown periods
        drawdown_periods = []
        peak_equity = initial_capital
        peak_date = sorted_trades[0].exit_time if sorted_trades else datetime.now()
        in_drawdown = False
        drawdown_start = None
        trough_equity = peak_equity
        trough_date = peak_date
        trades_in_dd = 0
        
        for point in equity_curve:
            current_equity = point['equity']
            current_date = point['date']
            
            # Check if we're at a new peak
            if current_equity > peak_equity:
                # If we were in drawdown, end it
                if in_drawdown:
                    drawdown_period = DrawdownPeriod(
                        start_date=drawdown_start,
                        end_date=trough_date,
                        recovery_date=current_date,
                        peak_value=peak_equity,
                        trough_value=trough_equity,
                        drawdown_amount=peak_equity - trough_equity,
                        drawdown_percent=((peak_equity - trough_equity) / peak_equity) * 100,
                        duration_days=(trough_date - drawdown_start).days,
                        recovery_days=(current_date - trough_date).days,
                        trades_in_drawdown=trades_in_dd,
                        is_recovered=True
                    )
                    drawdown_periods.append(drawdown_period)
                    in_drawdown = False
                
                # Update peak
                peak_equity = current_equity
                peak_date = current_date
            
            # Check if we're starting or continuing a drawdown
            elif current_equity < peak_equity:
                if not in_drawdown:
                    # Starting new drawdown
                    in_drawdown = True
                    drawdown_start = peak_date
                    trough_equity = current_equity
                    trough_date = current_date
                    trades_in_dd = 1
                else:
                    # Continuing drawdown
                    trades_in_dd += 1
                    if current_equity < trough_equity:
                        trough_equity = current_equity
                        trough_date = current_date
        
        # Handle ongoing drawdown
        if in_drawdown:
            drawdown_period = DrawdownPeriod(
                start_date=drawdown_start,
                end_date=trough_date,
                recovery_date=None,
                peak_value=peak_equity,
                trough_value=trough_equity,
                drawdown_amount=peak_equity - trough_equity,
                drawdown_percent=((peak_equity - trough_equity) / peak_equity) * 100,
                duration_days=(trough_date - drawdown_start).days,
                recovery_days=None,
                trades_in_drawdown=trades_in_dd,
                is_recovered=False
            )
            drawdown_periods.append(drawdown_period)
        
        return drawdown_periods
    
    def calculate_var_metrics(self, returns: List[float]) -> Tuple[float, float, float]:
        """Calculate Value at Risk metrics."""
        if not returns or len(returns) < 10:
            return 0.0, 0.0, 0.0
        
        returns_array = np.array(returns)
        
        # 95% and 99% VaR (negative values indicate losses)
        var_95 = np.percentile(returns_array, 5)
        var_99 = np.percentile(returns_array, 1)
        
        # Conditional VaR (Expected Shortfall) - average of worst 5%
        worst_5_percent = returns_array[returns_array <= var_95]
        cvar_95 = np.mean(worst_5_percent) if len(worst_5_percent) > 0 else 0.0
        
        return var_95, var_99, cvar_95
    
    def calculate_tail_metrics(self, returns: List[float]) -> Tuple[float, float, float]:
        """Calculate tail risk metrics."""
        if not returns or len(returns) < 10:
            return 0.0, 0.0, 0.0
        
        returns_array = np.array(returns)
        
        # Skewness (asymmetry)
        skewness = float(pd.Series(returns_array).skew())
        
        # Kurtosis (tail heaviness)
        kurtosis = float(pd.Series(returns_array).kurtosis())
        
        # Tail ratio (95th percentile / 5th percentile)
        p95 = np.percentile(returns_array, 95)
        p5 = np.percentile(returns_array, 5)
        tail_ratio = abs(p95 / p5) if p5 != 0 else 0.0
        
        return skewness, kurtosis, tail_ratio
    
    def calculate_portfolio_heat(
        self,
        trades: List[Trade],
        max_positions: int = 10,
        max_risk_per_trade: float = 0.02
    ) -> Tuple[float, float, float]:
        """Calculate portfolio heat metrics."""
        if not trades:
            return 0.0, 0.0, 0.0
        
        # Group trades by time periods to simulate concurrent positions
        heat_values = []
        
        # Sort trades by entry time
        sorted_trades = sorted(trades, key=lambda t: t.entry_time)
        
        for i, trade in enumerate(sorted_trades):
            # Find concurrent trades (overlapping time periods)
            concurrent_trades = []
            for other_trade in sorted_trades:
                if (other_trade.entry_time <= trade.exit_time and 
                    other_trade.exit_time >= trade.entry_time):
                    concurrent_trades.append(other_trade)
            
            # Calculate heat as percentage of portfolio at risk
            position_count = len(concurrent_trades)
            heat = min(position_count * max_risk_per_trade, 1.0) * 100
            heat_values.append(heat)
        
        current_heat = heat_values[-1] if heat_values else 0.0
        max_heat = max(heat_values) if heat_values else 0.0
        avg_heat = sum(heat_values) / len(heat_values) if heat_values else 0.0
        
        return current_heat, max_heat, avg_heat
    
    def calculate_comprehensive_risk_metrics(
        self,
        trades: List[Trade],
        initial_capital: float = 100000.0,
        risk_free_rate: float = 0.02
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics."""
        if not trades:
            return RiskMetrics(
                max_drawdown_absolute=0.0, max_drawdown_percent=0.0,
                avg_drawdown_percent=0.0, drawdown_periods=[],
                daily_volatility=0.0, annual_volatility=0.0, downside_deviation=0.0,
                sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0, sterling_ratio=0.0,
                var_95=0.0, var_99=0.0, cvar_95=0.0,
                skewness=0.0, kurtosis=0.0, tail_ratio=0.0,
                underwater_periods=0, avg_recovery_time=0.0, max_recovery_time=0,
                current_heat=0.0, max_heat=0.0, avg_heat=0.0
            )
        
        # Calculate returns
        returns = self._calculate_daily_returns(trades, initial_capital)
        
        # Drawdown analysis
        drawdown_periods = self.analyze_drawdowns(trades, initial_capital)
        
        max_dd_abs = max([dd.drawdown_amount for dd in drawdown_periods], default=0.0)
        max_dd_pct = max([dd.drawdown_percent for dd in drawdown_periods], default=0.0)
        avg_dd_pct = sum([dd.drawdown_percent for dd in drawdown_periods]) / len(drawdown_periods) if drawdown_periods else 0.0
        
        # Volatility metrics
        returns_array = np.array(returns) if returns else np.array([])
        daily_vol = float(np.std(returns_array, ddof=1)) if len(returns_array) > 1 else 0.0
        annual_vol = daily_vol * np.sqrt(252)
        
        # Downside deviation
        negative_returns = [r for r in returns if r < 0]
        downside_dev = float(np.std(negative_returns, ddof=1)) if len(negative_returns) > 1 else 0.0
        
        # Risk-adjusted returns
        mean_return = float(np.mean(returns_array)) if len(returns_array) > 0 else 0.0
        excess_return = mean_return - (risk_free_rate / 252)
        
        sharpe = (excess_return / daily_vol * np.sqrt(252)) if daily_vol > 0 else 0.0
        sortino = (excess_return / downside_dev * np.sqrt(252)) if downside_dev > 0 else 0.0
        calmar = (mean_return * 252 / max_dd_pct * 100) if max_dd_pct > 0 else 0.0
        sterling = (mean_return * 252 / avg_dd_pct * 100) if avg_dd_pct > 0 else 0.0
        
        # VaR metrics
        var_95, var_99, cvar_95 = self.calculate_var_metrics(returns)
        
        # Tail metrics
        skewness, kurtosis, tail_ratio = self.calculate_tail_metrics(returns)
        
        # Recovery metrics
        recovered_periods = [dd for dd in drawdown_periods if dd.is_recovered]
        avg_recovery = sum([dd.recovery_days for dd in recovered_periods]) / len(recovered_periods) if recovered_periods else 0.0
        max_recovery = max([dd.recovery_days for dd in recovered_periods], default=0)
        underwater_periods = len([dd for dd in drawdown_periods if not dd.is_recovered])
        
        # Portfolio heat
        current_heat, max_heat, avg_heat = self.calculate_portfolio_heat(trades)
        
        return RiskMetrics(
            max_drawdown_absolute=max_dd_abs,
            max_drawdown_percent=max_dd_pct,
            avg_drawdown_percent=avg_dd_pct,
            drawdown_periods=drawdown_periods,
            daily_volatility=daily_vol,
            annual_volatility=annual_vol,
            downside_deviation=downside_dev,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            sterling_ratio=sterling,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            skewness=skewness,
            kurtosis=kurtosis,
            tail_ratio=tail_ratio,
            underwater_periods=underwater_periods,
            avg_recovery_time=avg_recovery,
            max_recovery_time=max_recovery,
            current_heat=current_heat,
            max_heat=max_heat,
            avg_heat=avg_heat
        )
    
    def _calculate_daily_returns(self, trades: List[Trade], initial_capital: float) -> List[float]:
        """Calculate daily returns from trades."""
        if not trades:
            return []
        
        # Sort trades by exit time
        sorted_trades = sorted(trades, key=lambda t: t.exit_time)
        
        # Group trades by day
        daily_pnl = {}
        for trade in sorted_trades:
            date_key = trade.exit_time.date()
            if date_key not in daily_pnl:
                daily_pnl[date_key] = 0.0
            daily_pnl[date_key] += trade.pnl
        
        # Calculate daily returns
        returns = []
        running_capital = initial_capital
        
        for date in sorted(daily_pnl.keys()):
            daily_return = daily_pnl[date] / running_capital if running_capital > 0 else 0.0
            returns.append(daily_return)
            running_capital += daily_pnl[date]
        
        return returns
    
    def generate_risk_report(self, trades: List[Trade]) -> Dict[str, Any]:
        """Generate comprehensive risk analysis report."""
        risk_metrics = self.calculate_comprehensive_risk_metrics(trades)
        
        report = {
            "drawdown_analysis": {
                "max_drawdown": {
                    "absolute": f"${risk_metrics.max_drawdown_absolute:,.2f}",
                    "percentage": f"{risk_metrics.max_drawdown_percent:.2f}%"
                },
                "average_drawdown": f"{risk_metrics.avg_drawdown_percent:.2f}%",
                "drawdown_periods": len(risk_metrics.drawdown_periods),
                "current_underwater": risk_metrics.underwater_periods > 0,
                "longest_recovery": f"{risk_metrics.max_recovery_time} days"
            },
            "volatility_analysis": {
                "daily_volatility": f"{risk_metrics.daily_volatility:.4f}",
                "annual_volatility": f"{risk_metrics.annual_volatility:.2%}",
                "downside_deviation": f"{risk_metrics.downside_deviation:.4f}"
            },
            "risk_adjusted_returns": {
                "sharpe_ratio": f"{risk_metrics.sharpe_ratio:.2f}",
                "sortino_ratio": f"{risk_metrics.sortino_ratio:.2f}",
                "calmar_ratio": f"{risk_metrics.calmar_ratio:.2f}",
                "sterling_ratio": f"{risk_metrics.sterling_ratio:.2f}"
            },
            "value_at_risk": {
                "var_95": f"{risk_metrics.var_95:.2%}",
                "var_99": f"{risk_metrics.var_99:.2%}",
                "conditional_var_95": f"{risk_metrics.cvar_95:.2%}"
            },
            "tail_risk": {
                "skewness": f"{risk_metrics.skewness:.2f}",
                "kurtosis": f"{risk_metrics.kurtosis:.2f}",
                "tail_ratio": f"{risk_metrics.tail_ratio:.2f}"
            },
            "portfolio_heat": {
                "current": f"{risk_metrics.current_heat:.1f}%",
                "maximum": f"{risk_metrics.max_heat:.1f}%",
                "average": f"{risk_metrics.avg_heat:.1f}%"
            },
            "risk_warnings": self._generate_risk_warnings(risk_metrics)
        }
        
        return report
    
    def _generate_risk_warnings(self, metrics: RiskMetrics) -> List[str]:
        """Generate risk warnings based on metrics."""
        warnings = []
        
        if metrics.max_drawdown_percent > 25:
            warnings.append("🔴 CRITICAL: Maximum drawdown exceeds 25% - consider reducing position sizes")
        
        if metrics.underwater_periods > 0:
            warnings.append("🟡 WARNING: Currently in drawdown period - monitor risk closely")
        
        if metrics.sharpe_ratio < 0.5:
            warnings.append("🔴 Poor risk-adjusted returns - Sharpe ratio below 0.5")
        
        if metrics.var_99 < -0.05:
            warnings.append("🟡 High tail risk - 99% VaR indicates potential for large losses")
        
        if metrics.max_heat > 80:
            warnings.append("🔴 Excessive portfolio heat detected - reduce concurrent positions")
        
        if metrics.skewness < -1.0:
            warnings.append("🟡 Negative skew indicates asymmetric downside risk")
        
        if metrics.kurtosis > 3.0:
            warnings.append("🟡 High kurtosis indicates fat tails - expect extreme moves")
        
        if not warnings:
            warnings.append("🟢 Risk metrics within acceptable ranges")
        
        return warnings
