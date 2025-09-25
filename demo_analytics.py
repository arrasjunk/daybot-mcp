#!/usr/bin/env python3
"""
Demo script for the DayBot Analytics System.
Demonstrates comprehensive post-trade analytics, performance measurement, and optimization recommendations.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from daybot_mcp.analytics import (
    initialize_analytics, get_analytics_engine, Trade, PerformanceDashboard
)
from daybot_mcp.risk_analytics import RiskAnalyzer
from daybot_mcp.execution_analytics import ExecutionAnalyzer
from daybot_mcp.strategy_optimizer import StrategyOptimizer


def create_sample_trades(num_trades: int = 100) -> list[Trade]:
    """Create sample trades for demonstration."""
    trades = []
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "SPY", "QQQ"]
    strategies = ["momentum", "mean_reversion", "breakout", "scalping"]
    
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    
    for i in range(num_trades):
        symbol = random.choice(symbols)
        strategy = random.choice(strategies)
        side = random.choice(["buy", "sell"])
        
        # Entry time
        entry_time = base_time + timedelta(
            days=random.randint(0, 29),
            hours=random.randint(9, 15),
            minutes=random.randint(0, 59)
        )
        
        # Exit time (30 minutes to 4 hours later)
        duration_minutes = random.randint(30, 240)
        exit_time = entry_time + timedelta(minutes=duration_minutes)
        
        # Prices
        entry_price = random.uniform(50, 300)
        
        # Simulate realistic P&L distribution (60% win rate)
        if random.random() < 0.6:  # Win
            price_change = random.uniform(0.005, 0.04)  # 0.5% to 4% gain
        else:  # Loss
            price_change = -random.uniform(0.005, 0.025)  # 0.5% to 2.5% loss
        
        if side == "buy":
            exit_price = entry_price * (1 + price_change)
        else:
            exit_price = entry_price * (1 - price_change)
        
        quantity = random.randint(10, 500)
        
        # Calculate P&L
        if side == "buy":
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity
        
        # Add some commission and slippage
        commission = quantity * 0.005  # $0.005 per share
        slippage = random.uniform(-0.02, 0.01)  # -2 to +1 cents
        
        pnl -= commission
        
        # MFE and MAE (simplified)
        if pnl > 0:
            mfe = abs(pnl) * random.uniform(1.0, 1.5)
            mae = abs(pnl) * random.uniform(0.1, 0.3)
        else:
            mfe = abs(pnl) * random.uniform(0.1, 0.3)
            mae = abs(pnl) * random.uniform(1.0, 1.5)
        
        trade = Trade(
            symbol=symbol,
            strategy=strategy,
            entry_time=entry_time,
            exit_time=exit_time,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            side=side,
            pnl=pnl,
            pnl_percent=0.0,  # Will be calculated
            commission=commission,
            slippage=slippage,
            exit_reason=random.choice(["take_profit", "stop_loss", "time_exit", "manual"]),
            duration_minutes=duration_minutes,
            max_favorable_excursion=mfe,
            max_adverse_excursion=mae
        )
        
        trades.append(trade)
    
    return trades


def print_section_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_metrics_table(metrics: dict, title: str = "Metrics"):
    """Print metrics in a formatted table."""
    print(f"\n{title}:")
    print("-" * 50)
    for key, value in metrics.items():
        print(f"{key:<30}: {value}")


async def demo_analytics_system():
    """Demonstrate the complete analytics system."""
    print("🚀 DayBot Analytics System Demo")
    print("Demonstrating comprehensive post-trade analytics and optimization")
    
    # Initialize analytics
    print("\n📊 Initializing Analytics Engine...")
    analyzer = initialize_analytics("logs")
    
    # Create sample trades
    print("📈 Generating sample trade data...")
    sample_trades = create_sample_trades(150)
    
    # Add trades to database
    print("💾 Storing trades in analytics database...")
    for trade in sample_trades:
        analyzer.add_trade(trade)
    
    print(f"✅ Added {len(sample_trades)} sample trades to analytics database")
    
    # === PERFORMANCE ANALYTICS ===
    print_section_header("PERFORMANCE ANALYTICS")
    
    # Calculate overall performance metrics
    all_trades = analyzer.get_trades()
    performance_metrics = analyzer.calculate_performance_metrics(all_trades)
    
    # Display key metrics
    key_metrics = {
        "Total Trades": performance_metrics.total_trades,
        "Win Rate": f"{performance_metrics.win_rate:.1f}%",
        "Profit Factor": f"{performance_metrics.profit_factor:.2f}",
        "Net P&L": f"${performance_metrics.net_profit:,.2f}",
        "Expectancy": f"${performance_metrics.expectancy:.2f}",
        "Max Drawdown": f"{performance_metrics.max_drawdown_percent:.1f}%",
        "Sharpe Ratio": f"{performance_metrics.sharpe_ratio:.2f}",
        "Kelly Criterion": f"{performance_metrics.kelly_criterion:.2%}",
        "Avg Win": f"${performance_metrics.avg_win:.2f}",
        "Avg Loss": f"${performance_metrics.avg_loss:.2f}",
        "Max Consecutive Wins": performance_metrics.max_consecutive_wins,
        "Max Consecutive Losses": performance_metrics.max_consecutive_losses
    }
    
    print_metrics_table(key_metrics, "Overall Performance Metrics")
    
    # === RISK ANALYTICS ===
    print_section_header("RISK ANALYTICS")
    
    risk_analyzer = RiskAnalyzer(analyzer)
    risk_report = risk_analyzer.generate_risk_report(all_trades)
    
    print("\n🔍 Drawdown Analysis:")
    print("-" * 30)
    for key, value in risk_report["drawdown_analysis"].items():
        print(f"{key:<25}: {value}")
    
    print("\n📊 Risk-Adjusted Returns:")
    print("-" * 30)
    for key, value in risk_report["risk_adjusted_returns"].items():
        print(f"{key:<25}: {value}")
    
    print("\n⚠️  Value at Risk:")
    print("-" * 30)
    for key, value in risk_report["value_at_risk"].items():
        print(f"{key:<25}: {value}")
    
    print("\n🎯 Portfolio Heat:")
    print("-" * 30)
    for key, value in risk_report["portfolio_heat"].items():
        print(f"{key:<25}: {value}")
    
    if risk_report["risk_warnings"]:
        print("\n⚠️  Risk Warnings:")
        for warning in risk_report["risk_warnings"]:
            print(f"  • {warning}")
    
    # === EXECUTION ANALYTICS ===
    print_section_header("EXECUTION ANALYTICS")
    
    execution_analyzer = ExecutionAnalyzer(analyzer)
    execution_report = execution_analyzer.generate_execution_report(all_trades)
    
    print("\n📋 Execution Summary:")
    print("-" * 30)
    for key, value in execution_report["summary"].items():
        print(f"{key:<25}: {value}")
    
    print("\n💹 Slippage Analysis:")
    print("-" * 30)
    for key, value in execution_report["slippage_analysis"]["distribution"].items():
        print(f"{key:<25}: {value}")
    
    print("\n⏰ Timing Analysis:")
    print("-" * 30)
    for period, data in execution_report["timing_analysis"].items():
        print(f"{period:<25}: Avg Slippage {data['avg_slippage']}, Win Rate {data['win_rate']}")
    
    if execution_report["recommendations"]:
        print("\n💡 Execution Recommendations:")
        for rec in execution_report["recommendations"]:
            print(f"  • {rec}")
    
    # === STRATEGY OPTIMIZATION ===
    print_section_header("STRATEGY OPTIMIZATION")
    
    optimizer = StrategyOptimizer(analyzer)
    
    # Analyze each strategy
    strategies = set(trade.strategy for trade in all_trades)
    
    for strategy in strategies:
        strategy_trades = [t for t in all_trades if t.strategy == strategy]
        if len(strategy_trades) < 5:  # Skip strategies with too few trades
            continue
        
        analysis = optimizer.analyze_strategy_performance(strategy_trades, strategy)
        
        print(f"\n📈 {strategy.upper()} Strategy Analysis:")
        print("-" * 40)
        print(f"Performance Score    : {analysis.performance_score:.1f}/100")
        print(f"Total Trades        : {analysis.total_trades}")
        print(f"Win Rate           : {analysis.win_rate:.1f}%")
        print(f"Profit Factor      : {analysis.profit_factor:.2f}")
        print(f"Expectancy         : ${analysis.expectancy:.2f}")
        print(f"Max Drawdown       : {analysis.max_drawdown:.1f}%")
        print(f"Optimization Potential: {analysis.optimization_potential:.1f}%")
        
        if analysis.strengths:
            print(f"\n✅ Strengths:")
            for strength in analysis.strengths:
                print(f"  • {strength}")
        
        if analysis.weaknesses:
            print(f"\n❌ Weaknesses:")
            for weakness in analysis.weaknesses:
                print(f"  • {weakness}")
        
        if analysis.best_performing_symbols:
            print(f"\n🏆 Top Performing Symbols:")
            for symbol, avg_pnl in analysis.best_performing_symbols[:3]:
                print(f"  • {symbol}: ${avg_pnl:.2f} avg P&L")
    
    # === OPTIMIZATION RECOMMENDATIONS ===
    print_section_header("OPTIMIZATION RECOMMENDATIONS")
    
    optimization_report = optimizer.generate_optimization_report(all_trades)
    
    print(f"\n📊 Optimization Summary:")
    print("-" * 30)
    for key, value in optimization_report["summary"].items():
        print(f"{key:<25}: {value}")
    
    print(f"\n🚀 Implementation Roadmap:")
    roadmap = optimization_report["implementation_roadmap"]
    
    if roadmap["immediate"]:
        print("\n⚡ Immediate Actions (Easy & High Impact):")
        for action in roadmap["immediate"]:
            print(f"  • {action}")
    
    if roadmap["short_term"]:
        print("\n📅 Short-term Actions (1-2 weeks):")
        for action in roadmap["short_term"]:
            print(f"  • {action}")
    
    if roadmap["long_term"]:
        print("\n🎯 Long-term Actions (1+ months):")
        for action in roadmap["long_term"]:
            print(f"  • {action}")
    
    # Display high-priority recommendations in detail
    high_priority = optimization_report["by_priority"]["high"]
    if high_priority:
        print(f"\n🔥 HIGH PRIORITY RECOMMENDATIONS:")
        for i, rec in enumerate(high_priority[:3], 1):
            print(f"\n{i}. {rec['title']}")
            print(f"   Impact: {rec['expected_impact']}")
            print(f"   Difficulty: {rec['difficulty']}")
            print(f"   Description: {rec['description']}")
            if rec['actions']:
                print("   Actions:")
                for action in rec['actions'][:2]:  # Show first 2 actions
                    print(f"     • {action}")
    
    # === SYMBOL PERFORMANCE ANALYSIS ===
    print_section_header("SYMBOL PERFORMANCE ANALYSIS")
    
    # Analyze performance by symbol
    symbol_stats = {}
    for trade in all_trades:
        if trade.symbol not in symbol_stats:
            symbol_stats[trade.symbol] = {
                "trades": 0, "total_pnl": 0, "wins": 0, "total_quantity": 0
            }
        
        stats = symbol_stats[trade.symbol]
        stats["trades"] += 1
        stats["total_pnl"] += trade.pnl
        stats["total_quantity"] += trade.quantity
        if trade.pnl > 0:
            stats["wins"] += 1
    
    # Calculate metrics and sort by performance
    symbol_performance = []
    for symbol, stats in symbol_stats.items():
        if stats["trades"] >= 3:  # Minimum trades for significance
            avg_pnl = stats["total_pnl"] / stats["trades"]
            win_rate = (stats["wins"] / stats["trades"]) * 100
            symbol_performance.append((symbol, avg_pnl, win_rate, stats["trades"]))
    
    symbol_performance.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n📈 Symbol Performance Ranking:")
    print("-" * 60)
    print(f"{'Symbol':<8} {'Avg P&L':<12} {'Win Rate':<10} {'Trades':<8}")
    print("-" * 60)
    
    for symbol, avg_pnl, win_rate, trades in symbol_performance:
        print(f"{symbol:<8} ${avg_pnl:>8.2f}    {win_rate:>6.1f}%    {trades:>5}")
    
    # === DASHBOARD INFORMATION ===
    print_section_header("DASHBOARD ACCESS")
    
    print("""
