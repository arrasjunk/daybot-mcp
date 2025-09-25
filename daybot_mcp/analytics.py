"""
Comprehensive trade analytics and performance measurement system.
Provides post-trade analysis, performance metrics, and strategy optimization insights.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class AnalyticsPeriod(str, Enum):
    """Time periods for analytics calculations."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ALL_TIME = "all_time"


class TradeOutcome(str, Enum):
    """Trade outcome classification."""
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"


@dataclass
class Trade:
    """Represents a complete trade with entry and exit."""
    symbol: str
    strategy: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    side: str  # "buy" or "sell"
    pnl: float
    pnl_percent: float
    commission: float = 0.0
    slippage: float = 0.0
    exit_reason: str = ""
    duration_minutes: int = 0
    max_favorable_excursion: float = 0.0  # MFE
    max_adverse_excursion: float = 0.0    # MAE
    
    def __post_init__(self):
        """Calculate derived fields."""
        if self.duration_minutes == 0:
            self.duration_minutes = int((self.exit_time - self.entry_time).total_seconds() / 60)
        
        # Calculate percentage P&L if not provided
        if self.pnl_percent == 0.0 and self.entry_price > 0:
            if self.side.lower() == "buy":
                self.pnl_percent = ((self.exit_price - self.entry_price) / self.entry_price) * 100
            else:  # sell/short
                self.pnl_percent = ((self.entry_price - self.exit_price) / self.entry_price) * 100
    
    @property
    def outcome(self) -> TradeOutcome:
        """Classify trade outcome."""
        if abs(self.pnl) < 0.01:  # Within 1 cent
            return TradeOutcome.BREAKEVEN
        return TradeOutcome.WIN if self.pnl > 0 else TradeOutcome.LOSS
    
    @property
    def r_multiple(self) -> float:
        """Calculate R-multiple (reward/risk ratio)."""
        if self.max_adverse_excursion == 0:
            return 0.0
        return abs(self.pnl) / abs(self.max_adverse_excursion)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a trading period."""
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    
    # P&L metrics
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    
    # Ratio metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    recovery_factor: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trade distribution
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Time metrics
    avg_trade_duration: float = 0.0  # in minutes
    avg_time_in_market: float = 0.0  # percentage
    
    # Advanced metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    kelly_criterion: float = 0.0
    
    # Execution quality
    avg_slippage: float = 0.0
    total_commission: float = 0.0
    
    # Consecutive metrics
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # R-multiple analysis
    avg_r_multiple: float = 0.0
    
    # Additional metadata
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    strategies_analyzed: List[str] = field(default_factory=list)


class TradeAnalyzer:
    """Core trade analysis engine."""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize the trade analyzer."""
        self.log_dir = Path(log_dir)
        self.db_path = self.log_dir / "trades.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for trade storage."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    side TEXT NOT NULL,
                    pnl REAL NOT NULL,
                    pnl_percent REAL NOT NULL,
                    commission REAL DEFAULT 0.0,
                    slippage REAL DEFAULT 0.0,
                    exit_reason TEXT DEFAULT '',
                    duration_minutes INTEGER DEFAULT 0,
                    max_favorable_excursion REAL DEFAULT 0.0,
                    max_adverse_excursion REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)
            """)
    
    def add_trade(self, trade: Trade) -> int:
        """Add a completed trade to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO trades (
                    symbol, strategy, entry_time, exit_time, entry_price, exit_price,
                    quantity, side, pnl, pnl_percent, commission, slippage,
                    exit_reason, duration_minutes, max_favorable_excursion,
                    max_adverse_excursion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.symbol, trade.strategy,
                trade.entry_time.isoformat(), trade.exit_time.isoformat(),
                trade.entry_price, trade.exit_price, trade.quantity, trade.side,
                trade.pnl, trade.pnl_percent, trade.commission, trade.slippage,
                trade.exit_reason, trade.duration_minutes,
                trade.max_favorable_excursion, trade.max_adverse_excursion
            ))
            return cursor.lastrowid
    
    def get_trades(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Trade]:
        """Retrieve trades based on filters."""
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND entry_time >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND entry_time <= ?"
            params.append(end_date.isoformat())
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)
        
        query += " ORDER BY entry_time DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            trades = []
            for row in cursor.fetchall():
                trade = Trade(
                    symbol=row['symbol'],
                    strategy=row['strategy'],
                    entry_time=datetime.fromisoformat(row['entry_time']),
                    exit_time=datetime.fromisoformat(row['exit_time']),
                    entry_price=row['entry_price'],
                    exit_price=row['exit_price'],
                    quantity=row['quantity'],
                    side=row['side'],
                    pnl=row['pnl'],
                    pnl_percent=row['pnl_percent'],
                    commission=row['commission'],
                    slippage=row['slippage'],
                    exit_reason=row['exit_reason'],
                    duration_minutes=row['duration_minutes'],
                    max_favorable_excursion=row['max_favorable_excursion'],
                    max_adverse_excursion=row['max_adverse_excursion']
                )
                trades.append(trade)
            
            return trades
    
    def calculate_performance_metrics(
        self,
        trades: List[Trade],
        initial_capital: float = 100000.0
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics for a list of trades."""
        if not trades:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        
        # Basic counts
        metrics.total_trades = len(trades)
        metrics.winning_trades = sum(1 for t in trades if t.outcome == TradeOutcome.WIN)
        metrics.losing_trades = sum(1 for t in trades if t.outcome == TradeOutcome.LOSS)
        metrics.breakeven_trades = sum(1 for t in trades if t.outcome == TradeOutcome.BREAKEVEN)
        
        # P&L calculations
        metrics.total_pnl = sum(t.pnl for t in trades)
        metrics.gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        metrics.gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        metrics.net_profit = metrics.gross_profit - metrics.gross_loss
        
        # Ratio calculations
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
        
        if metrics.gross_loss > 0:
            metrics.profit_factor = metrics.gross_profit / metrics.gross_loss
        
        if metrics.total_trades > 0:
            metrics.expectancy = metrics.total_pnl / metrics.total_trades
        
        # Trade distribution
        winning_pnls = [t.pnl for t in trades if t.pnl > 0]
        losing_pnls = [t.pnl for t in trades if t.pnl < 0]
        
        if winning_pnls:
            metrics.avg_win = sum(winning_pnls) / len(winning_pnls)
            metrics.largest_win = max(winning_pnls)
        
        if losing_pnls:
            metrics.avg_loss = sum(losing_pnls) / len(losing_pnls)
            metrics.largest_loss = min(losing_pnls)
        
        # Time metrics
        durations = [t.duration_minutes for t in trades]
        if durations:
            metrics.avg_trade_duration = sum(durations) / len(durations)
        
        # Drawdown analysis
        metrics.max_drawdown, metrics.max_drawdown_percent = self._calculate_drawdown(
            trades, initial_capital
        )
        
        if metrics.max_drawdown > 0:
            metrics.recovery_factor = metrics.net_profit / metrics.max_drawdown
        
        # Execution quality
        metrics.avg_slippage = sum(t.slippage for t in trades) / len(trades) if trades else 0
        metrics.total_commission = sum(t.commission for t in trades)
        
        # Consecutive analysis
        metrics.max_consecutive_wins, metrics.max_consecutive_losses = self._calculate_consecutive_stats(trades)
        
        # R-multiple analysis
        r_multiples = [t.r_multiple for t in trades if t.r_multiple > 0]
        if r_multiples:
            metrics.avg_r_multiple = sum(r_multiples) / len(r_multiples)
        
        # Risk metrics
        returns = self._calculate_returns(trades, initial_capital)
        if returns:
            metrics.sharpe_ratio = self._calculate_sharpe_ratio(returns)
            metrics.sortino_ratio = self._calculate_sortino_ratio(returns)
        
        # Kelly Criterion
        if metrics.win_rate > 0 and metrics.avg_loss < 0:
            win_prob = metrics.win_rate / 100
            avg_win_ratio = abs(metrics.avg_win / metrics.avg_loss) if metrics.avg_loss != 0 else 0
            metrics.kelly_criterion = win_prob - ((1 - win_prob) / avg_win_ratio) if avg_win_ratio > 0 else 0
        
        # Period information
        if trades:
            metrics.period_start = min(t.entry_time for t in trades)
            metrics.period_end = max(t.exit_time for t in trades)
            metrics.strategies_analyzed = list(set(t.strategy for t in trades))
        
        return metrics
    
    def _calculate_drawdown(self, trades: List[Trade], initial_capital: float) -> Tuple[float, float]:
        """Calculate maximum drawdown in absolute and percentage terms."""
        if not trades:
            return 0.0, 0.0
        
        # Sort trades by exit time
        sorted_trades = sorted(trades, key=lambda t: t.exit_time)
        
        running_capital = initial_capital
        peak_capital = initial_capital
        max_drawdown = 0.0
        max_drawdown_percent = 0.0
        
        for trade in sorted_trades:
            running_capital += trade.pnl
            
            if running_capital > peak_capital:
                peak_capital = running_capital
            
            current_drawdown = peak_capital - running_capital
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
                max_drawdown_percent = (current_drawdown / peak_capital) * 100 if peak_capital > 0 else 0
        
        return max_drawdown, max_drawdown_percent
    
    def _calculate_consecutive_stats(self, trades: List[Trade]) -> Tuple[int, int]:
        """Calculate maximum consecutive wins and losses."""
        if not trades:
            return 0, 0
        
        # Sort trades by exit time
        sorted_trades = sorted(trades, key=lambda t: t.exit_time)
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in sorted_trades:
            if trade.outcome == TradeOutcome.WIN:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif trade.outcome == TradeOutcome.LOSS:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
            else:  # breakeven
                current_wins = 0
                current_losses = 0
        
        return max_wins, max_losses
    
    def _calculate_returns(self, trades: List[Trade], initial_capital: float) -> List[float]:
        """Calculate period returns for risk metrics."""
        if not trades:
            return []
        
        # Sort trades by exit time
        sorted_trades = sorted(trades, key=lambda t: t.exit_time)
        
        returns = []
        running_capital = initial_capital
        
        for trade in sorted_trades:
            period_return = trade.pnl / running_capital if running_capital > 0 else 0
            returns.append(period_return)
            running_capital += trade.pnl
        
        return returns
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe ratio (assuming daily returns)
        excess_return = mean_return - (risk_free_rate / 252)
        return (excess_return / std_return) * np.sqrt(252)
    
    def _calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            return float('inf') if mean_return > 0 else 0.0
        
        downside_deviation = np.std(downside_returns, ddof=1)
        
        if downside_deviation == 0:
            return 0.0
        
        # Annualized Sortino ratio
        excess_return = mean_return - (risk_free_rate / 252)
        return (excess_return / downside_deviation) * np.sqrt(252)
    
    def parse_log_files(self, start_date: Optional[datetime] = None) -> int:
        """Parse audit log files to extract and store trade data."""
        trades_added = 0
        
        # Look for trade log files
        trade_files = list(self.log_dir.glob("trades.log*"))
        
        for log_file in trade_files:
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())
                            
                            # Check if this is a trade exit event
                            if (log_entry.get('event_type') == 'trade_exit' and
                                'audit_data' in log_entry):
                                
                                audit_data = log_entry['audit_data']
                                
                                # Extract trade information
                                if self._is_complete_trade_data(audit_data):
                                    trade = self._create_trade_from_log(audit_data)
                                    if trade and (not start_date or trade.exit_time >= start_date):
                                        self.add_trade(trade)
                                        trades_added += 1
                        
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.debug(f"Skipping invalid log line: {e}")
                            continue
            
            except Exception as e:
                logger.error(f"Error parsing log file {log_file}: {e}")
        
        logger.info(f"Parsed and added {trades_added} trades from log files")
        return trades_added
    
    def _is_complete_trade_data(self, audit_data: Dict[str, Any]) -> bool:
        """Check if audit data contains complete trade information."""
        required_fields = ['symbol', 'quantity', 'price', 'pnl']
        return all(field in audit_data for field in required_fields)
    
    def _create_trade_from_log(self, audit_data: Dict[str, Any]) -> Optional[Trade]:
        """Create a Trade object from audit log data."""
        try:
            # This is a simplified version - in practice, you'd need to match
            # entry and exit events to create complete trades
            return Trade(
                symbol=audit_data['symbol'],
                strategy=audit_data.get('strategy_name', 'unknown'),
                entry_time=datetime.fromisoformat(audit_data.get('entry_time', audit_data['timestamp'])),
                exit_time=datetime.fromisoformat(audit_data['timestamp']),
                entry_price=audit_data.get('entry_price', 0.0),
                exit_price=audit_data['price'],
                quantity=audit_data['quantity'],
                side=audit_data.get('side', 'buy'),
                pnl=audit_data['pnl'],
                pnl_percent=0.0,  # Will be calculated in __post_init__
                exit_reason=audit_data.get('metadata', {}).get('exit_reason', '')
            )
        except Exception as e:
            logger.error(f"Error creating trade from log data: {e}")
            return None


class PerformanceDashboard:
    """Performance dashboard for visualizing trading metrics."""
    
    def __init__(self, analyzer: TradeAnalyzer):
        """Initialize the dashboard."""
        self.analyzer = analyzer
    
    def generate_performance_report(
        self,
        period: AnalyticsPeriod = AnalyticsPeriod.ALL_TIME,
        strategy: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        # Calculate date range based on period
        end_date = datetime.now(timezone.utc)
        start_date = self._get_period_start_date(period, end_date)
        
        # Get trades for the period
        trades = self.analyzer.get_trades(
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            symbol=symbol
        )
        
        # Calculate metrics
        metrics = self.analyzer.calculate_performance_metrics(trades)
        
        # Generate report
        report = {
            "period": period.value,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat()
            },
            "filters": {
                "strategy": strategy,
                "symbol": symbol
            },
            "summary": self._format_summary_metrics(metrics),
            "detailed_metrics": self._format_detailed_metrics(metrics),
            "trade_analysis": self._analyze_trades(trades),
            "recommendations": self._generate_recommendations(metrics, trades)
        }
        
        return report
    
    def _get_period_start_date(self, period: AnalyticsPeriod, end_date: datetime) -> Optional[datetime]:
        """Calculate start date based on period."""
        if period == AnalyticsPeriod.ALL_TIME:
            return None
        
        period_map = {
            AnalyticsPeriod.DAILY: timedelta(days=1),
            AnalyticsPeriod.WEEKLY: timedelta(weeks=1),
            AnalyticsPeriod.MONTHLY: timedelta(days=30),
            AnalyticsPeriod.QUARTERLY: timedelta(days=90),
            AnalyticsPeriod.YEARLY: timedelta(days=365)
        }
        
        return end_date - period_map[period]
    
    def _format_summary_metrics(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Format key summary metrics."""
        return {
            "total_trades": metrics.total_trades,
            "win_rate": f"{metrics.win_rate:.1f}%",
            "profit_factor": f"{metrics.profit_factor:.2f}",
            "net_profit": f"${metrics.net_profit:,.2f}",
            "max_drawdown": f"{metrics.max_drawdown_percent:.1f}%",
            "expectancy": f"${metrics.expectancy:.2f}",
            "sharpe_ratio": f"{metrics.sharpe_ratio:.2f}",
            "avg_r_multiple": f"{metrics.avg_r_multiple:.2f}R"
        }
    
    def _format_detailed_metrics(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Format detailed performance metrics."""
        return {
            "trade_distribution": {
                "winning_trades": metrics.winning_trades,
                "losing_trades": metrics.losing_trades,
                "breakeven_trades": metrics.breakeven_trades,
                "avg_win": f"${metrics.avg_win:.2f}",
                "avg_loss": f"${metrics.avg_loss:.2f}",
                "largest_win": f"${metrics.largest_win:.2f}",
                "largest_loss": f"${metrics.largest_loss:.2f}"
            },
            "risk_metrics": {
                "max_drawdown_absolute": f"${metrics.max_drawdown:,.2f}",
                "max_drawdown_percent": f"{metrics.max_drawdown_percent:.2f}%",
                "recovery_factor": f"{metrics.recovery_factor:.2f}",
                "calmar_ratio": f"{metrics.calmar_ratio:.2f}",
                "sortino_ratio": f"{metrics.sortino_ratio:.2f}"
            },
            "execution_quality": {
                "avg_slippage": f"${metrics.avg_slippage:.4f}",
                "total_commission": f"${metrics.total_commission:.2f}",
                "avg_trade_duration": f"{metrics.avg_trade_duration:.1f} minutes"
            },
            "streaks": {
                "max_consecutive_wins": metrics.max_consecutive_wins,
                "max_consecutive_losses": metrics.max_consecutive_losses
            },
            "kelly_criterion": f"{metrics.kelly_criterion:.2%}"
        }
    
    def _analyze_trades(self, trades: List[Trade]) -> Dict[str, Any]:
        """Analyze trade patterns and distributions."""
        if not trades:
            return {}
        
        # Symbol analysis
        symbol_stats = {}
        for trade in trades:
            if trade.symbol not in symbol_stats:
                symbol_stats[trade.symbol] = {"count": 0, "pnl": 0.0}
            symbol_stats[trade.symbol]["count"] += 1
            symbol_stats[trade.symbol]["pnl"] += trade.pnl
        
        # Strategy analysis
        strategy_stats = {}
        for trade in trades:
            if trade.strategy not in strategy_stats:
                strategy_stats[trade.strategy] = {"count": 0, "pnl": 0.0}
            strategy_stats[trade.strategy]["count"] += 1
            strategy_stats[trade.strategy]["pnl"] += trade.pnl
        
        # Time analysis
        hourly_stats = {}
        for trade in trades:
            hour = trade.entry_time.hour
            if hour not in hourly_stats:
                hourly_stats[hour] = {"count": 0, "pnl": 0.0}
            hourly_stats[hour]["count"] += 1
            hourly_stats[hour]["pnl"] += trade.pnl
        
        return {
            "by_symbol": dict(sorted(symbol_stats.items(), key=lambda x: x[1]["pnl"], reverse=True)[:10]),
            "by_strategy": dict(sorted(strategy_stats.items(), key=lambda x: x[1]["pnl"], reverse=True)),
            "by_hour": dict(sorted(hourly_stats.items()))
        }
    
    def _generate_recommendations(self, metrics: PerformanceMetrics, trades: List[Trade]) -> List[str]:
        """Generate optimization recommendations based on performance."""
        recommendations = []
        
        # Win rate analysis
        if metrics.win_rate < 40:
            recommendations.append("🔴 Low win rate detected. Consider tightening entry criteria or improving signal quality.")
        elif metrics.win_rate > 70:
            recommendations.append("🟢 High win rate suggests good entry timing. Consider increasing position sizes if risk allows.")
        
        # Profit factor analysis
        if metrics.profit_factor < 1.2:
            recommendations.append("🔴 Low profit factor. Focus on cutting losses faster or letting winners run longer.")
        elif metrics.profit_factor > 2.0:
            recommendations.append("🟢 Excellent profit factor. Strategy shows strong edge.")
        
        # Drawdown analysis
        if metrics.max_drawdown_percent > 20:
            recommendations.append("🔴 High drawdown detected. Consider reducing position sizes or improving risk management.")
        elif metrics.max_drawdown_percent < 5:
            recommendations.append("🟡 Very low drawdown may indicate overly conservative position sizing.")
        
        # R-multiple analysis
        if metrics.avg_r_multiple < 1.0:
            recommendations.append("🔴 Average R-multiple below 1.0. Improve risk/reward ratio by adjusting stops and targets.")
        elif metrics.avg_r_multiple > 2.0:
            recommendations.append("🟢 Strong R-multiple suggests good risk management.")
        
        # Consecutive losses
        if metrics.max_consecutive_losses > 5:
            recommendations.append("🔴 High consecutive losses detected. Consider adding circuit breakers or strategy filters.")
        
        # Kelly Criterion
        if metrics.kelly_criterion > 0.25:
            recommendations.append("🟡 Kelly Criterion suggests reducing position size to avoid over-leveraging.")
        elif metrics.kelly_criterion < 0:
            recommendations.append("🔴 Negative Kelly Criterion indicates strategy may not be profitable long-term.")
        
        # Execution quality
        if metrics.avg_slippage > 0.05:
            recommendations.append("🟡 High slippage detected. Consider using limit orders or trading more liquid symbols.")
        
        return recommendations


# Global analytics instance
_analytics_engine: Optional[TradeAnalyzer] = None


def get_analytics_engine() -> TradeAnalyzer:
    """Get the global analytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = TradeAnalyzer()
    return _analytics_engine


def initialize_analytics(log_dir: str = "logs") -> TradeAnalyzer:
    """Initialize the global analytics engine."""
    global _analytics_engine
    _analytics_engine = TradeAnalyzer(log_dir=log_dir)
    return _analytics_engine
