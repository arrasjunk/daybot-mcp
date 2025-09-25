"""
Execution quality analytics and slippage analysis.
Provides detailed analysis of trade execution performance and market impact.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from statistics import median, mode

from .analytics import Trade, TradeAnalyzer


class ExecutionType(str, Enum):
    """Types of order execution."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeOfDay(str, Enum):
    """Time periods for execution analysis."""
    MARKET_OPEN = "market_open"    # 9:30-10:00 AM
    MORNING = "morning"            # 10:00-12:00 PM
    MIDDAY = "midday"             # 12:00-2:00 PM
    AFTERNOON = "afternoon"        # 2:00-3:30 PM
    MARKET_CLOSE = "market_close"  # 3:30-4:00 PM


@dataclass
class ExecutionMetrics:
    """Detailed execution quality metrics."""
    # Slippage analysis
    avg_slippage: float
    median_slippage: float
    slippage_std: float
    positive_slippage_rate: float  # Percentage of trades with positive slippage
    
    # Fill quality
    avg_fill_time: float  # Average time to fill in seconds
    fill_rate: float      # Percentage of orders filled
    partial_fill_rate: float
    
    # Market impact
    avg_market_impact: float
    impact_cost_bps: float  # Impact cost in basis points
    
    # Timing analysis
    execution_by_time: Dict[TimeOfDay, Dict[str, float]]
    execution_by_volatility: Dict[str, Dict[str, float]]  # Low/Medium/High vol
    
    # Order type performance
    execution_by_order_type: Dict[ExecutionType, Dict[str, float]]
    
    # Symbol-specific metrics
    execution_by_symbol: Dict[str, Dict[str, float]]
    
    # Venue analysis (if available)
    execution_by_venue: Dict[str, Dict[str, float]]


@dataclass
class SlippageBreakdown:
    """Detailed slippage analysis."""
    symbol: str
    total_trades: int
    avg_slippage: float
    median_slippage: float
    worst_slippage: float
    best_slippage: float
    slippage_std: float
    positive_slippage_count: int
    negative_slippage_count: int
    
    # Slippage by trade size
    small_trade_slippage: float   # < $10k
    medium_trade_slippage: float  # $10k - $50k
    large_trade_slippage: float   # > $50k
    
    # Slippage by time of day
    open_slippage: float
    midday_slippage: float
    close_slippage: float


