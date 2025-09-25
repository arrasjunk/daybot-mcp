# 🚀 DayBot MCP - Quick Start Guide

## 1. Get Your Alpaca API Keys

### Paper Trading (Recommended for Testing)
1. Visit [Alpaca Markets](https://app.alpaca.markets/paper/dashboard/overview)
2. Sign up for a free paper trading account
3. Navigate to "API Keys" in the dashboard
4. Generate new API keys
5. Copy your `API Key ID` and `Secret Key`

### Live Trading (Use with Caution)
1. Fund your live Alpaca account
2. Generate live API keys from the live dashboard
3. Use `https://api.alpaca.markets` as the base URL

## 2. Configure Your Environment

Update your `.env` file with real credentials:

```bash
# Replace these with your actual Alpaca API keys
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Optional: Polygon.io backup data source (recommended for production)
POLYGON_API_KEY=your_polygon_api_key_here
ENABLE_POLYGON_BACKUP=false

# Adjust risk settings as needed
MAX_POSITION_SIZE=0.02      # 2% of portfolio per position
MAX_DAILY_LOSS=0.05         # 5% daily loss limit
DEFAULT_STOP_LOSS=0.02      # 2% default stop loss
DEFAULT_TAKE_PROFIT=0.04    # 4% default take profit

# Adaptive sizing (optional)
DEFAULT_RISK_PER_TRADE=0.01     # 1% portfolio risk per trade (separate from stop loss)
RISK_SIZING_MODE=fixed          # fixed|volatility|kelly|conviction|hybrid
FRACTIONAL_KELLY_MULTIPLIER=0.5 # Fraction of Kelly to use
KELLY_CAP=0.2                   # Maximum Kelly fraction
HYBRID_KELLY_WEIGHT=0.3         # Weight for Kelly in hybrid mode
RISK_FLOOR=0.002                # Minimum risk per trade (0.2%)
RISK_CEILING=0.02               # Maximum risk per trade (2%)
CONVICTION_MIN_MULTIPLIER=0.5   # Multiplier at lowest conviction
CONVICTION_MAX_MULTIPLIER=1.5   # Multiplier at highest conviction
HEAT_SCALING_ENABLED=true       # Downscale risk as portfolio heat rises
HEAT_MIN_MULTIPLIER=0.3         # Minimum scaling at high heat
LOW_VOLATILITY_MULTIPLIER=1.2   # Risk up-weight in low vol regimes
HIGH_VOLATILITY_MULTIPLIER=0.7  # Risk down-weight in high vol regimes
```

## 3. Start the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start the server
uvicorn daybot_mcp.server:app --host 0.0.0.0 --port 8000 --reload
```

## 4. Test Your Setup

```bash
# Run the analytics demo (seeds sample trades and prints reports)
python demo_analytics.py

# Check health
curl http://localhost:8000/tools/healthcheck

# View API docs and the performance dashboard
open http://localhost:8000/docs
open http://localhost:8000/dashboard/
```

## 5. Your First Trade

### Using curl:
```bash
# Enter a trade
curl -X POST http://localhost:8000/tools/enter_trade \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 10,
    "order_type": "market",
    "stop_loss_price": 145.00,
    "take_profit_price": 155.00
  }'

# Check positions
curl http://localhost:8000/positions

# Close position
curl -X POST http://localhost:8000/tools/close_symbol \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

### Using Python:
```python
import asyncio
import httpx

async def place_trade():
    async with httpx.AsyncClient() as client:
        # Enter trade
        response = await client.post(
            "http://localhost:8000/tools/enter_trade",
            json={
                "symbol": "AAPL",
                "side": "buy",
                "quantity": 10,
                "order_type": "market"
            }
        )
        print(response.json())

asyncio.run(place_trade())
```

## 6. Monitor Your Trading

### Risk Dashboard
```bash
curl http://localhost:8000/tools/risk_status
```

### Trade Log
```bash
curl http://localhost:8000/trade_log
```

### Account Status
```bash
curl http://localhost:8000/account
```

### 📊 Comprehensive Audit Logging (NEW!)

DayBot now includes a comprehensive logging system for detailed audit trails:

```bash
# Get daily trading report
curl http://localhost:8000/audit/daily_report

# Get trading performance metrics
curl "http://localhost:8000/audit/trading_metrics?start_date=2024-01-01&end_date=2024-01-31"

# Get system performance metrics
curl http://localhost:8000/audit/system_metrics

# Get error summary
curl http://localhost:8000/audit/error_summary

# Get performance by symbol
curl http://localhost:8000/audit/symbol_performance
```

**Log Files Location**: `logs/`
- `audit.log` - All events (comprehensive)
- `trades.log` - Trading-specific events  
- `system.log` - System events
- `errors.log` - Error events only
- `performance.log` - Performance metrics

**Try the logging demo**:
```bash
python examples/logging_example.py
```

### 📊 Performance Analytics (NEW!)

New analytics endpoints and a web dashboard are available for post-trade analysis:

```bash
# Performance metrics
curl "http://localhost:8000/analytics/performance?period=monthly"

# Risk analysis and drawdown metrics
curl http://localhost:8000/analytics/risk

# Execution quality and slippage analysis
curl http://localhost:8000/analytics/execution

# Strategy optimization recommendations
curl http://localhost:8000/analytics/optimization

# Browse dashboard
open http://localhost:8000/dashboard/
```

