# DayBot Analytics System

## 🎯 Overview

The DayBot Analytics System provides comprehensive post-trade analysis and performance optimization for algorithmic trading strategies. It addresses the critical gap between logging trades and learning from them by providing actionable insights, risk analysis, and optimization recommendations.

## 🚀 Key Features

### 📊 Performance Analytics
- **Comprehensive Metrics**: Win rate, profit factor, expectancy, Sharpe ratio, Kelly criterion
- **Trade Distribution Analysis**: Average wins/losses, consecutive streaks, R-multiples
- **Time-based Performance**: Analysis by time periods, market sessions, holding duration
- **Symbol Performance**: Ranking and analysis by individual instruments

### ⚠️ Risk Analytics
- **Drawdown Analysis**: Maximum drawdown, underwater periods, recovery times
- **Value at Risk (VaR)**: 95% and 99% VaR, Conditional VaR (Expected Shortfall)
- **Risk-adjusted Returns**: Sharpe ratio, Sortino ratio, Calmar ratio, Sterling ratio
- **Tail Risk Metrics**: Skewness, kurtosis, tail ratio analysis
- **Portfolio Heat**: Concurrent position risk monitoring

### 🎯 Execution Analytics
- **Slippage Analysis**: Average, median, distribution by symbol and time
- **Market Impact**: Cost analysis and execution quality metrics
- **Timing Analysis**: Performance by market open, midday, close periods
- **Fill Quality**: Fill rates, partial fills, execution speed analysis

### 🔧 Strategy Optimization
- **Performance Scoring**: 0-100 scoring system for strategy evaluation
- **Weakness Identification**: Automated detection of strategy problems
- **Actionable Recommendations**: Prioritized optimization suggestions
- **Implementation Roadmap**: Immediate, short-term, and long-term improvements

