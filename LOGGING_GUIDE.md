# DayBot Comprehensive Logging System

## Overview

The DayBot trading system now includes a comprehensive audit logging system designed to provide detailed tracking and analysis of all trading activities, system events, and operational metrics. This system enables thorough auditing, performance analysis, and debugging capabilities.

## Features

### 🔍 **Structured Logging**
- JSON-formatted logs for easy parsing and analysis
- Consistent schema across all log entries
- Hierarchical event categorization
- Rich metadata support

### 📊 **Trade Activity Logging**
- Complete trade lifecycle tracking (entry, exit, adjustments)
- Position sizing and risk management decisions
- P&L calculations and performance metrics
- Order execution details and timing

### 🛡️ **Risk Management Logging**
- Risk limit violations and warnings
- Portfolio heat monitoring
- Daily loss tracking
- Position size calculations

### 🔧 **System Event Logging**
- Health checks and system status
- API call monitoring and latency tracking
- Error tracking and debugging information
- Strategy execution events

### 📈 **Performance Analytics**
- Trading metrics calculation (win rate, Sharpe ratio, etc.)
- System performance monitoring
- Error analysis and reporting
- Symbol-level performance tracking

## Architecture

### Core Components

1. **AuditLogger** (`audit_logger.py`)
   - Main logging interface
   - Structured log entry creation
   - Multiple output destinations
   - Log rotation and archival

2. **LogAnalyzer** (`log_analyzer.py`)
   - Log parsing and analysis
   - Performance metrics calculation
   - Report generation
   - Data export capabilities

3. **Server Integration** (`server.py`)
   - Automatic logging of all API endpoints
   - Trade event tracking
   - System health monitoring

## Usage Guide

### Basic Setup

The logging system is automatically initialized when the DayBot server starts:

```python
from daybot_mcp.audit_logger import initialize_audit_logger, get_audit_logger

# Initialize the audit logger
initialize_audit_logger(
    log_dir="logs",
    environment="production",
    console_level=LogLevel.INFO,
    file_level=LogLevel.DEBUG
)

# Get the logger instance
audit_logger = get_audit_logger()
```

### Logging Trade Events

```python
# Log a trade entry
audit_logger.log_trade_entry(
    symbol="AAPL",
    side="buy",
    quantity=100,
    price=150.25,
    order_id="order_123",
    strategy_name="momentum",
    risk_percent=0.01,
    metadata={"stop_loss": 145.00, "take_profit": 160.00}
)

# Log a trade exit
audit_logger.log_trade_exit(
    symbol="AAPL",
    quantity=100,
    price=155.75,
    pnl=550.00,
    order_id="order_124",
    reason="take_profit_hit",
    metadata={"hold_time_minutes": 45}
)
```

### Logging System Events

```python
# Log system events
audit_logger.log_system_event(
    EventType.HEALTH_CHECK,
    "System health check completed",
    metadata={"status": "healthy", "response_time_ms": 125}
)

# Log errors
audit_logger.log_error(
    "API connection failed",
    "alpaca_client",
    error=exception_object,
    metadata={"endpoint": "/v2/positions", "retry_count": 3}
)
```

### Logging Strategy Events

```python
# Log strategy decisions
audit_logger.log_strategy_event(
    EventType.ENTRY_SIGNAL,
    "Momentum breakout signal detected",
    "momentum_strategy",
    symbol="TSLA",
    metadata={
        "price": 245.50,
        "volume": 1500000,
        "momentum_score": 0.85
    }
)
```

## Log Analysis and Reporting

### REST API Endpoints

The system provides several REST endpoints for log analysis:

#### Daily Report
```bash
GET /audit/daily_report?date=2024-01-15
```

#### Trading Metrics
```bash
GET /audit/trading_metrics?start_date=2024-01-01&end_date=2024-01-31
```

#### System Metrics
```bash
GET /audit/system_metrics?start_date=2024-01-01&end_date=2024-01-31
```

#### Risk Metrics
```bash
GET /audit/risk_metrics?start_date=2024-01-01&end_date=2024-01-31
```

#### Symbol Performance
```bash
GET /audit/symbol_performance?start_date=2024-01-01&end_date=2024-01-31
```

#### Error Summary
```bash
GET /audit/error_summary?start_date=2024-01-01&end_date=2024-01-31
```

