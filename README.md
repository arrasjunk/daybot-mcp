# DayBot MCP - Algorithmic Trading Server

A FastAPI-based MCP (Model Context Protocol) tool server for algorithmic trading with Alpaca Markets. This server provides REST endpoints for automated trading operations including position management, risk control, and market analysis.

## Features

- **Async Trading Operations**: Built with FastAPI and httpx for high-performance async operations
- **Risk Management**: Comprehensive position sizing, daily loss limits, and portfolio heat monitoring
- **Technical Indicators**: VWAP, EMA, ATR, RSI, and Bollinger Bands
- **Position Management**: Bracket orders, stop loss adjustment, trailing stops, and verified position closing
- **MCP Tool Endpoints**: RESTful API following MCP schema for easy integration
- **Real-time Monitoring**: Health checks, account status, and trade logging

## Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI (for MCP tool server endpoints)
- **Web server**: Uvicorn
- **HTTP client**: httpx (async, for Alpaca API calls)
- **Config management**: python-dotenv
- **Data models**: pydantic v2
- **Testing**: pytest + responses (for mocking)

## Project Structure

```
daybot-mcp/
├── README.md
├── requirements.txt
├── .env.example
├── daybot_mcp/
│   ├── __init__.py
│   ├── config.py          # loads env vars
│   ├── alpaca_client.py   # async REST client wrapper
│   ├── indicators.py      # VWAP, EMA, ATR classes
│   ├── risk.py            # shares_for_trade sizing
│   ├── utils.py           # close_with_verification
│   └── server.py          # FastAPI app w/ MCP endpoints
└── tests/
    ├── test_risk.py
    └── test_close.py
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd daybot-mcp
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Alpaca API credentials
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# Alpaca API Configuration (Required)
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Use paper trading URL

# Risk Management Settings (Optional)
MAX_POSITION_SIZE=0.02      # 2% of portfolio per position
MAX_DAILY_LOSS=0.05         # 5% daily loss limit
DEFAULT_STOP_LOSS=0.02      # 2% default stop loss
DEFAULT_TAKE_PROFIT=0.04    # 4% default take profit

# Server Configuration (Optional)
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG_MODE=false

# Trading Configuration (Optional)
MARKET_OPEN_BUFFER=5        # Minutes after market open
MARKET_CLOSE_BUFFER=15      # Minutes before market close
```

## Usage

### Starting the Server

```bash
# Development mode with auto-reload
uvicorn daybot_mcp.server:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn daybot_mcp.server:app --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Core MCP Tool Endpoints

- `POST /tools/scan_symbols` - Return watchlist (stubbed, extend with scanner later)
- `POST /tools/enter_trade` - Submit bracket orders (with stop/TP)
- `POST /tools/manage_trade` - Adjust stop, trail, exit partial
- `POST /tools/close_symbol` - Idempotent close with verification
- `POST /tools/flat_all` - Flatten all positions and cancel open orders
- `GET /tools/healthcheck` - Check account, clock, connectivity
- `GET /tools/risk_status` - Return P&L / drawdown counters
- `POST /tools/record_trade` - Log structured trade events

#### Utility Endpoints

- `GET /positions` - Get current positions
- `GET /orders` - Get orders by status
- `GET /account` - Get account information
- `GET /trade_log` - Get recent trade events

### Example Usage

#### Health Check
```bash
curl http://localhost:8000/tools/healthcheck
```

#### Enter a Trade
```bash
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
```

#### Close a Position
```bash
curl -X POST http://localhost:8000/tools/close_symbol \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL"
  }'
```

#### Get Risk Status
```bash
curl http://localhost:8000/tools/risk_status
```

## Risk Management

The system includes comprehensive risk management features:

- **Position Sizing**: Automatic calculation based on account size and risk parameters
- **Daily Loss Limits**: Prevents trading when daily loss threshold is reached
- **Portfolio Heat**: Monitors total risk exposure across all positions
- **Stop Loss Management**: Automatic and manual stop loss adjustment
- **Position Limits**: Maximum position size and count restrictions

## Technical Indicators

Built-in technical indicators for market analysis:

- **VWAP** (Volume Weighted Average Price)
- **EMA** (Exponential Moving Average) - 9, 21, 50 periods
- **ATR** (Average True Range) - 14 periods
- **RSI** (Relative Strength Index) - 14 periods
- **Bollinger Bands** - 20 periods, 2 standard deviations

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=daybot_mcp

# Run specific test file
pytest tests/test_risk.py
```

## Development

### Adding New Endpoints

1. Define request/response models using Pydantic
2. Implement the endpoint function in `server.py`
3. Add appropriate error handling and logging
4. Write tests for the new functionality

### Adding New Indicators

1. Implement the indicator class in `indicators.py`
2. Add it to the `IndicatorManager` class
3. Update the indicator calculation in trading logic

## Security Considerations

- **API Keys**: Never commit API keys to version control
- **Paper Trading**: Use paper trading URLs for development and testing
- **Rate Limiting**: Be aware of Alpaca API rate limits
- **Error Handling**: Comprehensive error handling prevents system crashes

## Deployment

### Docker (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY daybot_mcp/ daybot_mcp/
COPY .env .env

CMD ["uvicorn", "daybot_mcp.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t daybot-mcp .
docker run -p 8000:8000 daybot-mcp
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Trading involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Use at your own risk.

## Support

For questions or issues:
1. Check the documentation
2. Review existing issues
3. Create a new issue with detailed information

## Roadmap

- [ ] Advanced scanner implementation
- [ ] WebSocket real-time data feeds
- [ ] Machine learning integration
- [ ] Portfolio optimization algorithms
- [ ] Advanced order types (OCO, etc.)
- [ ] Performance analytics dashboard
