"""
Real-time WebSocket client for Alpaca market data and trade updates.
Provides low-latency streaming quotes, trades, and order status updates.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .config import settings

logger = logging.getLogger(__name__)

class StreamType(Enum):
    """Types of data streams available."""
    QUOTES = "quotes"
    TRADES = "trades"
    BARS = "bars"
    ORDERS = "trade_updates"
    NEWS = "news"

@dataclass
class Quote:
    """Real-time quote data."""
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    timestamp: datetime
    conditions: List[str] = field(default_factory=list)
    
    @property
    def mid_price(self) -> float:
        """Calculate mid-market price."""
        return (self.bid_price + self.ask_price) / 2
    
    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        return self.ask_price - self.bid_price
    
    @property
    def spread_bps(self) -> float:
        """Calculate spread in basis points."""
        return (self.spread / self.mid_price) * 10000 if self.mid_price > 0 else 0

@dataclass
class Trade:
    """Real-time trade data."""
    symbol: str
    price: float
    size: int
    timestamp: datetime
    conditions: List[str] = field(default_factory=list)
    exchange: Optional[str] = None

@dataclass
class Bar:
    """Real-time bar data."""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    vwap: Optional[float] = None

@dataclass
class OrderUpdate:
    """Real-time order status update."""
    order_id: str
    symbol: str
    side: str
    qty: float
    status: str
    event: str  # new, fill, partial_fill, canceled, etc.
    timestamp: datetime
    filled_qty: Optional[float] = None
    filled_price: Optional[float] = None
    remaining_qty: Optional[float] = None

class MarketDataManager:
    """Manages real-time market data subscriptions and callbacks."""
    
    def __init__(self):
        self.quote_callbacks: Dict[str, List[Callable]] = {}
        self.trade_callbacks: Dict[str, List[Callable]] = {}
        self.bar_callbacks: Dict[str, List[Callable]] = {}
        self.order_callbacks: List[Callable] = []
        
        # Latest data cache
        self.latest_quotes: Dict[str, Quote] = {}
        self.latest_trades: Dict[str, Trade] = {}
        self.latest_bars: Dict[str, Bar] = {}
        
        # Performance metrics
        self.message_count = 0
        self.last_message_time = 0
        self.latency_samples: List[float] = []
    
    def subscribe_quotes(self, symbol: str, callback: Callable[[Quote], None]):
        """Subscribe to real-time quotes for a symbol."""
        if symbol not in self.quote_callbacks:
            self.quote_callbacks[symbol] = []
        self.quote_callbacks[symbol].append(callback)
    
    def subscribe_trades(self, symbol: str, callback: Callable[[Trade], None]):
        """Subscribe to real-time trades for a symbol."""
        if symbol not in self.trade_callbacks:
            self.trade_callbacks[symbol] = []
        self.trade_callbacks[symbol].append(callback)
    
    def subscribe_bars(self, symbol: str, callback: Callable[[Bar], None]):
        """Subscribe to real-time bars for a symbol."""
        if symbol not in self.bar_callbacks:
            self.bar_callbacks[symbol] = []
        self.bar_callbacks[symbol].append(callback)
    
    def subscribe_orders(self, callback: Callable[[OrderUpdate], None]):
        """Subscribe to order status updates."""
        self.order_callbacks.append(callback)
    
    def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """Get the latest quote for a symbol."""
        return self.latest_quotes.get(symbol)
    
    def get_latest_trade(self, symbol: str) -> Optional[Trade]:
        """Get the latest trade for a symbol."""
        return self.latest_trades.get(symbol)
    
    def get_latest_bar(self, symbol: str) -> Optional[Bar]:
        """Get the latest bar for a symbol."""
        return self.latest_bars.get(symbol)
    
    def _handle_quote(self, quote: Quote):
        """Handle incoming quote data."""
        self.latest_quotes[quote.symbol] = quote
        
        # Call registered callbacks
        for callback in self.quote_callbacks.get(quote.symbol, []):
            try:
                callback(quote)
            except Exception as e:
                logger.error(f"Error in quote callback for {quote.symbol}: {e}")
    
    def _handle_trade(self, trade: Trade):
        """Handle incoming trade data."""
        self.latest_trades[trade.symbol] = trade
        
        # Call registered callbacks
        for callback in self.trade_callbacks.get(trade.symbol, []):
            try:
                callback(trade)
            except Exception as e:
                logger.error(f"Error in trade callback for {trade.symbol}: {e}")
    
    def _handle_bar(self, bar: Bar):
        """Handle incoming bar data."""
        self.latest_bars[bar.symbol] = bar
        
        # Call registered callbacks
        for callback in self.bar_callbacks.get(bar.symbol, []):
            try:
                callback(bar)
            except Exception as e:
                logger.error(f"Error in bar callback for {bar.symbol}: {e}")
    
    def _handle_order_update(self, order_update: OrderUpdate):
        """Handle incoming order updates."""
        # Call registered callbacks
        for callback in self.order_callbacks:
            try:
                callback(order_update)
            except Exception as e:
                logger.error(f"Error in order callback: {e}")
    
    def update_latency_metrics(self, message_timestamp: datetime):
        """Update latency tracking metrics."""
        now = time.time()
        if hasattr(message_timestamp, 'timestamp'):
            message_time = message_timestamp.timestamp()
        else:
            message_time = message_timestamp
        
        latency = (now - message_time) * 1000  # Convert to milliseconds
        self.latency_samples.append(latency)
        
        # Keep only last 1000 samples
        if len(self.latency_samples) > 1000:
            self.latency_samples.pop(0)
        
        self.message_count += 1
        self.last_message_time = now
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Get latency statistics."""
        if not self.latency_samples:
            return {"avg_latency_ms": 0, "min_latency_ms": 0, "max_latency_ms": 0}
        
        return {
            "avg_latency_ms": sum(self.latency_samples) / len(self.latency_samples),
            "min_latency_ms": min(self.latency_samples),
            "max_latency_ms": max(self.latency_samples),
            "message_count": self.message_count,
            "messages_per_second": self.message_count / max(1, time.time() - self.last_message_time + 60)
        }