#### Export Logs
```bash
POST /audit/export_logs
{
    "output_file": "trading_logs_2024_01.csv",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "event_types": ["trade_entry", "trade_exit"]
}
```

### Programmatic Analysis

```python
from daybot_mcp.log_analyzer import LogAnalyzer
from datetime import datetime, timedelta

# Initialize analyzer
analyzer = LogAnalyzer("logs")

# Get trading metrics for the last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
metrics = analyzer.get_trading_metrics(start_date, end_date)

print(f"Total trades: {metrics.total_trades}")
print(f"Win rate: {metrics.win_rate:.2%}")
print(f"Total P&L: ${metrics.total_pnl:.2f}")
print(f"Sharpe ratio: {metrics.sharpe_ratio:.2f}")

# Generate daily report
report = analyzer.generate_daily_report()
print(f"Daily report: {report}")

# Export logs to CSV
analyzer.export_logs_to_csv(
    "analysis.csv",
    start_date,
    end_date,
    [EventType.TRADE_ENTRY, EventType.TRADE_EXIT]
)
```

## Event Types

The system supports the following event types:

### Trading Events
- `TRADE_ENTRY` - New position opened
- `TRADE_EXIT` - Position closed
- `TRADE_PARTIAL_EXIT` - Partial position closure
- `STOP_LOSS_HIT` - Stop loss triggered
- `TAKE_PROFIT_HIT` - Take profit triggered
- `TRADE_CANCELLED` - Order cancelled
- `POSITION_ADJUSTED` - Position modified

### System Events
- `SYSTEM_START` - System startup
- `SYSTEM_STOP` - System shutdown
- `SYSTEM_ERROR` - System error occurred
- `HEALTH_CHECK` - Health check performed
- `MARKET_STATUS` - Market status update

### Risk Management Events
- `RISK_LIMIT_HIT` - Risk limit exceeded
- `POSITION_SIZE_CALCULATED` - Position size determined
- `DAILY_LOSS_LIMIT` - Daily loss limit reached
- `PORTFOLIO_HEAT_WARNING` - Portfolio heat warning

### Strategy Events
- `STRATEGY_SIGNAL` - Strategy signal generated
- `SYMBOL_SCAN` - Symbol scanning performed
- `ENTRY_SIGNAL` - Entry signal detected
- `EXIT_SIGNAL` - Exit signal detected

### API Events
- `API_CALL` - API call made
- `API_ERROR` - API error occurred
- `RATE_LIMIT` - Rate limit hit

### Performance Events
- `PERFORMANCE_METRIC` - Performance metric recorded
- `LATENCY_MEASUREMENT` - Latency measured

## Log File Structure

The system creates separate log files for different categories:

```
logs/
├── audit.log          # All events (comprehensive)
├── trades.log         # Trading-specific events
├── system.log         # System events
├── errors.log         # Error events only
└── performance.log    # Performance metrics
```

Each log file uses rotating file handlers with configurable size limits and backup counts.

## Configuration

### Environment Variables

```bash
# Log configuration
DAYBOT_LOG_LEVEL=INFO
DAYBOT_LOG_DIR=logs
DAYBOT_LOG_MAX_SIZE=52428800  # 50MB
DAYBOT_LOG_BACKUP_COUNT=10
```

### Programmatic Configuration

```python
# Initialize with custom settings
audit_logger = initialize_audit_logger(
    log_dir="custom_logs",
    session_id="trading_session_001",
    environment="production",
    max_file_size=100 * 1024 * 1024,  # 100MB
    backup_count=20,
    console_level=LogLevel.WARNING,
    file_level=LogLevel.DEBUG
)
```

## Performance Considerations

### Log Rotation
- Automatic log rotation when files reach size limit
- Configurable number of backup files
- Compressed backup files to save disk space

### Async Logging
- Non-blocking log operations
- Minimal impact on trading performance
- Buffered writes for efficiency

### Storage Requirements
- Approximately 1-5MB per day for typical trading activity
- JSON format is human-readable but larger than binary
- Consider log retention policies for long-term storage

## Best Practices

### 1. Use Appropriate Log Levels
```python
# Use DEBUG for detailed troubleshooting
audit_logger.log_system_event(EventType.API_CALL, "API call details", LogLevel.DEBUG)

# Use INFO for normal operations
audit_logger.log_trade_entry(...)

# Use WARNING for concerning but non-critical issues
audit_logger.log_risk_event(EventType.PORTFOLIO_HEAT_WARNING, "High portfolio heat")

# Use ERROR for failures
audit_logger.log_error("Trade execution failed", "trading")
```

