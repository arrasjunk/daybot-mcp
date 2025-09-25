"""
Polygon.io WebSocket client for backup market data feeds.
Provides redundant real-time data source with automatic failover.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .websocket_client import Quote, Trade, Bar, MarketDataManager
from .config import settings

logger = logging.getLogger(__name__)

class PolygonWebSocketClient:
    """WebSocket client for Polygon.io real-time market data."""
    
    def __init__(self, data_manager: MarketDataManager, api_key: str):
        self.data_manager = data_manager
        self.api_key = api_key
        self.websocket = None
        self.running = False
        self.subscribed_symbols = set()
        
        # Polygon WebSocket URLs
        self.stocks_url = "wss://socket.polygon.io/stocks"
        self.crypto_url = "wss://socket.polygon.io/crypto"
        self.forex_url = "wss://socket.polygon.io/forex"
        
        self.connection_id = None
    
    async def connect(self, feed_type: str = "stocks"):
        """Connect to Polygon WebSocket."""
        try:
            url_map = {
                "stocks": self.stocks_url,
                "crypto": self.crypto_url,
                "forex": self.forex_url
            }
            
            url = url_map.get(feed_type, self.stocks_url)
            logger.info(f"Connecting to Polygon {feed_type} WebSocket...")
            
            self.websocket = await websockets.connect(url)
            
            # Authenticate
            auth_message = {
                "action": "auth",
                "params": self.api_key
            }
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for auth response
            auth_response = await self.websocket.recv()
            auth_data = json.loads(auth_response)
            
            if auth_data[0].get("status") == "auth_success":
                logger.info("✅ Polygon WebSocket authenticated successfully")
                self.running = True
                return True
            else:
                logger.error(f"❌ Polygon authentication failed: {auth_data}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Polygon WebSocket: {e}")
            return False
    
    async def subscribe_symbols(self, symbols: List[str], data_types: List[str] = None):
        """Subscribe to real-time data for symbols."""
        if not self.websocket or not self.running:
            logger.error("Polygon WebSocket not connected")
            return False
        
        if data_types is None:
            data_types = ["Q", "T"]  # Quotes and Trades
        
        try:
            # Build subscription message
            subscription = {
                "action": "subscribe",
                "params": ".".join([f"{dt}.{symbol}" for symbol in symbols for dt in data_types])
            }
            
            await self.websocket.send(json.dumps(subscription))
            
            # Update tracking
            self.subscribed_symbols.update(symbols)
            
            logger.info(f"📡 Polygon subscribed to {data_types} for symbols: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to Polygon symbols: {e}")
            return False
    
    async def listen(self):
        """Listen for incoming Polygon WebSocket messages."""
        if not self.websocket or not self.running:
            logger.error("Polygon WebSocket not connected")
            return
        
        logger.info("🎧 Starting Polygon WebSocket message listener...")
        
        try:
            async for message in self.websocket:
                await self._handle_message(message)
                
        except ConnectionClosed:
            logger.warning("⚠️ Polygon WebSocket connection closed")
            self.running = False
        except WebSocketException as e:
            logger.error(f"❌ Polygon WebSocket error: {e}")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Unexpected error in Polygon WebSocket listener: {e}")
            self.running = False
    
    async def _handle_message(self, message: str):
        """Handle incoming Polygon WebSocket message."""
        try:
            data_list = json.loads(message)
            
            for data in data_list:
                msg_type = data.get("ev")  # Event type
                
                if msg_type == "Q":  # Quote
                    quote = self._parse_polygon_quote(data)
                    if quote:
                        self.data_manager.update_latency_metrics(quote.timestamp)
                        self.data_manager._handle_quote(quote)
                
                elif msg_type == "T":  # Trade
                    trade = self._parse_polygon_trade(data)
                    if trade:
                        self.data_manager.update_latency_metrics(trade.timestamp)
                        self.data_manager._handle_trade(trade)
                
                elif msg_type == "AM":  # Aggregate minute bar
                    bar = self._parse_polygon_bar(data)
                    if bar:
                        self.data_manager.update_latency_metrics(bar.timestamp)
                        self.data_manager._handle_bar(bar)
                
                elif msg_type == "status":
                    logger.info(f"📨 Polygon status: {data}")
                
        except Exception as e:
            logger.error(f"❌ Error parsing Polygon message: {e}")
            logger.debug(f"Raw message: {message}")
    
    def _parse_polygon_quote(self, data: Dict) -> Optional[Quote]:
        """Parse Polygon quote message."""
        try:
            return Quote(
                symbol=data["sym"],
                bid_price=float(data["bp"]),
                ask_price=float(data["ap"]),
                bid_size=int(data["bs"]),
                ask_size=int(data["as"]),
                timestamp=datetime.fromtimestamp(data["t"] / 1000),  # Polygon uses milliseconds
                conditions=data.get("c", [])
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Polygon quote: {e}")
            return None
    
    def _parse_polygon_trade(self, data: Dict) -> Optional[Trade]:
        """Parse Polygon trade message."""
        try:
            return Trade(
                symbol=data["sym"],
                price=float(data["p"]),
                size=int(data["s"]),
                timestamp=datetime.fromtimestamp(data["t"] / 1000),
                conditions=data.get("c", []),
                exchange=data.get("x")
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Polygon trade: {e}")
            return None
    
    def _parse_polygon_bar(self, data: Dict) -> Optional[Bar]:
        """Parse Polygon aggregate bar message."""
        try:
            return Bar(
                symbol=data["sym"],
                open=float(data["o"]),
                high=float(data["h"]),
                low=float(data["l"]),
                close=float(data["c"]),
                volume=int(data["v"]),
                timestamp=datetime.fromtimestamp(data["s"] / 1000),  # Start time
                vwap=data.get("vw")
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Polygon bar: {e}")
            return None
    
    async def disconnect(self):
        """Disconnect from Polygon WebSocket."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("🔌 Polygon WebSocket disconnected")

