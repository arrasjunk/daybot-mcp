#!/usr/bin/env python3
"""
Simple rate-limited trading demo for DayBot MCP.
Demonstrates proper API usage with rate limiting and error handling.
"""

import asyncio
import httpx
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleTrader:
    """Simple trader with proper rate limiting."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def safe_request(self, method: str, endpoint: str, **kwargs):
        """Make a safe API request with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method.upper() == "GET":
                    response = await self.client.get(f"{self.base_url}{endpoint}")
                elif method.upper() == "POST":
                    response = await self.client.post(f"{self.base_url}{endpoint}", **kwargs)
                
                if response.status_code == 429:  # Rate limit
                    wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                    logger.warning(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                elif response.status_code >= 500:  # Server error
                    logger.warning(f"Server error {response.status_code}, retrying in 3s")
                    await asyncio.sleep(3)
                    continue
                
                return response.json()
                
            except Exception as e:
                logger.error(f"Request error: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    raise
        
        raise Exception("Max retries exceeded")
    
    async def get_health(self):
        """Get system health."""
        return await self.safe_request("GET", "/tools/healthcheck")
    
    async def get_risk_status(self):
        """Get risk status."""
        return await self.safe_request("GET", "/tools/risk_status")
    
    async def get_positions(self):
        """Get current positions."""
        return await self.safe_request("GET", "/positions")
    
    async def enter_trade(self, symbol: str, quantity: int = 1):
        """Enter a simple trade."""
        return await self.safe_request(
            "POST", 
            "/tools/enter_trade",
            json={
                "symbol": symbol,
                "side": "buy",
                "quantity": quantity,
                "order_type": "market"
            }
        )
    
    async def close_position(self, symbol: str):
        """Close a position."""
        return await self.safe_request(
            "POST",
            "/tools/close_symbol",
            json={"symbol": symbol}
        )
    
    async def demo_trading_session(self):
        """Run a demo trading session with proper rate limiting."""
        logger.info("🚀 Starting Simple Trading Demo")
        
        try:
            # 1. Check system health
            logger.info("1. Checking system health...")
            health = await self.get_health()
            logger.info(f"   Status: {health['status']}")
            logger.info(f"   Market Open: {health['market_open']}")
            logger.info(f"   Buying Power: ${health['buying_power']:,.2f}")
            
            # Wait between requests
            await asyncio.sleep(2)
            
            # 2. Check risk status
            logger.info("2. Checking risk status...")
            risk = await self.get_risk_status()
            logger.info(f"   Risk Level: {risk['risk_level']}")
            logger.info(f"   Daily P&L: ${risk['daily_pnl']:,.2f}")
            logger.info(f"   Positions: {risk['positions_count']}")
            
            # Wait between requests
            await asyncio.sleep(2)
            
            # 3. Check current positions
            logger.info("3. Checking current positions...")
            positions = await self.get_positions()
            logger.info(f"   Current positions: {len(positions)}")
            for pos in positions:
                pnl = pos.get('unrealized_pl', 0)
                logger.info(f"   - {pos['symbol']}: {pos['qty']} shares, P&L: ${pnl:.2f}")
            
            # Wait between requests
            await asyncio.sleep(3)
            
            # 4. Enter a small test trade (if no positions)
            if len(positions) == 0 and health.get('market_open'):
                logger.info("4. Entering test trade...")
                result = await self.enter_trade("SPY", 1)
                if result.get('success'):
                    logger.info(f"   ✅ Trade successful: {result['symbol']} - {result['quantity']} shares")
                else:
                    logger.warning(f"   ❌ Trade failed: {result.get('message')}")
                
                # Wait after trade
                await asyncio.sleep(5)
                
                # 5. Check positions again
                logger.info("5. Checking positions after trade...")
                positions = await self.get_positions()
                for pos in positions:
                    pnl = pos.get('unrealized_pl', 0)
                    logger.info(f"   - {pos['symbol']}: {pos['qty']} shares, P&L: ${pnl:.2f}")
                
                # Wait before closing
                await asyncio.sleep(3)
                
                # 6. Close the position
                if positions:
                    symbol = positions[0]['symbol']
                    logger.info(f"6. Closing position: {symbol}")
                    result = await self.close_position(symbol)
                    if result.get('success'):
                        logger.info(f"   ✅ Position closed successfully")
                    else:
                        logger.warning(f"   ❌ Close failed: {result.get('error_message')}")
            else:
                logger.info("4. Skipping trade (market closed or positions exist)")
            
            logger.info("✅ Demo trading session completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Demo session error: {str(e)}")


async def main():
    """Main function."""
    async with SimpleTrader() as trader:
        await trader.demo_trading_session()


if __name__ == "__main__":
    asyncio.run(main())