class AlpacaWebSocketClient:
    """WebSocket client for Alpaca's real-time data streams."""
    
    def __init__(self, data_manager: MarketDataManager):
        self.data_manager = data_manager
        self.websocket = None
        self.running = False
        self.subscribed_symbols = set()
        self.subscribed_streams = set()
        
        # Alpaca WebSocket URLs (use paper trading URLs by default)
        self.market_data_url = "wss://stream.data.alpaca.markets/v2/iex"
        if "paper-api" in settings.alpaca_base_url:
            self.trading_url = "wss://paper-api.alpaca.markets/stream"
        else:
            self.trading_url = "wss://api.alpaca.markets/stream"
        
        self.auth_payload = {
            "action": "auth",
            "key": settings.alpaca_api_key,
            "secret": settings.alpaca_secret_key
        }
    
    async def connect_market_data(self):
        """Connect to Alpaca market data WebSocket."""
        try:
            logger.info("Connecting to Alpaca market data WebSocket...")
            self.websocket = await websockets.connect(self.market_data_url)
            
            # Authenticate
            await self.websocket.send(json.dumps(self.auth_payload))
            auth_response = await self.websocket.recv()
            auth_data = json.loads(auth_response)
            
            if auth_data.get("T") == "success":
                logger.info("✅ Market data WebSocket authenticated successfully")
                self.running = True
                return True
            else:
                logger.error(f"❌ Market data authentication failed: {auth_data}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to market data WebSocket: {e}")
            return False
    
    async def subscribe_symbols(self, symbols: List[str], streams: List[StreamType]):
        """Subscribe to real-time data for symbols."""
        if not self.websocket or not self.running:
            logger.error("WebSocket not connected")
            return False
        
        try:
            # Build subscription message
            subscription = {
                "action": "subscribe"
            }
            
            for stream in streams:
                if stream == StreamType.QUOTES:
                    subscription["quotes"] = symbols
                elif stream == StreamType.TRADES:
                    subscription["trades"] = symbols
                elif stream == StreamType.BARS:
                    subscription["bars"] = symbols
            
            await self.websocket.send(json.dumps(subscription))
            
            # Update tracking
            self.subscribed_symbols.update(symbols)
            self.subscribed_streams.update(streams)
            
            logger.info(f"📡 Subscribed to {streams} for symbols: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to symbols: {e}")
            return False
    
    async def listen(self):
        """Listen for incoming WebSocket messages."""
        if not self.websocket or not self.running:
            logger.error("WebSocket not connected")
            return
        
        logger.info("🎧 Starting WebSocket message listener...")
        
        try:
            async for message in self.websocket:
                await self._handle_message(message)
                
        except ConnectionClosed:
            logger.warning("⚠️ WebSocket connection closed")
            self.running = False
        except WebSocketException as e:
            logger.error(f"❌ WebSocket error: {e}")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Unexpected error in WebSocket listener: {e}")
            self.running = False
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            
            # Handle different message types
            msg_type = data.get("T")
            
            if msg_type == "q":  # Quote
                quote = self._parse_quote(data)
                if quote:
                    self.data_manager.update_latency_metrics(quote.timestamp)
                    self.data_manager._handle_quote(quote)
            
            elif msg_type == "t":  # Trade
                trade = self._parse_trade(data)
                if trade:
                    self.data_manager.update_latency_metrics(trade.timestamp)
                    self.data_manager._handle_trade(trade)
            
            elif msg_type == "b":  # Bar
                bar = self._parse_bar(data)
                if bar:
                    self.data_manager.update_latency_metrics(bar.timestamp)
                    self.data_manager._handle_bar(bar)
            
            elif msg_type == "trade_updates":  # Order update
                order_update = self._parse_order_update(data)
                if order_update:
                    self.data_manager._handle_order_update(order_update)
            
            elif msg_type in ["success", "subscription"]:
                logger.info(f"📨 WebSocket: {data}")
            
            elif msg_type == "error":
                logger.error(f"❌ WebSocket error: {data}")
            
        except Exception as e:
            logger.error(f"❌ Error parsing WebSocket message: {e}")
            logger.debug(f"Raw message: {message}")
    
    def _parse_quote(self, data: Dict) -> Optional[Quote]:
        """Parse quote message from Alpaca."""
        try:
            return Quote(
                symbol=data["S"],
                bid_price=float(data["bp"]),
                ask_price=float(data["ap"]),
                bid_size=int(data["bs"]),
                ask_size=int(data["as"]),
                timestamp=datetime.fromisoformat(data["t"].replace("Z", "+00:00")),
                conditions=data.get("c", [])
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing quote: {e}")
            return None
    
    def _parse_trade(self, data: Dict) -> Optional[Trade]:
        """Parse trade message from Alpaca."""
        try:
            return Trade(
                symbol=data["S"],
                price=float(data["p"]),
                size=int(data["s"]),
                timestamp=datetime.fromisoformat(data["t"].replace("Z", "+00:00")),
                conditions=data.get("c", []),
                exchange=data.get("x")
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing trade: {e}")
            return None
    
    def _parse_bar(self, data: Dict) -> Optional[Bar]:
        """Parse bar message from Alpaca."""
        try:
            return Bar(
                symbol=data["S"],
                open=float(data["o"]),
                high=float(data["h"]),
                low=float(data["l"]),
                close=float(data["c"]),
                volume=int(data["v"]),
                timestamp=datetime.fromisoformat(data["t"].replace("Z", "+00:00")),
                vwap=data.get("vw")
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing bar: {e}")
            return None
    
    def _parse_order_update(self, data: Dict) -> Optional[OrderUpdate]:
        """Parse order update message from Alpaca."""
        try:
            order_data = data.get("order", {})
            return OrderUpdate(
                order_id=order_data["id"],
                symbol=order_data["symbol"],
                side=order_data["side"],
                qty=float(order_data["qty"]),
                status=order_data["status"],
                event=data.get("event", ""),
                timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
                filled_qty=float(order_data.get("filled_qty", 0)),
                filled_price=float(order_data.get("filled_avg_price", 0)) if order_data.get("filled_avg_price") else None
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing order update: {e}")
            return None
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("🔌 WebSocket disconnected")

class RealTimeDataService:
    """High-level service for managing real-time market data."""
    
    def __init__(self):
        self.data_manager = MarketDataManager()
        self.ws_client = AlpacaWebSocketClient(self.data_manager)
        self.running = False
        self._tasks = []
    
    async def start(self, symbols: List[str], streams: List[StreamType] = None):
        """Start real-time data service."""
        if streams is None:
            streams = [StreamType.QUOTES, StreamType.TRADES]
        
        logger.info(f"🚀 Starting real-time data service for {len(symbols)} symbols")
        
        # Connect to WebSocket
        if not await self.ws_client.connect_market_data():
            raise Exception("Failed to connect to market data WebSocket")
        
        # Subscribe to symbols
        if not await self.ws_client.subscribe_symbols(symbols, streams):
            raise Exception("Failed to subscribe to symbols")
        
        # Start listening task
        listen_task = asyncio.create_task(self.ws_client.listen())
        self._tasks.append(listen_task)
        
        self.running = True
        logger.info("✅ Real-time data service started successfully")
    
    async def stop(self):
        """Stop real-time data service."""
        logger.info("🛑 Stopping real-time data service...")
        
        self.running = False
        
        # Cancel tasks
        for task in self._tasks:
            task.cancel()
        
        # Disconnect WebSocket
        await self.ws_client.disconnect()
        
        logger.info("✅ Real-time data service stopped")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol."""
        quote = self.data_manager.get_latest_quote(symbol)
        if quote:
            return quote.mid_price
        
        trade = self.data_manager.get_latest_trade(symbol)
        if trade:
            return trade.price
        
        return None
    
    def get_bid_ask_spread(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get current bid-ask spread information."""
        quote = self.data_manager.get_latest_quote(symbol)
        if quote:
            return {
                "bid": quote.bid_price,
                "ask": quote.ask_price,
                "spread": quote.spread,
                "spread_bps": quote.spread_bps,
                "mid": quote.mid_price
            }
        return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics."""
        latency_stats = self.data_manager.get_latency_stats()
        
        return {
            "connected": self.running,
            "subscribed_symbols": len(self.ws_client.subscribed_symbols),
            "subscribed_streams": list(self.ws_client.subscribed_streams),
            "latency_stats": latency_stats,
            "latest_quotes_count": len(self.data_manager.latest_quotes),
            "latest_trades_count": len(self.data_manager.latest_trades)
        }