See `ANALYTICS_README.md` for detailed documentation and examples.

#### Position Sizing: Kelly Inputs (NEW!)

Use analytics-derived Kelly inputs to inform adaptive position sizing. The server can auto-populate Kelly stats when `sizing_mode` is `kelly` or `hybrid`, or you can query them directly:

```bash
curl "http://localhost:8000/analytics/kelly_inputs?start_date=2024-01-01&end_date=2024-12-31&strategy=momentum&symbol=AAPL"
```

Response includes: `win_rate`, `avg_win`, `avg_loss`, `kelly_fraction`, `fractional_kelly`, and `recommended_risk_fraction` (bounded by your global risk floor/ceiling).

## 7. Safety Features

- **Daily Loss Limits**: Trading stops when daily loss exceeds threshold
- **Position Sizing**: Automatic calculation based on account size and risk
- **Portfolio Heat**: Monitors total risk exposure
- **Verified Closes**: Ensures positions are actually closed
- **Health Checks**: Continuous monitoring of account and market status

## 8. Common Use Cases

### Momentum Trading
```python
# Scan for symbols
symbols = await client.post("/tools/scan_symbols", json={})

# Enter trades with tight stops
for symbol in symbols["symbols"][:5]:
    await client.post("/tools/enter_trade", json={
        "symbol": symbol,
        "side": "buy",
        "risk_percent": 0.01,  # 1% risk per trade
        "order_type": "market"
    })
```

### Adaptive Sizing Examples
```bash
# Volatility-scaled sizing using ATR (server uses latest indicator values)
curl -X POST http://localhost:8000/tools/enter_trade \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "buy",
    "order_type": "market",
    "sizing_mode": "volatility"
  }'

# Conviction-based sizing (0..1 or 1..5 scale)
curl -X POST http://localhost:8000/tools/enter_trade \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NVDA",
    "side": "buy",
    "order_type": "market",
    "sizing_mode": "conviction",
    "conviction": 0.8
  }'

# Fractional Kelly sizing (supply win rate and average P/L)
curl -X POST http://localhost:8000/tools/enter_trade \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "QQQ",
    "side": "buy",
    "order_type": "market",
    "sizing_mode": "kelly",
    "kelly_win_rate": 58.0,
    "kelly_avg_win": 120.0,
    "kelly_avg_loss": -80.0
  }'

# Hybrid sizing (volatility x conviction, blended with Kelly)
curl -X POST http://localhost:8000/tools/enter_trade \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "SPY",
    "side": "buy",
    "order_type": "market",
    "sizing_mode": "hybrid",
    "conviction": 4,
    "kelly_win_rate": 55.0,
    "kelly_avg_win": 100.0,
    "kelly_avg_loss": -70.0
  }'
```

### Risk Management
```python
# Check portfolio heat
risk = await client.get("/tools/risk_status")
if risk["portfolio_heat"]["portfolio_heat_percent"] > 10:
    # Reduce position sizes or close some trades
    await client.post("/tools/flat_all")
```

### Position Management
```python
# Adjust stop loss
await client.post("/tools/manage_trade", json={
    "symbol": "AAPL",
    "action": "adjust_stop",
    "new_stop_price": 148.00
})

# Take partial profits
await client.post("/tools/manage_trade", json={
    "symbol": "AAPL", 
    "action": "partial_exit",
    "exit_quantity": 5
})
```

## 9. Troubleshooting

### Common Issues:

**"Invalid API credentials"**
- Check your API keys in `.env`
- Ensure you're using the correct base URL (paper vs live)

**"Market is closed"**
- Check market hours (9:30 AM - 4:00 PM ET)
- Use `extended_hours=true` for pre/post market trading

**"Insufficient buying power"**
- Check your account balance
- Reduce position sizes
- Check day trading rules (PDT)

**"Position not found"**
- Verify the symbol exists
- Check if position was already closed
- Use `/positions` endpoint to see current holdings

### Debug Mode:
```bash
# Enable debug logging
DEBUG_MODE=true uvicorn daybot_mcp.server:app --reload --log-level debug
```

## 10. Production Deployment

### Docker:
```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f daybot-mcp
```

### Systemd Service:
```bash
# Create service file
sudo nano /etc/systemd/system/daybot-mcp.service

# Enable and start
sudo systemctl enable daybot-mcp
sudo systemctl start daybot-mcp
```

## 📞 Support

- **Documentation**: Check `/docs` endpoint for API reference
- **Logs**: Monitor server logs for detailed error information
- **Health Check**: Use `/tools/healthcheck` to verify system status
- **Demo Script**: Run `python demo.py` to test functionality

## ⚠️ Important Disclaimers

1. **Paper Trading First**: Always test with paper trading before using real money
2. **Risk Management**: Never risk more than you can afford to lose
3. **Market Hours**: Be aware of market hours and trading rules
4. **API Limits**: Respect Alpaca's API rate limits
5. **Monitoring**: Always monitor your positions and system health

Happy Trading! 🎯
