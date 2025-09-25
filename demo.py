#!/usr/bin/env python3
"""
Demo script for DayBot MCP Trading Server.
Shows how to interact with the API endpoints.
"""

import asyncio
import httpx
import json
from datetime import datetime


class DayBotClient:
    """Simple client for DayBot MCP API."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def healthcheck(self):
        """Check server health."""
        response = await self.client.get(f"{self.base_url}/tools/healthcheck")
        return response.json()
    
    async def scan_symbols(self, criteria=None):
        """Scan for trading symbols."""
        data = criteria or {}
        response = await self.client.post(
            f"{self.base_url}/tools/scan_symbols",
            json=data
        )
        return response.json()
    
    async def risk_status(self):
        """Get current risk status."""
        response = await self.client.get(f"{self.base_url}/tools/risk_status")
        return response.json()
    
    async def enter_trade(self, symbol, side, **kwargs):
        """Enter a new trade."""
        data = {"symbol": symbol, "side": side, **kwargs}
        response = await self.client.post(
            f"{self.base_url}/tools/enter_trade",
            json=data
        )
        return response.json()
    
    async def get_positions(self):
        """Get current positions."""
        response = await self.client.get(f"{self.base_url}/positions")
        return response.json()
    
    async def get_orders(self, status="open"):
        """Get orders by status."""
        response = await self.client.get(
            f"{self.base_url}/orders",
            params={"status": status}
        )
        return response.json()


async def demo():
    """Run the demo."""
    print("🚀 DayBot MCP Trading Server Demo")
    print("=" * 50)
    
    async with DayBotClient() as client:
        try:
            # 1. Health Check
            print("\n1. Health Check:")
            health = await client.healthcheck()
            print(f"   Status: {health['status']}")
            print(f"   Account: {health['account_status']}")
            print(f"   Market Open: {health['market_open']}")
            print(f"   Portfolio Value: ${health['portfolio_value']:,.2f}")
            print(f"   Buying Power: ${health['buying_power']:,.2f}")
            
            # 2. Risk Status
            print("\n2. Risk Status:")
            risk = await client.risk_status()
            print(f"   Risk Level: {risk['risk_level']}")
            print(f"   Daily P&L: ${risk['daily_pnl']:,.2f} ({risk['daily_pnl_percent']:.2f}%)")
            print(f"   Portfolio Heat: {risk['portfolio_heat']['portfolio_heat_percent']:.1f}%")
            print(f"   Positions: {risk['positions_count']}")
            
            # 3. Scan Symbols
            print("\n3. Symbol Scanner:")
            symbols = await client.scan_symbols()
            print(f"   Found {len(symbols['symbols'])} symbols:")
            print(f"   {', '.join(symbols['symbols'][:10])}...")
            
            # 4. Current Positions
            print("\n4. Current Positions:")
            try:
                positions = await client.get_positions()
                if positions:
                    for pos in positions:
                        print(f"   {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']:.2f}")
                else:
                    print("   No open positions")
            except Exception as e:
                print(f"   Error getting positions: {str(e)}")
            
            # 5. Open Orders
            print("\n5. Open Orders:")
            try:
                orders = await client.get_orders()
                if orders:
                    for order in orders:
                        print(f"   {order['symbol']}: {order['side']} {order['qty']} @ {order.get('limit_price', 'market')}")
                else:
                    print("   No open orders")
            except Exception as e:
                print(f"   Error getting orders: {str(e)}")
            
            # 6. Demo Trade (Note: This will fail without real API keys)
            print("\n6. Demo Trade Entry (will fail without real Alpaca keys):")
            try:
                trade_result = await client.enter_trade(
                    symbol="AAPL",
                    side="buy",
                    quantity=1,
                    order_type="market"
                )
                print(f"   Trade Result: {trade_result['success']}")
                if trade_result['success']:
                    print(f"   Order IDs: {trade_result['order_ids']}")
                else:
                    print(f"   Error: {trade_result['message']}")
            except Exception as e:
                print(f"   Expected error (no real API keys): {str(e)}")
        
        except Exception as e:
            print(f"❌ Demo failed: {str(e)}")
            return
    
    print("\n✅ Demo completed successfully!")
    print("\n📚 Next Steps:")
    print("   1. Get real Alpaca API keys from https://app.alpaca.markets/")
    print("   2. Update the .env file with your credentials")
    print("   3. Visit http://127.0.0.1:8000/docs for API documentation")
    print("   4. Start building your trading strategies!")


if __name__ == "__main__":
    asyncio.run(demo())
