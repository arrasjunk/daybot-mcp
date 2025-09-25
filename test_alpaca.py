#!/usr/bin/env python3
"""
Test script to debug Alpaca API connection and order submission.
"""

import asyncio
import os
from daybot_mcp.alpaca_client import AlpacaClient
from daybot_mcp.config import settings

async def test_alpaca_connection():
    """Test the Alpaca API connection and basic operations."""
    print("🔍 Testing Alpaca API Connection...")
    print(f"Base URL: {settings.alpaca_base_url}")
    print(f"API Key: {settings.alpaca_api_key[:8]}...")
    print()
    
    async with AlpacaClient() as client:
        try:
            # Test 1: Get account info
            print("1. Testing account info...")
            account = await client.get_account()
            print(f"   ✅ Account ID: {account.id}")
            print(f"   ✅ Status: {account.status}")
            print(f"   ✅ Buying Power: ${account.buying_power:,.2f}")
            print()
            
            # Test 2: Get market clock
            print("2. Testing market clock...")
            clock = await client.get_clock()
            print(f"   ✅ Market Open: {clock.get('is_open')}")
            print(f"   ✅ Next Open: {clock.get('next_open')}")
            print()
            
            # Test 3: Get positions
            print("3. Testing positions...")
            positions = await client.get_positions()
            print(f"   ✅ Current Positions: {len(positions)}")
            for pos in positions:
                print(f"      - {pos.symbol}: {pos.qty} shares")
            print()
            
            # Test 4: Get orders
            print("4. Testing orders...")
            orders = await client.get_orders()
            print(f"   ✅ Open Orders: {len(orders)}")
            for order in orders:
                print(f"      - {order.symbol}: {order.side} {order.qty} @ {order.order_type}")
            print()
            
            # Test 5: Get latest quote for AAPL
            print("5. Testing market data...")
            try:
                quote = await client.get_latest_quote("AAPL")
                print(f"   ✅ AAPL Quote: Bid ${quote.get('bp', 0):.2f} / Ask ${quote.get('ap', 0):.2f}")
            except Exception as e:
                print(f"   ⚠️  Quote Error: {str(e)}")
            print()
            
            # Test 6: Try a simple order (this might fail, that's OK)
            print("6. Testing order submission...")
            try:
                # Try to submit a very small order
                order = await client.submit_order(
                    symbol="AAPL",
                    qty=1,
                    side="buy",
                    order_type="market",
                    time_in_force="day"
                )
                print(f"   ✅ Order Submitted: {order.id}")
                
                # Cancel it immediately
                await client.cancel_order(order.id)
                print(f"   ✅ Order Cancelled: {order.id}")
                
            except Exception as e:
                print(f"   ❌ Order Error: {str(e)}")
                print(f"      This might be normal for paper trading or market hours")
            print()
            
            print("🎉 Alpaca API connection test completed!")
            
        except Exception as e:
            print(f"❌ Connection Error: {str(e)}")
            print("Check your API keys and network connection.")

if __name__ == "__main__":
    asyncio.run(test_alpaca_connection())