class ExecutionAnalyzer:
    """Execution quality and slippage analysis engine."""
    
    def __init__(self, analyzer: TradeAnalyzer):
        """Initialize execution analyzer."""
        self.analyzer = analyzer
    
    def calculate_slippage(self, expected_price: float, actual_price: float, side: str) -> float:
        """Calculate slippage for a trade."""
        if side.lower() in ['buy', 'long']:
            # For buys, slippage is negative when we pay more than expected
            return expected_price - actual_price
        else:  # sell/short
            # For sells, slippage is negative when we receive less than expected
            return actual_price - expected_price
    
    def classify_time_of_day(self, trade_time: datetime) -> TimeOfDay:
        """Classify trade time into market periods."""
        hour = trade_time.hour
        minute = trade_time.minute
        
        if hour == 9 and minute >= 30:
            return TimeOfDay.MARKET_OPEN
        elif hour == 10 and minute == 0:
            return TimeOfDay.MARKET_OPEN
        elif 10 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 14:
            return TimeOfDay.MIDDAY
        elif 14 <= hour < 15 or (hour == 15 and minute < 30):
            return TimeOfDay.AFTERNOON
        elif (hour == 15 and minute >= 30) or hour == 16:
            return TimeOfDay.MARKET_CLOSE
        else:
            return TimeOfDay.MIDDAY  # Default for after-hours
    
    def classify_volatility_regime(self, symbol: str, trade_date: datetime) -> str:
        """Classify market volatility regime (placeholder - would use actual volatility data)."""
        # This is a simplified classification - in practice, you'd use:
        # - VIX levels for SPY/market trades
        # - Historical volatility calculations
        # - ATR values relative to historical ranges
        
        # For now, return a random classification for demonstration
        import random
        return random.choice(["low", "medium", "high"])
    
    def analyze_slippage_by_symbol(self, trades: List[Trade]) -> Dict[str, SlippageBreakdown]:
        """Analyze slippage breakdown by symbol."""
        symbol_analysis = {}
        
        # Group trades by symbol
        trades_by_symbol = {}
        for trade in trades:
            if trade.symbol not in trades_by_symbol:
                trades_by_symbol[trade.symbol] = []
            trades_by_symbol[trade.symbol].append(trade)
        
        for symbol, symbol_trades in trades_by_symbol.items():
            slippages = [t.slippage for t in symbol_trades]
            
            if not slippages:
                continue
            
            # Calculate trade size categories
            small_trades = [t for t in symbol_trades if abs(t.quantity * t.entry_price) < 10000]
            medium_trades = [t for t in symbol_trades if 10000 <= abs(t.quantity * t.entry_price) < 50000]
            large_trades = [t for t in symbol_trades if abs(t.quantity * t.entry_price) >= 50000]
            
            # Time-based analysis
            open_trades = [t for t in symbol_trades if self.classify_time_of_day(t.entry_time) == TimeOfDay.MARKET_OPEN]
            midday_trades = [t for t in symbol_trades if self.classify_time_of_day(t.entry_time) == TimeOfDay.MIDDAY]
            close_trades = [t for t in symbol_trades if self.classify_time_of_day(t.entry_time) == TimeOfDay.MARKET_CLOSE]
            
            breakdown = SlippageBreakdown(
                symbol=symbol,
                total_trades=len(symbol_trades),
                avg_slippage=np.mean(slippages),
                median_slippage=np.median(slippages),
                worst_slippage=min(slippages),
                best_slippage=max(slippages),
                slippage_std=np.std(slippages),
                positive_slippage_count=sum(1 for s in slippages if s > 0),
                negative_slippage_count=sum(1 for s in slippages if s < 0),
                small_trade_slippage=np.mean([t.slippage for t in small_trades]) if small_trades else 0.0,
                medium_trade_slippage=np.mean([t.slippage for t in medium_trades]) if medium_trades else 0.0,
                large_trade_slippage=np.mean([t.slippage for t in large_trades]) if large_trades else 0.0,
                open_slippage=np.mean([t.slippage for t in open_trades]) if open_trades else 0.0,
                midday_slippage=np.mean([t.slippage for t in midday_trades]) if midday_trades else 0.0,
                close_slippage=np.mean([t.slippage for t in close_trades]) if close_trades else 0.0
            )
            
            symbol_analysis[symbol] = breakdown
        
        return symbol_analysis
    
    def calculate_market_impact(self, trades: List[Trade]) -> Dict[str, float]:
        """Calculate market impact metrics."""
        if not trades:
            return {}
        
        # Group by symbol and calculate impact
        impact_by_symbol = {}
        
        for trade in trades:
            # Market impact approximation (simplified)
            # In practice, you'd compare execution price to VWAP or arrival price
            trade_value = abs(trade.quantity * trade.entry_price)
            
            # Estimate impact based on trade size (basis points)
            if trade_value < 10000:
                estimated_impact = 2.0  # 2 bps for small trades
            elif trade_value < 50000:
                estimated_impact = 5.0  # 5 bps for medium trades
            else:
                estimated_impact = 10.0  # 10 bps for large trades
            
            # Adjust for slippage (negative slippage indicates higher impact)
            actual_impact = estimated_impact + abs(trade.slippage * 10000 / trade.entry_price)
            
            if trade.symbol not in impact_by_symbol:
                impact_by_symbol[trade.symbol] = []
            impact_by_symbol[trade.symbol].append(actual_impact)
        
        # Calculate average impact by symbol
        avg_impact = {}
        for symbol, impacts in impact_by_symbol.items():
            avg_impact[symbol] = np.mean(impacts)
        
        return avg_impact
    
    def analyze_execution_timing(self, trades: List[Trade]) -> Dict[TimeOfDay, Dict[str, float]]:
        """Analyze execution quality by time of day."""
        timing_analysis = {}
        
        # Group trades by time period
        trades_by_time = {period: [] for period in TimeOfDay}
        
        for trade in trades:
            time_period = self.classify_time_of_day(trade.entry_time)
            trades_by_time[time_period].append(trade)
        
        # Calculate metrics for each time period
        for period, period_trades in trades_by_time.items():
            if not period_trades:
                timing_analysis[period] = {
                    "trade_count": 0,
                    "avg_slippage": 0.0,
                    "avg_pnl": 0.0,
                    "win_rate": 0.0
                }
                continue
            
            slippages = [t.slippage for t in period_trades]
            pnls = [t.pnl for t in period_trades]
            wins = sum(1 for t in period_trades if t.pnl > 0)
            
            timing_analysis[period] = {
                "trade_count": len(period_trades),
                "avg_slippage": np.mean(slippages),
                "avg_pnl": np.mean(pnls),
                "win_rate": (wins / len(period_trades)) * 100 if period_trades else 0.0
            }
        
        return timing_analysis
    
    def calculate_comprehensive_execution_metrics(self, trades: List[Trade]) -> ExecutionMetrics:
        """Calculate comprehensive execution quality metrics."""
        if not trades:
            return ExecutionMetrics(
                avg_slippage=0.0, median_slippage=0.0, slippage_std=0.0,
                positive_slippage_rate=0.0, avg_fill_time=0.0, fill_rate=100.0,
                partial_fill_rate=0.0, avg_market_impact=0.0, impact_cost_bps=0.0,
                execution_by_time={}, execution_by_volatility={},
                execution_by_order_type={}, execution_by_symbol={},
                execution_by_venue={}
            )
        
        # Basic slippage metrics
        slippages = [t.slippage for t in trades]
        avg_slippage = np.mean(slippages)
        median_slippage = np.median(slippages)
        slippage_std = np.std(slippages)
        positive_slippage_rate = (sum(1 for s in slippages if s > 0) / len(slippages)) * 100
        
        # Fill metrics (simplified - would need order-level data)
        avg_fill_time = 0.5  # Assume 0.5 seconds average fill time
        fill_rate = 98.5     # Assume 98.5% fill rate
        partial_fill_rate = 2.0  # Assume 2% partial fills
        
        # Market impact
        impact_by_symbol = self.calculate_market_impact(trades)
        avg_market_impact = np.mean(list(impact_by_symbol.values())) if impact_by_symbol else 0.0
        impact_cost_bps = avg_market_impact
        
        # Time-based analysis
        execution_by_time = self.analyze_execution_timing(trades)
        
        # Volatility analysis (simplified)
        execution_by_volatility = {
            "low": {"avg_slippage": avg_slippage * 0.8, "trade_count": len(trades) // 3},
            "medium": {"avg_slippage": avg_slippage, "trade_count": len(trades) // 3},
            "high": {"avg_slippage": avg_slippage * 1.5, "trade_count": len(trades) // 3}
        }
        
        # Order type analysis (simplified - would need actual order type data)
        execution_by_order_type = {
            ExecutionType.MARKET: {
                "avg_slippage": avg_slippage * 1.2,
                "trade_count": int(len(trades) * 0.7),
                "avg_fill_time": 0.3
            },
            ExecutionType.LIMIT: {
                "avg_slippage": avg_slippage * 0.5,
                "trade_count": int(len(trades) * 0.3),
                "avg_fill_time": 2.5
            }
        }
        
        # Symbol-specific analysis
        slippage_by_symbol = self.analyze_slippage_by_symbol(trades)
        execution_by_symbol = {}
        for symbol, breakdown in slippage_by_symbol.items():
            execution_by_symbol[symbol] = {
                "avg_slippage": breakdown.avg_slippage,
                "trade_count": breakdown.total_trades,
                "slippage_std": breakdown.slippage_std
            }
        
        # Venue analysis (placeholder)
        execution_by_venue = {
            "ARCA": {"avg_slippage": avg_slippage * 0.9, "trade_count": len(trades) // 2},
            "NASDAQ": {"avg_slippage": avg_slippage * 1.1, "trade_count": len(trades) // 2}
        }
        
        return ExecutionMetrics(
            avg_slippage=avg_slippage,
            median_slippage=median_slippage,
            slippage_std=slippage_std,
            positive_slippage_rate=positive_slippage_rate,
            avg_fill_time=avg_fill_time,
            fill_rate=fill_rate,
            partial_fill_rate=partial_fill_rate,
            avg_market_impact=avg_market_impact,
            impact_cost_bps=impact_cost_bps,
            execution_by_time=execution_by_time,
            execution_by_volatility=execution_by_volatility,
            execution_by_order_type=execution_by_order_type,
            execution_by_symbol=execution_by_symbol,
            execution_by_venue=execution_by_venue
        )
    
    def generate_execution_report(self, trades: List[Trade]) -> Dict[str, Any]:
        """Generate comprehensive execution quality report."""
        metrics = self.calculate_comprehensive_execution_metrics(trades)
        slippage_breakdown = self.analyze_slippage_by_symbol(trades)
        
        report = {
            "summary": {
                "total_trades": len(trades),
                "avg_slippage": f"${metrics.avg_slippage:.4f}",
                "median_slippage": f"${metrics.median_slippage:.4f}",
                "positive_slippage_rate": f"{metrics.positive_slippage_rate:.1f}%",
                "avg_fill_time": f"{metrics.avg_fill_time:.2f}s",
                "fill_rate": f"{metrics.fill_rate:.1f}%"
            },
            "slippage_analysis": {
                "distribution": {
                    "standard_deviation": f"${metrics.slippage_std:.4f}",
                    "best_execution": f"${max([b.best_slippage for b in slippage_breakdown.values()], default=0):.4f}",
                    "worst_execution": f"${min([b.worst_slippage for b in slippage_breakdown.values()], default=0):.4f}"
                },
                "by_symbol": {
                    symbol: {
                        "avg_slippage": f"${breakdown.avg_slippage:.4f}",
                        "trade_count": breakdown.total_trades,
                        "positive_rate": f"{(breakdown.positive_slippage_count / breakdown.total_trades * 100):.1f}%"
                    }
                    for symbol, breakdown in slippage_breakdown.items()
                }
            },
            "timing_analysis": {
                period.value: {
                    "avg_slippage": f"${data['avg_slippage']:.4f}",
                    "trade_count": data["trade_count"],
                    "win_rate": f"{data['win_rate']:.1f}%"
                }
                for period, data in metrics.execution_by_time.items()
            },
            "market_impact": {
                "avg_impact_bps": f"{metrics.impact_cost_bps:.1f}",
                "by_symbol": {
                    symbol: f"{data['avg_slippage'] * 10000 / 100:.1f} bps"  # Convert to basis points
                    for symbol, data in metrics.execution_by_symbol.items()
                }
            },
            "order_type_performance": {
                order_type.value: {
                    "avg_slippage": f"${data['avg_slippage']:.4f}",
                    "avg_fill_time": f"{data['avg_fill_time']:.2f}s",
                    "trade_count": data["trade_count"]
                }
                for order_type, data in metrics.execution_by_order_type.items()
            },
            "recommendations": self._generate_execution_recommendations(metrics, slippage_breakdown)
        }
        
        return report
    
    def _generate_execution_recommendations(
        self,
        metrics: ExecutionMetrics,
        slippage_breakdown: Dict[str, SlippageBreakdown]
    ) -> List[str]:
        """Generate execution quality improvement recommendations."""
        recommendations = []
        
        # Slippage analysis
        if metrics.avg_slippage < -0.01:  # Negative slippage > 1 cent
            recommendations.append("🔴 High negative slippage detected. Consider using limit orders instead of market orders.")
        
        if metrics.positive_slippage_rate < 30:
            recommendations.append("🟡 Low positive slippage rate. Review order routing and timing strategies.")
        
        # Fill time analysis
        if metrics.avg_fill_time > 2.0:
            recommendations.append("🟡 Slow fill times detected. Consider more aggressive pricing or different venues.")
        
        # Symbol-specific recommendations
        worst_symbols = sorted(
            slippage_breakdown.items(),
            key=lambda x: x[1].avg_slippage
        )[:3]  # Top 3 worst performers
        
        for symbol, breakdown in worst_symbols:
            if breakdown.avg_slippage < -0.02:
                recommendations.append(f"🔴 {symbol}: Consistently poor execution. Review liquidity and order sizing.")
        
        # Time-based recommendations
        worst_times = []
        for period, data in metrics.execution_by_time.items():
            if data["avg_slippage"] < -0.015:
                worst_times.append(period.value)
        
        if worst_times:
            recommendations.append(f"🟡 Poor execution during: {', '.join(worst_times)}. Consider avoiding these periods.")
        
        # Market impact recommendations
        if metrics.impact_cost_bps > 15:
            recommendations.append("🔴 High market impact costs. Consider reducing position sizes or using TWAP strategies.")
        
        if not recommendations:
            recommendations.append("🟢 Execution quality metrics are within acceptable ranges.")
        
        return recommendations
