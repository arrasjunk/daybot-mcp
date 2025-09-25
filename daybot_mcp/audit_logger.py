"""
Comprehensive audit logging system for DayBot trading operations.
Provides structured logging for trades, system events, and operational metrics.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import uuid


class LogLevel(str, Enum):
    """Log levels for different types of events."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(str, Enum):
    """Types of events that can be logged."""
    # Trading Events
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    TRADE_PARTIAL_EXIT = "trade_partial_exit"
    STOP_LOSS_HIT = "stop_loss_hit"
    TAKE_PROFIT_HIT = "take_profit_hit"
    TRADE_CANCELLED = "trade_cancelled"
    POSITION_ADJUSTED = "position_adjusted"
    
    # System Events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"
    HEALTH_CHECK = "health_check"
    MARKET_STATUS = "market_status"
    
    # Risk Management Events
    RISK_LIMIT_HIT = "risk_limit_hit"
    POSITION_SIZE_CALCULATED = "position_size_calculated"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    PORTFOLIO_HEAT_WARNING = "portfolio_heat_warning"
    
    # Strategy Events
    STRATEGY_SIGNAL = "strategy_signal"
    SYMBOL_SCAN = "symbol_scan"
    ENTRY_SIGNAL = "entry_signal"
    EXIT_SIGNAL = "exit_signal"
    
    # API Events
    API_CALL = "api_call"
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"
    
    # Performance Events
    PERFORMANCE_METRIC = "performance_metric"
    LATENCY_MEASUREMENT = "latency_measurement"


