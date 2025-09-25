import pytest
import asyncio
from datetime import datetime, timezone

import httpx
from httpx import ASGITransport

# We import the app after monkeypatching analytics and alpaca classes


class StubMetrics:
    total_trades = 100
    win_rate = 58.0
    avg_win = 120.0
    avg_loss = -80.0


class StubAnalyzer:
    def get_trades(self, start_date=None, end_date=None, strategy=None, symbol=None, limit=None):
        return []

    def calculate_performance_metrics(self, trades):
        return StubMetrics()


class StubAccount:
    def __init__(self):
        self.portfolio_value = 100000.0
        self.equity = 100000.0
        self.last_equity = 100000.0
        self.buying_power = 100000.0
        self.cash = 100000.0
        self.status = "ACTIVE"


class StubOrder:
    def __init__(self, id):
        self.id = id


class StubAlpacaClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def is_market_open(self):
        return True

    async def get_account(self):
        return StubAccount()

    async def get_position(self, symbol):
        return None

    async def get_positions(self):
        return []

    async def get_orders(self, status="open"):
        return []

    async def get_latest_trade(self, symbol):
        return {"p": 100.0}

    async def submit_order(self, symbol, qty, side, order_type, limit_price=None, time_in_force="day"):
        return StubOrder("order-1")

    async def submit_bracket_order(self, **kwargs):
        return [StubOrder("order-1"), StubOrder("order-2"), StubOrder("order-3")]


@pytest.mark.asyncio
async def test_enter_trade_auto_kelly_populates(monkeypatch):
    # Monkeypatch analytics engine and Alpaca client in the server module
    import daybot_mcp.server as server

    monkeypatch.setattr(server, "get_analytics_engine", lambda: StubAnalyzer())
    monkeypatch.setattr(server, "AlpacaClient", StubAlpacaClient)

    # Initialize audit logger since ASGITransport bypasses startup event
    server.initialize_audit_logger(log_dir="logs", environment="test")

    transport = ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "symbol": "TEST",
            "side": "buy",
            "order_type": "market",
            "sizing_mode": "kelly"
        }
        resp = await client.post("/tools/enter_trade", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # Ensure position sizing info present and includes Kelly metadata
        psi = data.get("position_size_info") or {}
        assert psi
        assert psi.get("effective_risk_percent") is not None
        # Because our stubbed metrics imply positive Kelly
        assert psi.get("kelly_fraction") is not None
        assert psi.get("sizing_mode") in ("kelly", "hybrid")
