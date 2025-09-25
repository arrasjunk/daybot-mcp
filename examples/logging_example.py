#!/usr/bin/env python3
"""
Example script demonstrating the DayBot comprehensive logging system.
This shows how to use the audit logger and log analyzer for trading activities.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from daybot_mcp.audit_logger import (
    initialize_audit_logger,
    get_audit_logger,
    close_audit_logger,
    EventType,
    LogLevel
)
from daybot_mcp.log_analyzer import LogAnalyzer


async def demonstrate_logging():
    """Demonstrate various logging capabilities."""
    
    print("🚀 DayBot Logging System Demo")
    print("=" * 50)
    
    # Initialize the audit logger
    print("1. Initializing audit logger...")
    audit_logger = initialize_audit_logger(
        log_dir="logs/demo",
        session_id="demo_session_001",
        environment="demo",
        console_level=LogLevel.INFO,
        file_level=LogLevel.DEBUG
    )
    
    print("✅ Audit logger initialized")
    
    # Demonstrate system events
    print("\n2. Logging system events...")
    audit_logger.log_system_event(
        EventType.SYSTEM_START,
        "Demo system started",
        metadata={"demo_mode": True, "version": "1.0.0"}
    )
    
    # Demonstrate strategy events
    print("3. Logging strategy events...")
    audit_logger.log_strategy_event(
        EventType.SYMBOL_SCAN,
        "Scanning for momentum opportunities",
        "demo_strategy",
        metadata={"scan_criteria": {"volume_min": 1000000, "price_min": 10.0}}
    )
    
    # Demonstrate trade logging
    print("4. Logging trade activities...")
    
    # Simulate a series of trades
    trades = [
        {"symbol": "AAPL", "side": "buy", "quantity": 100, "price": 150.25, "success": True},
        {"symbol": "TSLA", "side": "buy", "quantity": 50, "price": 245.75, "success": True},
        {"symbol": "MSFT", "side": "buy", "quantity": 75, "price": 380.50, "success": False},
        {"symbol": "GOOGL", "side": "buy", "quantity": 25, "price": 2750.00, "success": True},
    ]
    
    for i, trade in enumerate(trades):
        if trade["success"]:
            audit_logger.log_trade_entry(
                symbol=trade["symbol"],
                side=trade["side"],
                quantity=trade["quantity"],
                price=trade["price"],
                order_id=f"demo_order_{i+1}",
                strategy_name="demo_strategy",
                risk_percent=0.01,
                metadata={
                    "entry_reason": "momentum_breakout",
                    "confidence": 0.85,
                    "market_conditions": "bullish"
                }
            )
            print(f"   ✅ Logged entry for {trade['symbol']}")
        else:
            audit_logger.log_error(
                f"Trade entry failed for {trade['symbol']}",
                "demo_strategy",
                metadata={"symbol": trade["symbol"], "reason": "insufficient_buying_power"}
            )
            print(f"   ❌ Logged error for {trade['symbol']}")
    
    # Simulate some exits
    print("5. Logging trade exits...")
    exits = [
        {"symbol": "AAPL", "quantity": 100, "price": 155.75, "pnl": 550.00},
        {"symbol": "TSLA", "quantity": 50, "price": 240.25, "pnl": -275.00},
    ]
    
    for exit_trade in exits:
        audit_logger.log_trade_exit(
            symbol=exit_trade["symbol"],
            quantity=exit_trade["quantity"],
            price=exit_trade["price"],
            pnl=exit_trade["pnl"],
            order_id=f"exit_{exit_trade['symbol'].lower()}",
            reason="take_profit" if exit_trade["pnl"] > 0 else "stop_loss",
            metadata={"hold_time_minutes": 45}
        )
        print(f"   📈 Logged exit for {exit_trade['symbol']} (P&L: ${exit_trade['pnl']:.2f})")
    
    # Demonstrate risk events
    print("6. Logging risk management events...")
    audit_logger.log_risk_event(
        EventType.PORTFOLIO_HEAT_WARNING,
        "Portfolio heat approaching limit",
        portfolio_value=100000.0,
        portfolio_heat=12.5,
        metadata={"heat_limit": 15.0, "current_positions": 4}
    )
    
    # Demonstrate API logging
    print("7. Logging API events...")
    audit_logger.log_api_call(
        endpoint="/v2/positions",
        method="GET",
        status_code=200,
        latency_ms=125.5,
        metadata={"response_size": 1024}
    )
    
    # Demonstrate performance metrics
    print("8. Logging performance metrics...")
    audit_logger.log_performance_metric(
        metric_name="strategy_cycle_time",
        value=2.5,
        unit="seconds",
        metadata={"cycle_number": 42}
    )
    
    print("\n✅ All logging demonstrations completed!")
    
    # Wait a moment for logs to be written
    await asyncio.sleep(1)
    
    # Demonstrate log analysis
    print("\n" + "=" * 50)
    print("📊 Log Analysis Demo")
    print("=" * 50)
    
    analyzer = LogAnalyzer("logs/demo")
    
    # Get trading metrics
    print("1. Trading Metrics:")
    trading_metrics = analyzer.get_trading_metrics()
    print(f"   Total trades: {trading_metrics.total_trades}")
    print(f"   Winning trades: {trading_metrics.winning_trades}")
    print(f"   Win rate: {trading_metrics.win_rate:.2%}")
    print(f"   Total P&L: ${trading_metrics.total_pnl:.2f}")
    print(f"   Average win: ${trading_metrics.avg_win:.2f}")
    print(f"   Average loss: ${trading_metrics.avg_loss:.2f}")
    
    # Get system metrics
    print("\n2. System Metrics:")
    system_metrics = analyzer.get_system_metrics()
    print(f"   Total API calls: {system_metrics.total_api_calls}")
    print(f"   Average API latency: {system_metrics.avg_api_latency:.1f}ms")
    print(f"   Error count: {system_metrics.error_count}")
    print(f"   Error rate: {system_metrics.error_rate:.2%}")
    
    # Get symbol performance
    print("\n3. Symbol Performance:")
    symbol_performance = analyzer.get_symbol_performance()
    for symbol, data in symbol_performance.items():
        print(f"   {symbol}: {data['trades']} trades, "
              f"Win rate: {data['win_rate']:.2%}, "
              f"Total P&L: ${data['total_pnl']:.2f}")
    
    # Get error summary
    print("\n4. Error Summary:")
    error_summary = analyzer.get_error_summary()
    print(f"   Total errors: {error_summary['total_errors']}")
    print(f"   Errors by component: {error_summary['errors_by_component']}")
    
    # Generate daily report
    print("\n5. Daily Report:")
    daily_report = analyzer.generate_daily_report()
    print(f"   Report generated for: {daily_report['date']}")
    print(f"   Trading metrics: {daily_report['trading_metrics']['total_trades']} trades")
    print(f"   System uptime: {daily_report['system_metrics']['uptime_hours']:.1f} hours")
    
    # Export logs to CSV
    print("\n6. Exporting logs to CSV...")
    try:
        analyzer.export_logs_to_csv(
            "logs/demo/demo_export.csv",
            event_types=[EventType.TRADE_ENTRY, EventType.TRADE_EXIT]
        )
        print("   ✅ Logs exported to demo_export.csv")
    except Exception as e:
        print(f"   ❌ Export failed: {e}")
    
    print("\n🎉 Demo completed successfully!")
    print("\nCheck the logs/demo/ directory for generated log files:")
    print("   - audit.log (all events)")
    print("   - trades.log (trading events)")
    print("   - system.log (system events)")
    print("   - errors.log (error events)")
    print("   - demo_export.csv (exported data)")
    
    # Clean up
    audit_logger.log_system_event(
        EventType.SYSTEM_STOP,
        "Demo system stopping"
    )
    
    close_audit_logger()


def demonstrate_sync_logging():
    """Demonstrate synchronous logging features."""
    print("\n" + "=" * 50)
    print("🔄 Synchronous Logging Features")
    print("=" * 50)
    
    # Initialize for sync demo
    audit_logger = initialize_audit_logger(
        log_dir="logs/sync_demo",
        session_id="sync_demo_001",
        environment="sync_demo"
    )
    
    # Log various event types
    event_types = [
        (EventType.SYSTEM_START, "Sync demo started"),
        (EventType.HEALTH_CHECK, "Health check performed"),
        (EventType.SYMBOL_SCAN, "Symbol scan completed"),
        (EventType.ENTRY_SIGNAL, "Entry signal detected"),
        (EventType.RISK_LIMIT_HIT, "Risk limit exceeded"),
        (EventType.API_ERROR, "API error occurred"),
    ]
    
    for event_type, message in event_types:
        if event_type == EventType.SYSTEM_START:
            audit_logger.log_system_event(event_type, message)
        elif event_type == EventType.HEALTH_CHECK:
            audit_logger.log_system_event(event_type, message, metadata={"status": "healthy"})
        elif event_type in [EventType.SYMBOL_SCAN, EventType.ENTRY_SIGNAL]:
            audit_logger.log_strategy_event(event_type, message, "sync_strategy")
        elif event_type == EventType.RISK_LIMIT_HIT:
            audit_logger.log_risk_event(event_type, message)
        elif event_type == EventType.API_ERROR:
            audit_logger.log_error(message, "api_client")
        
        print(f"   ✅ Logged: {event_type.value}")
    
    print("\n✅ Synchronous logging demo completed!")
    close_audit_logger()


if __name__ == "__main__":
    print("DayBot Comprehensive Logging System Demo")
    print("This demo will create log files in logs/demo/ directory")
    
    # Create logs directory if it doesn't exist
    Path("logs/demo").mkdir(parents=True, exist_ok=True)
    Path("logs/sync_demo").mkdir(parents=True, exist_ok=True)
    
    # Run async demo
    asyncio.run(demonstrate_logging())
    
    # Run sync demo
    demonstrate_sync_logging()
    
    print("\n🎯 Demo Summary:")
    print("- Created comprehensive audit logs with structured JSON format")
    print("- Demonstrated trade, system, risk, and performance logging")
    print("- Showed log analysis and reporting capabilities")
    print("- Exported data to CSV for external analysis")
    print("- All logs are stored in logs/demo/ and logs/sync_demo/")
    print("\nYou can now integrate this logging system into your trading strategies!")
