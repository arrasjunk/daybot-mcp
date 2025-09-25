"""
Async REST client wrapper for Alpaca API.
Handles authentication, rate limiting, and common trading operations.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import httpx
from pydantic import BaseModel

from .config import settings, get_alpaca_headers


class Position(BaseModel):
    """Alpaca position model."""
    symbol: str
    qty: float
    side: str
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float


class Order(BaseModel):
    """Alpaca order model."""
    id: str
    symbol: str
    qty: float
    side: str
    order_type: str
    time_in_force: str
    status: str
    filled_qty: Optional[float] = None
    filled_avg_price: Optional[float] = None
    stop_price: Optional[float] = None
    limit_price: Optional[float] = None


class Account(BaseModel):
    """Alpaca account model."""
    id: str
    account_number: str
    status: str
    currency: str
    buying_power: float
    cash: float
    portfolio_value: float
    equity: float
    last_equity: float
    multiplier: int
    daytrade_count: int
    sma: float


class AlpacaClient:
    """Async client for Alpaca API operations."""
    
    def __init__(self):
        self.base_url = settings.alpaca_base_url
        self.headers = get_alpaca_headers()
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to Alpaca API."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
            raise Exception(f"Alpaca API error: {error_detail}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    async def get_account(self) -> Account:
        """Get account information."""
        data = await self._request("GET", "/v2/account")
        return Account(**data)
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        data = await self._request("GET", "/v2/positions")
        return [Position(**pos) for pos in data]
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        try:
            data = await self._request("GET", f"/v2/positions/{symbol}")
            return Position(**data)
        except Exception:
            return None
    
    async def get_orders(self, status: str = "open") -> List[Order]:
        """Get orders by status."""
        params = {"status": status, "limit": 500}
        data = await self._request("GET", "/v2/orders", params=params)
        return [Order(**order) for order in data]
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get specific order by ID."""
        try:
            data = await self._request("GET", f"/v2/orders/{order_id}")
            return Order(**data)
        except Exception:
            return None
    
    async def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail_price: Optional[float] = None,
        trail_percent: Optional[float] = None,
        extended_hours: bool = False
    ) -> Order:
        """Submit a new order."""
        order_data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
            "extended_hours": extended_hours
        }
        
        if limit_price:
            order_data["limit_price"] = str(limit_price)
        if stop_price:
            order_data["stop_price"] = str(stop_price)
        if trail_price:
            order_data["trail_price"] = str(trail_price)
        if trail_percent:
            order_data["trail_percent"] = str(trail_percent)
        
        data = await self._request("POST", "/v2/orders", json=order_data)
        return Order(**data)
    
    async def submit_bracket_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        limit_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        time_in_force: str = "day"
    ) -> List[Order]:
        """Submit a bracket order (entry + stop loss + take profit)."""
        order_class = "bracket"
        
        order_data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "market" if not limit_price else "limit",
            "time_in_force": time_in_force,
            "order_class": order_class
        }
        
        if limit_price:
            order_data["limit_price"] = str(limit_price)
        
        # Add bracket legs
        if stop_loss_price:
            order_data["stop_loss"] = {
                "stop_price": str(stop_loss_price)
            }
        
        if take_profit_price:
            order_data["take_profit"] = {
                "limit_price": str(take_profit_price)
            }
        
        data = await self._request("POST", "/v2/orders", json=order_data)
        
        # Bracket orders return multiple orders
        if isinstance(data, list):
            return [Order(**order) for order in data]
        else:
            return [Order(**data)]
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            await self._request("DELETE", f"/v2/orders/{order_id}")
            return True
        except Exception:
            return False
    
    async def cancel_all_orders(self) -> bool:
        """Cancel all open orders."""
        try:
            await self._request("DELETE", "/v2/orders")
            return True
        except Exception:
            return False
    
    async def close_position(self, symbol: str, qty: Optional[float] = None) -> Order:
        """Close a position (or partial position)."""
        close_data = {"symbol": symbol}
        if qty:
            close_data["qty"] = str(qty)
        
        data = await self._request("DELETE", f"/v2/positions/{symbol}", json=close_data)
        return Order(**data)
    
    async def close_all_positions(self) -> bool:
        """Close all positions."""
        try:
            await self._request("DELETE", "/v2/positions")
            return True
        except Exception:
            return False
    
    async def get_clock(self) -> Dict[str, Any]:
        """Get market clock information."""
        return await self._request("GET", "/v2/clock")
    
    async def get_bars(
        self,
        symbols: List[str],
        timeframe: str = "1Day",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get historical bars for symbols."""
        params = {
            "symbols": ",".join(symbols),
            "timeframe": timeframe,
            "limit": limit
        }
        
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()
        
        return await self._request("GET", "/v2/stocks/bars", params=params)
    
    async def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """Get latest quote for a symbol."""
        data = await self._request("GET", f"/v2/stocks/{symbol}/quotes/latest")
        return data.get("quote", {})
    
    async def get_latest_trade(self, symbol: str) -> Dict[str, Any]:
        """Get latest trade for a symbol."""
        data = await self._request("GET", f"/v2/stocks/{symbol}/trades/latest")
        return data.get("trade", {})
    
    async def is_market_open(self) -> bool:
        """Check if market is currently open."""
        clock = await self.get_clock()
        return clock.get("is_open", False)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the connection and account."""
        try:
            account = await self.get_account()
            clock = await self.get_clock()
            
            return {
                "status": "healthy",
                "account_status": account.status,
                "market_open": clock.get("is_open", False),
                "buying_power": account.buying_power,
                "portfolio_value": account.portfolio_value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