🌐 Web Dashboard Available:
   
   Start the server with: python -m daybot_mcp.server
   Then visit: http://localhost:8000/dashboard/
   
📊 Available Endpoints:
   • GET  /analytics/performance  - Performance metrics
   • GET  /analytics/risk         - Risk analysis  
   • GET  /analytics/execution    - Execution quality
   • GET  /analytics/optimization - Strategy recommendations
   • GET  /analytics/trades       - Trade data with filtering
   • POST /analytics/sync         - Sync data from log files
   
💡 Example API Usage:
   curl "http://localhost:8000/analytics/performance?period=monthly&strategy=momentum"
   curl "http://localhost:8000/analytics/optimization"
   curl "http://localhost:8000/analytics/risk"
    """)
    
    print_section_header("SUMMARY")
    
    print(f"""
✅ Analytics System Successfully Demonstrated!

📊 Key Capabilities Implemented:
   • Comprehensive performance metrics (win rate, profit factor, Sharpe ratio)
   • Advanced risk analytics (drawdown analysis, VaR, portfolio heat)
   • Execution quality analysis (slippage, market impact, timing)
   • Strategy optimization recommendations with actionable insights
   • Interactive web dashboard with real-time visualizations
   • RESTful API endpoints for programmatic access

🎯 Benefits for Trading Strategy Improvement:
   • Data-driven optimization recommendations
   • Risk management insights to prevent large losses  
   • Execution quality monitoring to reduce costs
   • Performance tracking across multiple timeframes
   • Strategy comparison and ranking capabilities

🚀 Next Steps:
   1. Integrate with your live trading system
   2. Set up automated daily/weekly reporting
   3. Implement the high-priority optimization recommendations
   4. Monitor execution quality and adjust order routing
   5. Use the dashboard for real-time performance monitoring

The analytics system provides the missing feedback loop for continuous
strategy improvement and risk management optimization.
    """)


if __name__ == "__main__":
    asyncio.run(demo_analytics_system())
