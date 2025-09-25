#!/usr/bin/env python3
"""
Simple Momentum Trading Strategy Example for DayBot MCP.
This demonstrates how to build trading strategies using the MCP API.
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import sys
import os

# Add the parent directory to the path so we can import from daybot_mcp
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daybot_mcp.audit_logger import (
    initialize_audit_logger, 
    get_audit_logger, 
    close_audit_logger,
    EventType,
    LogLevel
)
from daybot_mcp.indicators import IndicatorManager, ATR
from daybot_mcp.risk import RiskManager
from daybot_mcp.correlation_controls import CorrelationLimits
from daybot_mcp.websocket_client import RealTimeDataService, StreamType, Quote, Trade

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MomentumStrategy:
    """
    Simple momentum trading strategy that:
    1. Scans for symbols with high volume
    2. Enters long positions on breakouts
    3. Uses ATR-based stops and targets
    4. Manages risk with position sizing
    """
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.positions = {}
        self.max_positions = 5
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.running = False
        self.audit_logger = None
        # Initialize risk manager with correlation controls
        correlation_limits = CorrelationLimits(
            max_positions_per_sector=2,      # Max 2 positions per sector
            max_sector_exposure_percent=30.0, # Max 30% in any sector
            max_beta_weighted_exposure=1.5,   # Limit market exposure
            max_high_beta_positions=3,        # Max 3 high-beta positions
            correlation_threshold=0.7,        # Consider 0.7+ as highly correlated
            max_correlated_positions=2        # Max 2 highly correlated positions
        )
        self.risk_manager = RiskManager(correlation_limits)
        self.indicators = {}  # Store IndicatorManager instances per symbol
        self.use_atr_stops = True  # Enable ATR-based dynamic stops
        
        # Real-time data service
        self.realtime_service = RealTimeDataService()
        self.use_realtime_data = True
        self.monitored_symbols = set()
        
        # Real-time price tracking
        self.current_prices = {}
        self.price_momentum = {}  # Track price momentum for signals
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        if self.use_realtime_data:
            await self.realtime_service.stop()
    
    async def get_health(self) -> Dict[str, Any]:
        """Check system health."""
        response = await self.client.get(f"{self.base_url}/tools/healthcheck")
        return response.json()
    
    async def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status."""
        response = await self.client.get(f"{self.base_url}/tools/risk_status")
        return response.json()
    
    async def scan_symbols(self) -> List[str]:
        """Scan for trading candidates."""
        if self.audit_logger:
            self.audit_logger.log_strategy_event(
                EventType.SYMBOL_SCAN,
                "Starting symbol scan for momentum candidates",
                "momentum_strategy",
                metadata={"volume_min": 1000000}
            )
        
        response = await self.client.post(
            f"{self.base_url}/tools/scan_symbols",
            json={"volume_min": 1000000}  # High volume stocks
        )
        data = response.json()
        symbols = data.get("symbols", [])
        
        if self.audit_logger:
            self.audit_logger.log_strategy_event(
                EventType.SYMBOL_SCAN,
                f"Symbol scan completed, found {len(symbols)} candidates",
                "momentum_strategy",
                metadata={"symbol_count": len(symbols), "symbols": symbols}
            )
        
        return symbols
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        try:
            response = await self.client.get(f"{self.base_url}/positions")
            return response.json()
        except Exception:
            return []
    
    async def get_symbol_atr(self, symbol: str) -> Optional[float]:
        """
        Get ATR value for a symbol. In a real implementation, this would
        fetch recent price data and calculate ATR.
        """
        try:
            # Placeholder: In real implementation, fetch recent bars and calculate ATR
            # For now, simulate ATR based on symbol characteristics
            if symbol in ['TSLA', 'NVDA', 'AMD']:  # High volatility stocks
                return 5.0
            elif symbol in ['AAPL', 'MSFT', 'GOOGL']:  # Medium volatility
                return 3.0
            else:  # Lower volatility
                return 2.0
        except Exception:
            return None
    
    def setup_realtime_callbacks(self):
        """Setup callbacks for real-time market data."""
        # Register quote handler for all monitored symbols
        for symbol in self.monitored_symbols:
            self.realtime_service.data_manager.subscribe_quotes(symbol, self._on_quote_update)
            self.realtime_service.data_manager.subscribe_trades(symbol, self._on_trade_update)
    
    def _on_quote_update(self, quote: Quote):
        """Handle real-time quote updates."""
        symbol = quote.symbol
        
        # Update current price tracking
        self.current_prices[symbol] = {
            'mid_price': quote.mid_price,
            'bid': quote.bid_price,
            'ask': quote.ask_price,
            'spread': quote.spread,
            'spread_bps': quote.spread_bps,
            'timestamp': quote.timestamp
        }
        
        # Update indicators if we have this symbol
        if symbol in self.indicators:
            # Update indicators with new price data
            bar_data = {
                'h': quote.ask_price,
                'l': quote.bid_price,
                'c': quote.mid_price,
                'v': 1000  # Placeholder volume
            }
            self.indicators[symbol].update(bar_data)
        
        # Check for momentum signals
        self._check_momentum_signal(symbol, quote.mid_price)
        
        # Log high-frequency updates for audit
        if self.audit_logger and symbol in self.positions:
            self.audit_logger.log_strategy_event(
                EventType.PRICE_UPDATE,
                f"Real-time quote update for {symbol}",
                "momentum_strategy",
                symbol=symbol,
                metadata={
                    'mid_price': quote.mid_price,
                    'spread_bps': quote.spread_bps,
                    'timestamp': quote.timestamp.isoformat()
                }
            )
    
    def _on_trade_update(self, trade: Trade):
        """Handle real-time trade updates."""
        symbol = trade.symbol
        
        # Update price momentum tracking
        if symbol not in self.price_momentum:
            self.price_momentum[symbol] = {'prices': [], 'timestamps': []}
        
        # Keep last 20 trades for momentum calculation
        self.price_momentum[symbol]['prices'].append(trade.price)
        self.price_momentum[symbol]['timestamps'].append(trade.timestamp)
        
        if len(self.price_momentum[symbol]['prices']) > 20:
            self.price_momentum[symbol]['prices'].pop(0)
            self.price_momentum[symbol]['timestamps'].pop(0)
        
        # Check for breakout patterns
        self._check_breakout_signal(symbol, trade.price, trade.size)
    
    def _check_momentum_signal(self, symbol: str, current_price: float):
        """Check for momentum signals based on real-time price action."""
        if symbol not in self.price_momentum or len(self.price_momentum[symbol]['prices']) < 10:
            return
        
        prices = self.price_momentum[symbol]['prices']
        
        # Calculate short-term momentum (last 5 vs previous 5 trades)
        if len(prices) >= 10:
            recent_avg = sum(prices[-5:]) / 5
            previous_avg = sum(prices[-10:-5]) / 5
            
            momentum_pct = ((recent_avg - previous_avg) / previous_avg) * 100
            
            # Strong momentum signal threshold
            if abs(momentum_pct) > 0.5:  # 0.5% momentum
                if self.audit_logger:
                    self.audit_logger.log_strategy_event(
                        EventType.MOMENTUM_SIGNAL,
                        f"Momentum signal detected for {symbol}: {momentum_pct:.2f}%",
                        "momentum_strategy",
                        symbol=symbol,
                        metadata={
                            'momentum_pct': momentum_pct,
                            'current_price': current_price,
                            'recent_avg': recent_avg,
                            'previous_avg': previous_avg
                        }
                    )
    
    def _check_breakout_signal(self, symbol: str, price: float, volume: int):
        """Check for volume-weighted breakout signals."""
        # Placeholder for sophisticated breakout detection
        # In a real implementation, this would analyze:
        # - Volume spikes
        # - Price level breaks
        # - Technical indicator confirmations
        
        if volume > 10000:  # High volume threshold
            logger.info(f"High volume trade detected: {symbol} @ ${price:.2f} (vol: {volume:,})")
    
    async def enter_trade(self, symbol: str, side: str = "buy") -> Dict[str, Any]:
        """Enter a new trade with risk management."""
        if self.audit_logger:
            self.audit_logger.log_strategy_event(
                EventType.ENTRY_SIGNAL,
                f"Entry signal generated for {symbol}",
                "momentum_strategy",
                symbol=symbol,
                metadata={"side": side, "risk_percent": self.risk_per_trade}
            )
        
        try:
            # Get current portfolio value for position sizing
            risk_status = await self.get_risk_status()
            portfolio_value = risk_status.get('portfolio_value', 100000)  # Default fallback
            
            # Calculate position size using ATR if available
            quantity = 1  # Default fallback
            if self.use_atr_stops:
                atr_value = await self.get_symbol_atr(symbol)
                if atr_value:
                    # Get current price from real-time data or fallback
                    entry_price = self.realtime_service.get_current_price(symbol) or 100.0
                    
                    # Calculate ATR-based position size
                    position_result = self.risk_manager.calculate_atr_position_size(
                        symbol=symbol,
                        entry_price=entry_price,
                        atr_value=atr_value,
                        portfolio_value=portfolio_value,
                        risk_percent=self.risk_per_trade
                    )
                    
                    quantity = max(1, position_result.recommended_shares)
                    
                    if self.audit_logger:
                        self.audit_logger.log_strategy_event(
                            EventType.POSITION_SIZING,
                            f"ATR-based position sizing for {symbol}",
                            "momentum_strategy",
                            symbol=symbol,
                            metadata={
                                "atr_value": atr_value,
                                "entry_price": entry_price,
                                "quantity": quantity,
                                "stop_loss": position_result.stop_loss_price,
                                "take_profit": position_result.take_profit_price,
                                "risk_amount": position_result.risk_amount,
                                "warnings": position_result.warnings
                            }
                        )
            
            response = await self.client.post(
                f"{self.base_url}/tools/enter_trade",
                json={
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "order_type": "market"
                }
            )
            result = response.json()
            
            if self.audit_logger:
                if result.get("success"):
                    self.audit_logger.log_strategy_event(
                        EventType.TRADE_ENTRY,
                        f"Trade entry successful for {symbol}",
                        "momentum_strategy",
                        symbol=symbol,
                        metadata=result
                    )
                else:
                    self.audit_logger.log_error(
                        f"Trade entry failed for {symbol}: {result.get('message')}",
                        "momentum_strategy",
                        metadata={"symbol": symbol, "result": result}
                    )
            
            return result
        except Exception as e:
            logger.error(f"Error entering trade for {symbol}: {str(e)}")
            if self.audit_logger:
                self.audit_logger.log_error(
                    f"Exception during trade entry for {symbol}: {str(e)}",
                    "momentum_strategy",
                    error=e,
                    metadata={"symbol": symbol}
                )
            return {"success": False, "message": str(e)}
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close a position."""
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/close_symbol",
                json={"symbol": symbol}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
            return {"success": False, "error_message": str(e)}
    
    async def adjust_stop_loss(self, symbol: str, new_stop: float) -> Dict[str, Any]:
        """Adjust stop loss for a position."""
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/manage_trade",
                json={
                    "symbol": symbol,
                    "action": "adjust_stop",
                    "new_stop_price": new_stop
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error adjusting stop for {symbol}: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def should_enter_trade(self, symbol: str) -> bool:
        """
        Simple momentum signal logic.
        In a real strategy, this would analyze price/volume data.
        """
        # Placeholder logic - replace with real technical analysis
        import random
        
        # Simulate momentum conditions
        momentum_score = random.random()
        volume_condition = True  # Would check actual volume
        price_condition = True   # Would check price breakout
        
        return (momentum_score > 0.7 and 
                volume_condition and 
                price_condition and
                symbol not in self.positions)
    
    def should_exit_trade(self, position: Dict[str, Any]) -> bool:
        """
        Exit signal logic with ATR-based dynamic exits.
        In a real strategy, this would analyze current market conditions.
        """
        symbol = position.get('symbol')
        unrealized_pl_pct = position.get('unrealized_plpc', 0)
        
        if self.use_atr_stops and symbol in self.indicators:
            # Use ATR-based exit logic (positions should hit their bracket orders)
            # Only exit manually if there's a strong reversal signal
            # For now, let bracket orders handle exits
            return False
        else:
            # Fallback to percentage-based exits
            return unrealized_pl_pct >= 4.0 or unrealized_pl_pct <= -2.0
    
    async def check_risk_limits(self) -> bool:
        """Check if we're within risk limits with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                risk_status = await self.get_risk_status()
                
                # Stop trading if daily loss limit is approached
                daily_loss_pct = risk_status.get('daily_pnl_percent', 0)
                if daily_loss_pct <= -3.0:  # Stop at 3% daily loss
                    logger.warning(f"Daily loss limit approached: {daily_loss_pct:.2f}%")
                    return False
                
                # Stop if portfolio heat is too high
                portfolio_heat = risk_status.get('portfolio_heat', {}).get('portfolio_heat_percent', 0)
                if portfolio_heat >= 15.0:  # Stop at 15% portfolio heat
                    logger.warning(f"Portfolio heat too high: {portfolio_heat:.1f}%")
                    return False
                
                return True
                
            except Exception as e:
                if "429" in str(e):  # Rate limit
                    wait_time = (2 ** attempt) * 1  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                elif "500" in str(e):  # Server error
                    logger.warning(f"Server error, retrying in 2s (attempt {attempt + 1})")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Risk check error: {str(e)}")
                    return False
        
        logger.error("Failed to check risk limits after retries")
        return False
    
    async def scan_for_entries(self):
        """Scan for new entry opportunities."""
        if len(self.positions) >= self.max_positions:
            logger.info(f"Max positions reached ({self.max_positions})")
            return
        
        # Get candidate symbols
        symbols = await self.scan_symbols()
        logger.info(f"Scanning {len(symbols)} symbols for entries")
        
        # Check each symbol for entry signals (with rate limiting)
        for i, symbol in enumerate(symbols[:10]):  # Reduced to top 10 to avoid rate limits
            if not await self.check_risk_limits():
                break
            
            if self.should_enter_trade(symbol):
                logger.info(f"Entry signal for {symbol}")
                
                # Add retry logic for trade entry
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        result = await self.enter_trade(symbol)
                        if result.get("success"):
                            self.positions[symbol] = {
                                "entry_time": datetime.now(),
                                "entry_price": result.get("entry_price"),
                                "quantity": result.get("quantity")
                            }
                            logger.info(f"Entered position: {symbol} @ {result.get('entry_price')}")
                            break
                        else:
                            if "429" in result.get('message', ''):
                                wait_time = 3 * (attempt + 1)
                                logger.warning(f"Rate limit on entry, waiting {wait_time}s")
                                await asyncio.sleep(wait_time)
                            else:
                                logger.warning(f"Failed to enter {symbol}: {result.get('message')}")
                                break
                    except Exception as e:
                        logger.error(f"Entry error for {symbol}: {str(e)}")
                        break
                
                # Longer delay between trades to respect rate limits
                await asyncio.sleep(3)
            
            # Add delay every few symbols to avoid overwhelming the API
            if (i + 1) % 3 == 0:
                await asyncio.sleep(2)
    
    async def manage_positions(self):
        """Manage existing positions."""
        current_positions = await self.get_positions()
        
        for position in current_positions:
            symbol = position.get('symbol')
            
            if self.should_exit_trade(position):
                logger.info(f"Exit signal for {symbol}")
                
                result = await self.close_position(symbol)
                if result.get("success"):
                    if symbol in self.positions:
                        entry_info = self.positions.pop(symbol)
                        pnl = position.get('unrealized_pl', 0)
                        logger.info(f"Closed position: {symbol}, P&L: ${pnl:.2f}")
                else:
                    logger.warning(f"Failed to close {symbol}: {result.get('error_message')}")
    
    async def run_strategy_cycle(self):
        """Run one complete strategy cycle."""
        try:
            # Check system health
            health = await self.get_health()
            if health.get("status") != "healthy":
                logger.error("System not healthy, skipping cycle")
                return
            
            # Check if market is open
            if not health.get("market_open"):
                logger.info("Market closed, skipping cycle")
                return
            
            # Check risk limits
            if not await self.check_risk_limits():
                logger.warning("Risk limits exceeded, skipping new entries")
                # Still manage existing positions
                await self.manage_positions()
                return
            
            # Manage existing positions first
            await self.manage_positions()
            
            # Look for new entries
            await self.scan_for_entries()
            
            # Log current status
            risk_status = await self.get_risk_status()
            logger.info(f"Cycle complete - Positions: {len(self.positions)}, "
                       f"Daily P&L: {risk_status.get('daily_pnl_percent', 0):.2f}%")
        
        except Exception as e:
            logger.error(f"Strategy cycle error: {str(e)}")
    
    async def run(self, cycle_interval: int = 120):  # Increased default to 2 minutes
        """Run the strategy continuously."""
        # Initialize audit logging for the strategy
        try:
            self.audit_logger = get_audit_logger()
        except RuntimeError:
            # Initialize if not already done
            initialize_audit_logger(
                log_dir="logs/strategy",
                environment="strategy"
            )
            self.audit_logger = get_audit_logger()
        
        logger.info("🚀 Starting Momentum Strategy with Real-Time Data & Advanced Risk Controls")
        logger.info(f"Max positions: {self.max_positions}")
        logger.info(f"Risk per trade: {self.risk_per_trade * 100:.1f}%")
        logger.info(f"ATR-based stops: {'Enabled' if self.use_atr_stops else 'Disabled'}")
        logger.info(f"Real-time data: {'Enabled' if self.use_realtime_data else 'Disabled'}")
        logger.info(f"Max positions per sector: {self.risk_manager.correlation_manager.limits.max_positions_per_sector}")
        logger.info(f"Max sector exposure: {self.risk_manager.correlation_manager.limits.max_sector_exposure_percent}%")
        logger.info(f"Max beta-weighted exposure: {self.risk_manager.correlation_manager.limits.max_beta_weighted_exposure}")
        logger.info(f"Cycle interval: {cycle_interval} seconds")
        
        # Initialize real-time data if enabled
        if self.use_realtime_data:
            try:
                # Get initial symbol list for monitoring
                symbols = await self.scan_symbols()
                self.monitored_symbols.update(symbols[:10])  # Monitor top 10 symbols
                
                logger.info(f"📡 Starting real-time data for {len(self.monitored_symbols)} symbols")
                await self.realtime_service.start(
                    list(self.monitored_symbols), 
                    [StreamType.QUOTES, StreamType.TRADES]
                )
                
                # Setup callbacks
                self.setup_realtime_callbacks()
                
                logger.info("✅ Real-time market data connected successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to start real-time data: {e}")
                logger.info("📊 Falling back to REST-only mode")
                self.use_realtime_data = False
        
        logger.info("⚠️  Using conservative rate limiting to avoid API limits")
        
        if self.audit_logger:
            self.audit_logger.log_system_event(
                EventType.SYSTEM_START,
                "Momentum Strategy started",
                metadata={
                    "max_positions": self.max_positions,
                    "risk_per_trade": self.risk_per_trade,
                    "cycle_interval": cycle_interval,
                    "atr_stops_enabled": self.use_atr_stops
                }
            )
        
        self.running = True
        
        try:
            while self.running:
                await self.run_strategy_cycle()
                logger.info(f"Cycle complete, waiting {cycle_interval}s for next cycle...")
                await asyncio.sleep(cycle_interval)
        
        except KeyboardInterrupt:
            logger.info("Strategy stopped by user")
        except Exception as e:
            logger.error(f"Strategy error: {str(e)}")
        finally:
            self.running = False
            logger.info("Strategy stopped")
    
    async def stop(self):
        """Stop the strategy and close all positions."""
        logger.info("Stopping strategy and closing all positions...")
        self.running = False
        
        # Close all positions
        try:
            response = await self.client.post(f"{self.base_url}/tools/flat_all")
            result = response.json()
            if result.get("success"):
                logger.info("All positions closed successfully")
            else:
                logger.error("Error closing positions")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")


async def main():
    """Main function to run the strategy."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Momentum Trading Strategy")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="DayBot MCP Server URL")
    parser.add_argument("--interval", type=int, default=60, help="Strategy cycle interval (seconds)")
    parser.add_argument("--max-positions", type=int, default=5, help="Maximum number of positions")
    parser.add_argument("--risk-per-trade", type=float, default=0.01, help="Risk per trade (decimal)")
    
    args = parser.parse_args()
    
    async with MomentumStrategy(args.url) as strategy:
        strategy.max_positions = args.max_positions
        strategy.risk_per_trade = args.risk_per_trade
        
        await strategy.run(args.interval)


if __name__ == "__main__":
    asyncio.run(main())