class AuditLogEntry(BaseModel):
    """Structured audit log entry."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    level: LogLevel
    message: str
    component: str  # Which component generated the log (e.g., "server", "strategy", "risk_manager")
    session_id: Optional[str] = None
    
    # Trading specific fields
    symbol: Optional[str] = None
    side: Optional[str] = None  # "buy", "sell"
    quantity: Optional[float] = None
    price: Optional[float] = None
    order_id: Optional[str] = None
    position_id: Optional[str] = None
    pnl: Optional[float] = None
    
    # Risk management fields
    risk_percent: Optional[float] = None
    portfolio_value: Optional[float] = None
    daily_pnl: Optional[float] = None
    portfolio_heat: Optional[float] = None
    
    # Performance fields
    latency_ms: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Context information
    strategy_name: Optional[str] = None
    user_id: Optional[str] = None
    environment: Optional[str] = None


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add any extra fields from the log record
        if hasattr(record, 'audit_data'):
            log_entry.update(record.audit_data)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class AuditLogger:
    """
    Comprehensive audit logger for trading operations.
    Provides structured logging with multiple output destinations.
    """
    
    def __init__(
        self,
        log_dir: str = "logs",
        session_id: Optional[str] = None,
        environment: str = "development",
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        backup_count: int = 10,
        console_level: LogLevel = LogLevel.INFO,
        file_level: LogLevel = LogLevel.DEBUG
    ):
        """
        Initialize the audit logger.
        
        Args:
            log_dir: Directory to store log files
            session_id: Unique session identifier
            environment: Environment name (development, production, etc.)
            max_file_size: Maximum size of each log file in bytes
            backup_count: Number of backup files to keep
            console_level: Minimum level for console output
            file_level: Minimum level for file output
        """
        self.log_dir = Path(log_dir)
        self.session_id = session_id or str(uuid.uuid4())
        self.environment = environment
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize loggers
        self._setup_loggers(console_level, file_level)
        
        # Log system start
        self.log_system_event(
            EventType.SYSTEM_START,
            "Audit logging system initialized",
            metadata={
                "session_id": self.session_id,
                "environment": environment,
                "log_dir": str(self.log_dir)
            }
        )
    
    def _setup_loggers(self, console_level: LogLevel, file_level: LogLevel):
        """Setup logging handlers and formatters."""
        # Create main logger
        self.logger = logging.getLogger("daybot_audit")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # Clear any existing handlers
        
        # JSON formatter for structured logging
        json_formatter = JSONFormatter()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_level.value))
        console_handler.setFormatter(json_formatter)
        self.logger.addHandler(console_handler)
        
        # File handlers for different log types
        self._setup_file_handlers(json_formatter, file_level)
    
    def _setup_file_handlers(self, formatter: JSONFormatter, file_level: LogLevel):
        """Setup rotating file handlers for different log categories."""
        handlers_config = [
            ("audit", "audit.log", logging.DEBUG),
            ("trades", "trades.log", logging.INFO),
            ("system", "system.log", logging.INFO),
            ("errors", "errors.log", logging.ERROR),
            ("performance", "performance.log", logging.INFO),
        ]
        
        for handler_name, filename, level in handlers_config:
            file_path = self.log_dir / filename
            handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            handler.setLevel(max(level, getattr(logging, file_level.value)))
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _log_entry(self, entry: AuditLogEntry):
        """Log an audit entry."""
        # Set session and environment if not already set
        if not entry.session_id:
            entry.session_id = self.session_id
        if not entry.environment:
            entry.environment = self.environment
        
        # Convert to dict for logging
        audit_data = entry.dict(exclude_none=True)
        
        # Log with appropriate level
        level = getattr(logging, entry.level.value)
        self.logger.log(
            level,
            entry.message,
            extra={"audit_data": audit_data}
        )
    
    def log_trade_entry(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str,
        strategy_name: str,
        risk_percent: float,
        message: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log a trade entry event."""
        entry = AuditLogEntry(
            event_type=EventType.TRADE_ENTRY,
            level=LogLevel.INFO,
            message=message or f"Trade entry: {side} {quantity} {symbol} @ ${price:.2f}",
            component="trading",
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_id=order_id,
            risk_percent=risk_percent,
            strategy_name=strategy_name,
            metadata=metadata or {}
        )
        self._log_entry(entry)
    
    def log_trade_exit(
        self,
        symbol: str,
        quantity: float,
        price: float,
        pnl: float,
        order_id: str,
        reason: str,
        message: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log a trade exit event."""
        entry = AuditLogEntry(
            event_type=EventType.TRADE_EXIT,
            level=LogLevel.INFO,
            message=message or f"Trade exit: {symbol} {quantity} @ ${price:.2f}, P&L: ${pnl:.2f}",
            component="trading",
            symbol=symbol,
            quantity=quantity,
            price=price,
            pnl=pnl,
            order_id=order_id,
            metadata={**(metadata or {}), "exit_reason": reason}
        )
        self._log_entry(entry)
    
    def log_risk_event(
        self,
        event_type: EventType,
        message: str,
        portfolio_value: float = None,
        daily_pnl: float = None,
        portfolio_heat: float = None,
        metadata: Dict[str, Any] = None
    ):
        """Log a risk management event."""
        entry = AuditLogEntry(
            event_type=event_type,
            level=LogLevel.WARNING if "limit" in event_type.value else LogLevel.INFO,
            message=message,
            component="risk_manager",
            portfolio_value=portfolio_value,
            daily_pnl=daily_pnl,
            portfolio_heat=portfolio_heat,
            metadata=metadata or {}
        )
        self._log_entry(entry)
    
    def log_strategy_event(
        self,
        event_type: EventType,
        message: str,
        strategy_name: str,
        symbol: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log a strategy event."""
        entry = AuditLogEntry(
            event_type=event_type,
            level=LogLevel.INFO,
            message=message,
            component="strategy",
            strategy_name=strategy_name,
            symbol=symbol,
            metadata=metadata or {}
        )
        self._log_entry(entry)
    
    def log_system_event(
        self,
        event_type: EventType,
        message: str,
        level: LogLevel = LogLevel.INFO,
        metadata: Dict[str, Any] = None
    ):
        """Log a system event."""
        entry = AuditLogEntry(
            event_type=event_type,
            level=level,
            message=message,
            component="system",
            metadata=metadata or {}
        )
        self._log_entry(entry)
    
    def log_api_call(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
        message: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log an API call event."""
        entry = AuditLogEntry(
            event_type=EventType.API_CALL,
            level=LogLevel.DEBUG,
            message=message or f"API call: {method} {endpoint} - {status_code} ({latency_ms:.1f}ms)",
            component="api_client",
            latency_ms=latency_ms,
            metadata={
                **(metadata or {}),
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code
            }
        )
        self._log_entry(entry)
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        message: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log a performance metric."""
        entry = AuditLogEntry(
            event_type=EventType.PERFORMANCE_METRIC,
            level=LogLevel.DEBUG,
            message=message or f"Performance metric: {metric_name} = {value} {unit}",
            component="performance",
            metadata={
                **(metadata or {}),
                "metric_name": metric_name,
                "value": value,
                "unit": unit
            }
        )
        self._log_entry(entry)
    
    def log_error(
        self,
        message: str,
        component: str,
        error: Exception = None,
        metadata: Dict[str, Any] = None
    ):
        """Log an error event."""
        error_metadata = metadata or {}
        if error:
            error_metadata.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
        
        entry = AuditLogEntry(
            event_type=EventType.SYSTEM_ERROR,
            level=LogLevel.ERROR,
            message=message,
            component=component,
            metadata=error_metadata
        )
        self._log_entry(entry)
    
    def get_session_logs(self, event_types: List[EventType] = None) -> List[Dict[str, Any]]:
        """
        Retrieve logs for the current session.
        Note: This is a placeholder - in production you'd query from a database or log aggregation system.
        """
        # This would typically query a log database or parse log files
        # For now, return empty list as this requires additional infrastructure
        return []
    
    def close(self):
        """Close the audit logger and clean up resources."""
        self.log_system_event(
            EventType.SYSTEM_STOP,
            "Audit logging system shutting down"
        )
        
        # Close all handlers
        for handler in self.logger.handlers:
            handler.close()
        
        self.logger.handlers.clear()


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        raise RuntimeError("Audit logger not initialized. Call initialize_audit_logger() first.")
    return _audit_logger


def initialize_audit_logger(
    log_dir: str = "logs",
    session_id: Optional[str] = None,
    environment: str = "development",
    **kwargs
) -> AuditLogger:
    """Initialize the global audit logger."""
    global _audit_logger
    _audit_logger = AuditLogger(
        log_dir=log_dir,
        session_id=session_id,
        environment=environment,
        **kwargs
    )
    return _audit_logger


def close_audit_logger():
    """Close the global audit logger."""
    global _audit_logger
    if _audit_logger:
        _audit_logger.close()
        _audit_logger = None