### 2. Include Rich Metadata
```python
# Good: Rich context
audit_logger.log_trade_entry(
    symbol="AAPL",
    side="buy",
    quantity=100,
    price=150.25,
    order_id="order_123",
    strategy_name="momentum",
    risk_percent=0.01,
    metadata={
        "entry_reason": "breakout_above_resistance",
        "technical_indicators": {
            "rsi": 65.2,
            "macd": 1.25,
            "volume_ratio": 2.1
        },
        "market_conditions": "trending_up"
    }
)
```

### 3. Monitor Log Health
```python
# Regular log analysis
analyzer = LogAnalyzer("logs")
error_summary = analyzer.get_error_summary()

if error_summary["total_errors"] > 100:
    # Alert on high error count
    send_alert("High error count detected")
```

### 4. Use Session IDs
- Group related activities with session IDs
- Easier to trace complete trading sessions
- Better correlation of events

## Troubleshooting

### Common Issues

1. **Logger Not Initialized**
   ```python
   # Error: RuntimeError: Audit logger not initialized
   # Solution: Call initialize_audit_logger() first
   initialize_audit_logger()
   ```

2. **Permission Errors**
   ```bash
   # Ensure log directory is writable
   chmod 755 logs/
   ```

3. **Disk Space Issues**
   ```python
   # Monitor disk usage and adjust retention
   analyzer = LogAnalyzer("logs")
   # Implement log cleanup based on age/size
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```python
initialize_audit_logger(
    console_level=LogLevel.DEBUG,
    file_level=LogLevel.DEBUG
)
```

## Integration Examples

### Strategy Integration

```python
class MyTradingStrategy:
    def __init__(self):
        self.audit_logger = get_audit_logger()
    
    async def execute_trade(self, symbol, signal):
        # Log the signal
        self.audit_logger.log_strategy_event(
            EventType.ENTRY_SIGNAL,
            f"Signal detected for {symbol}",
            "my_strategy",
            symbol=symbol,
            metadata=signal.__dict__
        )
        
        # Execute trade
        result = await self.place_order(symbol, signal)
        
        # Log the result
        if result.success:
            self.audit_logger.log_trade_entry(
                symbol=symbol,
                side=signal.side,
                quantity=result.quantity,
                price=result.price,
                order_id=result.order_id,
                strategy_name="my_strategy",
                risk_percent=signal.risk_percent
            )
```

### Risk Manager Integration

```python
class RiskManager:
    def __init__(self):
        self.audit_logger = get_audit_logger()
    
    def check_position_size(self, symbol, size, portfolio_value):
        # Calculate position size
        max_size = portfolio_value * 0.02  # 2% max position
        
        if size > max_size:
            self.audit_logger.log_risk_event(
                EventType.RISK_LIMIT_HIT,
                f"Position size limit exceeded for {symbol}",
                metadata={
                    "requested_size": size,
                    "max_allowed": max_size,
                    "portfolio_value": portfolio_value
                }
            )
            return False
        
        return True
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Error Rate**: Errors per hour/day
2. **Trade Success Rate**: Successful vs failed trades
3. **System Uptime**: Health check success rate
4. **API Latency**: Average response times
5. **Risk Violations**: Risk limit hits per day

### Sample Monitoring Script

```python
import asyncio
from datetime import datetime, timedelta

async def monitor_system():
    analyzer = LogAnalyzer("logs")
    
    # Check last hour for issues
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    error_summary = analyzer.get_error_summary(start_time, end_time)
    
    if error_summary["total_errors"] > 10:
        await send_alert(f"High error count: {error_summary['total_errors']}")
    
    system_metrics = analyzer.get_system_metrics(start_time, end_time)
    
    if system_metrics.avg_api_latency > 1000:  # 1 second
        await send_alert(f"High API latency: {system_metrics.avg_api_latency}ms")

# Run monitoring every 15 minutes
asyncio.create_task(monitor_system())
```

This comprehensive logging system provides the foundation for robust trading system monitoring, analysis, and continuous improvement. The structured approach ensures that all critical events are captured and can be analyzed for performance optimization and risk management.
