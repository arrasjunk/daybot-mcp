"""
Log analysis and reporting utilities for DayBot audit logs.
Provides tools to analyze trading performance, system health, and generate reports.
"""

import json
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re
from collections import defaultdict, Counter

from .audit_logger import EventType, LogLevel


@dataclass
class TradingMetrics:
    """Trading performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    total_volume: float
    avg_trade_duration: float


@dataclass
class SystemMetrics:
    """System performance metrics."""
    uptime_hours: float
    total_api_calls: int
    avg_api_latency: float
    error_count: int
    error_rate: float
    rate_limit_hits: int
    health_check_failures: int


@dataclass
class RiskMetrics:
    """Risk management metrics."""
    max_daily_loss: float
    max_portfolio_heat: float
    risk_limit_violations: int
    avg_position_size: float
    max_position_size: float
    position_size_violations: int


class LogAnalyzer:
    """
    Analyze DayBot audit logs and generate performance reports.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize the log analyzer.
        
        Args:
            log_dir: Directory containing log files
        """
        self.log_dir = Path(log_dir)
        self.logs_cache: List[Dict[str, Any]] = []
        self.cache_timestamp: Optional[datetime] = None
    
    def _load_logs(self, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   force_reload: bool = False) -> List[Dict[str, Any]]:
        """
        Load and parse log files.
        
        Args:
            start_date: Filter logs from this date
            end_date: Filter logs until this date
            force_reload: Force reload even if cache is fresh
            
        Returns:
            List of parsed log entries
        """
        # Check if we need to reload cache
        if (not force_reload and 
            self.logs_cache and 
            self.cache_timestamp and 
            datetime.now() - self.cache_timestamp < timedelta(minutes=5)):
            return self._filter_logs_by_date(self.logs_cache, start_date, end_date)
        
        logs = []
        
        # Find all log files
        log_files = list(self.log_dir.glob("*.log*"))
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            log_entry = json.loads(line)
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            # Skip malformed JSON lines
                            continue
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")
                continue
        
        # Sort by timestamp
        logs.sort(key=lambda x: x.get('timestamp', ''))
        
        # Update cache
        self.logs_cache = logs
        self.cache_timestamp = datetime.now()
        
        return self._filter_logs_by_date(logs, start_date, end_date)
    
    def _filter_logs_by_date(self, 
                            logs: List[Dict[str, Any]], 
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Filter logs by date range."""
        if not start_date and not end_date:
            return logs
        
        filtered_logs = []
        for log in logs:
            try:
                log_time = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
                
                if start_date and log_time < start_date:
                    continue
                if end_date and log_time > end_date:
                    continue
                
                filtered_logs.append(log)
            except (ValueError, TypeError):
                # Skip logs with invalid timestamps
                continue
        
        return filtered_logs
    
    def get_trading_metrics(self, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> TradingMetrics:
        """
        Calculate trading performance metrics.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            TradingMetrics object with calculated metrics
        """
        logs = self._load_logs(start_date, end_date)
        
        # Filter for trade events
        trade_entries = [log for log in logs if log.get('event_type') == EventType.TRADE_ENTRY.value]
        trade_exits = [log for log in logs if log.get('event_type') == EventType.TRADE_EXIT.value]
        
        # Calculate basic metrics
        total_trades = len(trade_exits)
        if total_trades == 0:
            return TradingMetrics(
                total_trades=0, winning_trades=0, losing_trades=0, win_rate=0.0,
                total_pnl=0.0, avg_win=0.0, avg_loss=0.0, profit_factor=0.0,
                max_drawdown=0.0, sharpe_ratio=0.0, total_volume=0.0, avg_trade_duration=0.0
            )
        
        # Analyze P&L
        pnls = [log.get('pnl', 0) for log in trade_exits if log.get('pnl') is not None]
        winning_trades = len([pnl for pnl in pnls if pnl > 0])
        losing_trades = len([pnl for pnl in pnls if pnl < 0])
        
        total_pnl = sum(pnls)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        wins = [pnl for pnl in pnls if pnl > 0]
        losses = [pnl for pnl in pnls if pnl < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf')
        
        # Calculate drawdown
        cumulative_pnl = []
        running_total = 0
        for pnl in pnls:
            running_total += pnl
            cumulative_pnl.append(running_total)
        
        max_drawdown = 0.0
        if cumulative_pnl:
            peak = cumulative_pnl[0]
            for value in cumulative_pnl:
                if value > peak:
                    peak = value
                drawdown = peak - value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        # Calculate Sharpe ratio (simplified)
        if len(pnls) > 1:
            mean_return = sum(pnls) / len(pnls)
            variance = sum((pnl - mean_return) ** 2 for pnl in pnls) / (len(pnls) - 1)
            std_dev = variance ** 0.5
            sharpe_ratio = mean_return / std_dev if std_dev > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Calculate volume
        total_volume = sum(log.get('quantity', 0) * log.get('price', 0) 
                          for log in trade_entries if log.get('quantity') and log.get('price'))
        
        # Calculate average trade duration (placeholder - would need entry/exit matching)
        avg_trade_duration = 0.0  # Would require matching entries to exits
        
        return TradingMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            total_volume=total_volume,
            avg_trade_duration=avg_trade_duration
        )
    
    def get_system_metrics(self, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> SystemMetrics:
        """
        Calculate system performance metrics.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            SystemMetrics object with calculated metrics
        """
        logs = self._load_logs(start_date, end_date)
        
        # Calculate uptime
        system_starts = [log for log in logs if log.get('event_type') == EventType.SYSTEM_START.value]
        system_stops = [log for log in logs if log.get('event_type') == EventType.SYSTEM_STOP.value]
        
        uptime_hours = 0.0
        if system_starts:
            start_time = datetime.fromisoformat(system_starts[0].get('timestamp', '').replace('Z', '+00:00'))
            end_time = datetime.now(timezone.utc)
            if system_stops:
                end_time = datetime.fromisoformat(system_stops[-1].get('timestamp', '').replace('Z', '+00:00'))
            uptime_hours = (end_time - start_time).total_seconds() / 3600
        
        # API metrics
        api_calls = [log for log in logs if log.get('event_type') == EventType.API_CALL.value]
        total_api_calls = len(api_calls)
        
        latencies = [log.get('latency_ms', 0) for log in api_calls if log.get('latency_ms')]
        avg_api_latency = sum(latencies) / len(latencies) if latencies else 0.0
        
        # Error metrics
        errors = [log for log in logs if log.get('level') == LogLevel.ERROR.value]
        error_count = len(errors)
        error_rate = error_count / len(logs) if logs else 0.0
        
        # Rate limit hits
        rate_limit_hits = len([log for log in logs if log.get('event_type') == EventType.RATE_LIMIT.value])
        
        # Health check failures
        health_checks = [log for log in logs if log.get('event_type') == EventType.HEALTH_CHECK.value]
        health_check_failures = len([log for log in health_checks if 'fail' in log.get('message', '').lower()])
        
        return SystemMetrics(
            uptime_hours=uptime_hours,
            total_api_calls=total_api_calls,
            avg_api_latency=avg_api_latency,
            error_count=error_count,
            error_rate=error_rate,
            rate_limit_hits=rate_limit_hits,
            health_check_failures=health_check_failures
        )
    
    def get_risk_metrics(self, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> RiskMetrics:
        """
        Calculate risk management metrics.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            RiskMetrics object with calculated metrics
        """
        logs = self._load_logs(start_date, end_date)
        
        # Risk events
        risk_events = [log for log in logs if 'risk' in log.get('event_type', '').lower()]
        
        # Daily loss tracking
        daily_losses = [log.get('daily_pnl', 0) for log in risk_events if log.get('daily_pnl')]
        max_daily_loss = min(daily_losses) if daily_losses else 0.0
        
        # Portfolio heat tracking
        portfolio_heats = [log.get('portfolio_heat', 0) for log in risk_events if log.get('portfolio_heat')]
        max_portfolio_heat = max(portfolio_heats) if portfolio_heats else 0.0
        
        # Risk limit violations
        risk_limit_violations = len([log for log in logs if log.get('event_type') == EventType.RISK_LIMIT_HIT.value])
        
        # Position sizing
        trade_entries = [log for log in logs if log.get('event_type') == EventType.TRADE_ENTRY.value]
        position_sizes = [log.get('quantity', 0) * log.get('price', 0) for log in trade_entries 
                         if log.get('quantity') and log.get('price')]
        
        avg_position_size = sum(position_sizes) / len(position_sizes) if position_sizes else 0.0
        max_position_size = max(position_sizes) if position_sizes else 0.0
        
        # Position size violations (placeholder - would need risk limits configuration)
        position_size_violations = 0
        
        return RiskMetrics(
            max_daily_loss=max_daily_loss,
            max_portfolio_heat=max_portfolio_heat,
            risk_limit_violations=risk_limit_violations,
            avg_position_size=avg_position_size,
            max_position_size=max_position_size,
            position_size_violations=position_size_violations
        )
    
    def get_symbol_performance(self, 
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics by symbol.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with symbol performance data
        """
        logs = self._load_logs(start_date, end_date)
        
        # Group by symbol
        symbol_data = defaultdict(lambda: {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'total_volume': 0.0,
            'avg_price': 0.0
        })
        
        trade_exits = [log for log in logs if log.get('event_type') == EventType.TRADE_EXIT.value]
        
        for log in trade_exits:
            symbol = log.get('symbol')
            if not symbol:
                continue
            
            pnl = log.get('pnl', 0)
            quantity = log.get('quantity', 0)
            price = log.get('price', 0)
            
            symbol_data[symbol]['trades'] += 1
            symbol_data[symbol]['total_pnl'] += pnl
            symbol_data[symbol]['total_volume'] += quantity * price
            
            if pnl > 0:
                symbol_data[symbol]['wins'] += 1
            elif pnl < 0:
                symbol_data[symbol]['losses'] += 1
        
        # Calculate derived metrics
        for symbol, data in symbol_data.items():
            if data['trades'] > 0:
                data['win_rate'] = data['wins'] / data['trades']
                data['avg_pnl'] = data['total_pnl'] / data['trades']
            else:
                data['win_rate'] = 0.0
                data['avg_pnl'] = 0.0
        
        return dict(symbol_data)
    
    def generate_daily_report(self, date: datetime = None) -> Dict[str, Any]:
        """
        Generate a comprehensive daily trading report.
        
        Args:
            date: Date for the report (defaults to today)
            
        Returns:
            Dictionary containing the daily report
        """
        if date is None:
            date = datetime.now(timezone.utc).date()
        
        start_date = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=1)
        
        trading_metrics = self.get_trading_metrics(start_date, end_date)
        system_metrics = self.get_system_metrics(start_date, end_date)
        risk_metrics = self.get_risk_metrics(start_date, end_date)
        symbol_performance = self.get_symbol_performance(start_date, end_date)
        
        return {
            'date': date.isoformat(),
            'trading_metrics': trading_metrics.__dict__,
            'system_metrics': system_metrics.__dict__,
            'risk_metrics': risk_metrics.__dict__,
            'symbol_performance': symbol_performance,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    def export_logs_to_csv(self, 
                          output_file: str,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          event_types: Optional[List[EventType]] = None):
        """
        Export logs to CSV format for external analysis.
        
        Args:
            output_file: Path to output CSV file
            start_date: Start date for export
            end_date: End date for export
            event_types: Filter by specific event types
        """
        logs = self._load_logs(start_date, end_date)
        
        if event_types:
            event_type_values = [et.value for et in event_types]
            logs = [log for log in logs if log.get('event_type') in event_type_values]
        
        if not logs:
            print("No logs found for the specified criteria")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(logs)
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        print(f"Exported {len(logs)} log entries to {output_file}")
    
    def get_error_summary(self, 
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get a summary of errors and issues.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with error summary
        """
        logs = self._load_logs(start_date, end_date)
        
        # Filter for errors and warnings
        error_logs = [log for log in logs if log.get('level') in [LogLevel.ERROR.value, LogLevel.WARNING.value]]
        
        # Group by component and error type
        error_by_component = Counter(log.get('component', 'unknown') for log in error_logs)
        error_by_type = Counter(log.get('event_type', 'unknown') for log in error_logs)
        
        # Recent errors (last 24 hours)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_errors = []
        
        for log in error_logs:
            try:
                log_time = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
                if log_time > recent_cutoff:
                    recent_errors.append({
                        'timestamp': log.get('timestamp'),
                        'level': log.get('level'),
                        'component': log.get('component'),
                        'message': log.get('message'),
                        'event_type': log.get('event_type')
                    })
            except (ValueError, TypeError):
                continue
        
        return {
            'total_errors': len(error_logs),
            'errors_by_component': dict(error_by_component),
            'errors_by_type': dict(error_by_type),
            'recent_errors_24h': len(recent_errors),
            'recent_error_details': recent_errors[-10:],  # Last 10 recent errors
            'analysis_period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            }
        }