class RedundantDataService:
    """Manages multiple data sources with automatic failover."""
    
    def __init__(self, polygon_api_key: str):
        self.data_manager = MarketDataManager()
        
        # Initialize clients
        from .websocket_client import AlpacaWebSocketClient
        self.alpaca_client = AlpacaWebSocketClient(self.data_manager)
        self.polygon_client = PolygonWebSocketClient(self.data_manager, polygon_api_key)
        
        # Connection status
        self.alpaca_connected = False
        self.polygon_connected = False
        self.primary_source = "alpaca"  # Primary data source
        
        # Failover settings
        self.failover_timeout = 5.0  # Seconds before failover
        self.last_message_time = time.time()
        self.monitoring_task = None
    
    async def start(self, symbols: List[str], streams: List[str] = None):
        """Start redundant data service with automatic failover."""
        logger.info("🚀 Starting redundant data service with Alpaca + Polygon")
        
        # Try to connect to both sources
        self.alpaca_connected = await self.alpaca_client.connect_market_data()
        self.polygon_connected = await self.polygon_client.connect()
        
        if not self.alpaca_connected and not self.polygon_connected:
            raise Exception("Failed to connect to any data source")
        
        # Subscribe to symbols on available sources
        if self.alpaca_connected:
            from .websocket_client import StreamType
            stream_types = [StreamType.QUOTES, StreamType.TRADES] if streams is None else streams
            await self.alpaca_client.subscribe_symbols(symbols, stream_types)
        
        if self.polygon_connected:
            data_types = ["Q", "T"] if streams is None else streams
            await self.polygon_client.subscribe_symbols(symbols, data_types)
        
        # Start listeners
        tasks = []
        if self.alpaca_connected:
            tasks.append(asyncio.create_task(self.alpaca_client.listen()))
        if self.polygon_connected:
            tasks.append(asyncio.create_task(self.polygon_client.listen()))
        
        # Start connection monitoring
        self.monitoring_task = asyncio.create_task(self._monitor_connections())
        
        logger.info(f"✅ Redundant data service started - Sources: "
                   f"Alpaca({'✅' if self.alpaca_connected else '❌'}), "
                   f"Polygon({'✅' if self.polygon_connected else '❌'})")
    
    async def _monitor_connections(self):
        """Monitor connection health and handle failover."""
        while True:
            try:
                current_time = time.time()
                
                # Check if we haven't received data recently
                if current_time - self.last_message_time > self.failover_timeout:
                    await self._handle_failover()
                
                # Check individual connection status
                if self.primary_source == "alpaca" and not self.alpaca_client.running:
                    logger.warning("⚠️ Alpaca connection lost, switching to Polygon")
                    self.primary_source = "polygon"
                
                elif self.primary_source == "polygon" and not self.polygon_client.running:
                    logger.warning("⚠️ Polygon connection lost, switching to Alpaca")
                    self.primary_source = "alpaca"
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"❌ Error in connection monitoring: {e}")
                await asyncio.sleep(5)
    
    async def _handle_failover(self):
        """Handle automatic failover between data sources."""
        if self.primary_source == "alpaca" and self.polygon_connected:
            logger.warning("🔄 Failing over from Alpaca to Polygon")
            self.primary_source = "polygon"
        elif self.primary_source == "polygon" and self.alpaca_connected:
            logger.warning("🔄 Failing over from Polygon to Alpaca")
            self.primary_source = "alpaca"
        else:
            logger.error("❌ No backup data source available for failover")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from active data source."""
        return self.data_manager.get_latest_quote(symbol).mid_price if self.data_manager.get_latest_quote(symbol) else None
    
    def get_connection_status(self) -> Dict[str, any]:
        """Get status of all data connections."""
        return {
            "primary_source": self.primary_source,
            "alpaca_connected": self.alpaca_connected and self.alpaca_client.running,
            "polygon_connected": self.polygon_connected and self.polygon_client.running,
            "last_message_age": time.time() - self.last_message_time,
            "total_messages": self.data_manager.message_count,
            "latency_stats": self.data_manager.get_latency_stats()
        }
    
    async def stop(self):
        """Stop redundant data service."""
        logger.info("🛑 Stopping redundant data service...")
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        if self.alpaca_connected:
            await self.alpaca_client.disconnect()
        
        if self.polygon_connected:
            await self.polygon_client.disconnect()
        
        logger.info("✅ Redundant data service stopped")