### 🌐 Interactive Dashboard
- **Real-time Visualization**: Charts and graphs for key metrics
- **Filtering Capabilities**: By strategy, symbol, time period
- **Export Functions**: CSV export and API access
- **Mobile Responsive**: Works on desktop and mobile devices

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DayBot Analytics System                   │
├─────────────────────────────────────────────────────────────┤
│  Web Dashboard (dashboard.py)                               │
│  ├── Interactive Charts & Visualizations                    │
│  ├── Real-time Performance Monitoring                       │
│  └── Export & Filtering Capabilities                        │
├─────────────────────────────────────────────────────────────┤
│  REST API Endpoints (/analytics/*)                          │
│  ├── Performance Analytics                                   │
│  ├── Risk Analytics                                          │
│  ├── Execution Analytics                                     │
│  └── Strategy Optimization                                   │
├─────────────────────────────────────────────────────────────┤
│  Analytics Engines                                           │
│  ├── TradeAnalyzer (analytics.py)                          │
│  ├── RiskAnalyzer (risk_analytics.py)                      │
│  ├── ExecutionAnalyzer (execution_analytics.py)            │
│  └── StrategyOptimizer (strategy_optimizer.py)             │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  ├── SQLite Database (trades.db)                           │
│  ├── Log File Parser                                        │
│  └── Trade Data Models                                       │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install specific analytics dependencies
pip install numpy pandas fastapi jinja2 aiofiles
```

### 2. Basic Usage

```python
from daybot_mcp.analytics import initialize_analytics, get_analytics_engine
from daybot_mcp.strategy_optimizer import StrategyOptimizer

# Initialize analytics system
analyzer = initialize_analytics("logs")

# Get trades and calculate metrics
trades = analyzer.get_trades()
metrics = analyzer.calculate_performance_metrics(trades)

print(f"Win Rate: {metrics.win_rate:.1f}%")
print(f"Profit Factor: {metrics.profit_factor:.2f}")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")

# Get optimization recommendations
optimizer = StrategyOptimizer(analyzer)
recommendations = optimizer.generate_optimization_recommendations(trades)

for rec in recommendations[:3]:  # Top 3 recommendations
    print(f"• {rec.title}: {rec.expected_impact}")
```

### 3. Web Dashboard

```bash
# Start the server
python -m daybot_mcp.server

# Access dashboard at:
# http://localhost:8000/dashboard/
```

### 4. API Usage

```bash
# Get performance metrics
curl "http://localhost:8000/analytics/performance?period=monthly"

# Get optimization recommendations
curl "http://localhost:8000/analytics/optimization"

# Get risk analysis
curl "http://localhost:8000/analytics/risk"

# Sync data from log files
curl -X POST "http://localhost:8000/analytics/sync"
```

## 📊 API Endpoints

### Performance Analytics
- `GET /analytics/performance` - Comprehensive performance metrics
- `GET /analytics/trades` - Trade data with filtering
- `POST /analytics/sync` - Sync data from log files

### Risk Analytics
- `GET /analytics/risk` - Risk analysis and drawdown metrics
- Parameters: `start_date`, `end_date`

### Execution Analytics
- `GET /analytics/execution` - Execution quality and slippage analysis
- Parameters: `start_date`, `end_date`

### Strategy Optimization
- `GET /analytics/optimization` - Optimization recommendations
- `GET /analytics/strategy/{strategy_name}` - Specific strategy analysis
- Parameters: `strategy`, `start_date`, `end_date`

### Dashboard
- `GET /dashboard/` - Interactive web dashboard
- `GET /dashboard/api/performance` - Dashboard data API
- `POST /dashboard/api/sync-logs` - Sync logs via dashboard

## 🔧 Configuration

### Environment Variables

```bash
# Server configuration
SERVER_HOST=localhost
SERVER_PORT=8000

# Analytics configuration
ANALYTICS_LOG_DIR=logs
ANALYTICS_DB_PATH=logs/trades.db

# Dashboard configuration
DASHBOARD_TITLE="DayBot Performance Dashboard"
DASHBOARD_REFRESH_INTERVAL=30
```

### Analytics Settings

```python
# In your application
from daybot_mcp.analytics import initialize_analytics

# Initialize with custom settings
analyzer = initialize_analytics(
    log_dir="custom_logs",
    # Additional configuration options
)
```

## 📈 Key Metrics Explained

### Performance Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| **Win Rate** | Percentage of profitable trades | >50% |
| **Profit Factor** | Gross profit / Gross loss | >1.5 |
| **Expectancy** | Average profit per trade | >$0 |
| **Sharpe Ratio** | Risk-adjusted returns | >1.0 |
| **Kelly Criterion** | Optimal position size | 0.1-0.25 |

### Risk Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| **Max Drawdown** | Largest peak-to-trough decline | <15% |
| **VaR 95%** | Potential loss 5% of the time | Monitor |
| **Sortino Ratio** | Downside risk-adjusted returns | >1.0 |
| **Recovery Factor** | Net profit / Max drawdown | >2.0 |

### Execution Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| **Average Slippage** | Execution price vs expected | <$0.02 |
| **Fill Rate** | Percentage of orders filled | >95% |
| **Market Impact** | Price impact of trades | <10 bps |

## 🎯 Optimization Recommendations

The system generates actionable recommendations in these categories:

### 🎯 Entry Timing
- Signal quality improvement suggestions
- Market condition filters
- Volatility-based entry criteria

### 🚪 Exit Strategy
- Risk/reward ratio optimization
- Trailing stop implementations
- Profit-taking strategies

### 📏 Position Sizing
- Kelly criterion optimization
- Volatility-based sizing
- Correlation limits

### ⚠️ Risk Management
- Drawdown reduction strategies
- Portfolio heat management
- Daily loss limits

### 🎪 Symbol Selection
- Performance-based filtering
- Liquidity requirements
- Sector diversification

### ⏰ Time Filters
- Market session optimization
- Volatility period avoidance
- Economic event filters

### 🎯 Execution Quality
- Order type optimization
- Venue selection
- Timing improvements

## 🧪 Testing

### Run Analytics Tests

```bash
# Run all analytics tests
python test_analytics_system.py

# Run with pytest for detailed output
pytest test_analytics_system.py -v

# Run specific test categories
pytest test_analytics_system.py::TestTradeAnalyzer -v
pytest test_analytics_system.py::TestRiskAnalyzer -v
pytest test_analytics_system.py::TestExecutionAnalyzer -v
pytest test_analytics_system.py::TestStrategyOptimizer -v
```

### Demo Script

```bash
# Run comprehensive demo
python demo_analytics.py

# This will:
# 1. Generate sample trade data
# 2. Calculate all analytics metrics
# 3. Show optimization recommendations
# 4. Display dashboard information
```

## 📊 Sample Output

### Performance Summary
```
📊 Overall Performance Metrics:
Total Trades             : 150
Win Rate                : 62.7%
Profit Factor           : 1.85
Net P&L                 : $12,450.00
Expectancy              : $83.00
Max Drawdown            : 8.3%
Sharpe Ratio            : 1.42
Kelly Criterion         : 18.5%
```

### Risk Analysis
```
🔍 Drawdown Analysis:
max_drawdown            : {'absolute': '$2,100.00', 'percentage': '8.3%'}
average_drawdown        : 3.2%
drawdown_periods        : 3
current_underwater      : False
longest_recovery        : 12 days
```

### Optimization Recommendations
```
🔥 HIGH PRIORITY RECOMMENDATIONS:

1. Improve Risk/Reward Ratio
   Impact: 15-25% improvement in profit factor
   Difficulty: medium
   Description: Average win to average loss ratio is suboptimal
   Actions:
     • Implement trailing stops to capture larger wins
     • Use ATR-based targets instead of fixed percentages

2. Reduce Position Sizes
   Impact: 30-50% reduction in drawdown
   Difficulty: easy
   Description: High drawdown indicates excessive position sizing
   Actions:
     • Reduce position size by 25-50%
     • Implement Kelly Criterion for optimal sizing
```

## 🔗 Integration with Existing Systems

### With Audit Logger

```python
from daybot_mcp.audit_logger import get_audit_logger
from daybot_mcp.analytics import get_analytics_engine

# Log trade and add to analytics
audit_logger = get_audit_logger()
audit_logger.log_trade_exit(symbol, quantity, price, pnl, order_id, reason)

# Sync to analytics database
analyzer = get_analytics_engine()
analyzer.parse_log_files()  # Parse recent log entries
```

### With Trading Strategies

```python
from daybot_mcp.analytics import get_analytics_engine
from daybot_mcp.strategy_optimizer import StrategyOptimizer

class MomentumStrategy:
    def __init__(self):
        self.analyzer = get_analytics_engine()
        self.optimizer = StrategyOptimizer(self.analyzer)
    
    def optimize_parameters(self):
        """Use analytics to optimize strategy parameters."""
        trades = self.analyzer.get_trades(strategy="momentum")
        recommendations = self.optimizer.generate_optimization_recommendations(trades)
        
        # Apply high-priority recommendations
        for rec in recommendations:
            if rec.priority == "high":
                self.apply_recommendation(rec)
```

## 🚀 Advanced Features

### Custom Analytics

```python
from daybot_mcp.analytics import TradeAnalyzer

class CustomAnalyzer(TradeAnalyzer):
    def calculate_custom_metric(self, trades):
        """Add your custom analytics logic."""
        # Your custom analysis here
        pass
```

### Real-time Monitoring

```python
import asyncio
from daybot_mcp.analytics import get_analytics_engine

async def monitor_performance():
    """Real-time performance monitoring."""
    analyzer = get_analytics_engine()
    
    while True:
        recent_trades = analyzer.get_trades(limit=10)
        metrics = analyzer.calculate_performance_metrics(recent_trades)
        
        if metrics.max_drawdown_percent > 15:
            # Alert on high drawdown
            send_alert(f"High drawdown detected: {metrics.max_drawdown_percent:.1f}%")
        
        await asyncio.sleep(60)  # Check every minute
```

### Data Export

```python
from daybot_mcp.analytics import get_analytics_engine
import pandas as pd

analyzer = get_analytics_engine()
trades = analyzer.get_trades()

# Convert to DataFrame for analysis
df = pd.DataFrame([
    {
        'symbol': t.symbol,
        'strategy': t.strategy,
        'pnl': t.pnl,
        'duration': t.duration_minutes,
        'outcome': t.outcome.value
    }
    for t in trades
])

# Export to CSV
df.to_csv('trade_analysis.csv', index=False)
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/analytics-enhancement`
3. **Add tests**: Ensure new features have comprehensive tests
4. **Run tests**: `pytest test_analytics_system.py -v`
5. **Submit pull request**: Include description of changes and test results

## 📝 License

This analytics system is part of the DayBot MCP trading framework. See the main project license for details.

## 🆘 Support

- **Documentation**: See inline code documentation and docstrings
- **Issues**: Report bugs and feature requests via GitHub issues
- **Examples**: Check `demo_analytics.py` for comprehensive usage examples
- **Tests**: Review `test_analytics_system.py` for implementation details

## 🔮 Roadmap

### Planned Features
- **Machine Learning Integration**: Predictive analytics and pattern recognition
- **Advanced Visualizations**: 3D charts, heatmaps, correlation matrices
- **Real-time Alerts**: Configurable performance and risk alerts
- **Portfolio Attribution**: Performance attribution by strategy, symbol, time
- **Backtesting Integration**: Historical strategy testing and optimization
- **Multi-timeframe Analysis**: Intraday, daily, weekly, monthly analytics
- **Benchmark Comparison**: Performance vs market indices and peers

---

**The DayBot Analytics System transforms your trading logs into actionable insights for continuous strategy improvement and risk management optimization.**
