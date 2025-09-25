#!/usr/bin/env python3
"""
Real-time monitoring dashboard for DayBot MCP Trading Server.
Displays key metrics and system status in the terminal.
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
import os


class DayBotMonitor:
    """Real-time monitoring for DayBot MCP."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)
        self.running = True
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    async def get_health(self):
        """Get health status."""
        try:
            response = await self.client.get(f"{self.base_url}/tools/healthcheck")
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_risk_status(self):
        """Get risk status."""
        try:
            response = await self.client.get(f"{self.base_url}/tools/risk_status")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_positions(self):
        """Get current positions."""
        try:
            response = await self.client.get(f"{self.base_url}/positions")
            return response.json()
        except Exception as e:
            return []
    
    async def get_orders(self):
        """Get open orders."""
        try:
            response = await self.client.get(f"{self.base_url}/orders")
            return response.json()
        except Exception as e:
            return []
    
    async def get_trade_log(self, limit=10):
        """Get recent trades."""
        try:
            response = await self.client.get(f"{self.base_url}/trade_log?limit={limit}")
            return response.json()
        except Exception as e:
            return {"events": [], "total_events": 0}
    
    def format_currency(self, amount):
        """Format currency for display."""
        if abs(amount) >= 1000000:
            return f"${amount/1000000:.2f}M"
        elif abs(amount) >= 1000:
            return f"${amount/1000:.1f}K"
        else:
            return f"${amount:.2f}"
    
    def format_percentage(self, value):
        """Format percentage for display."""
        color = ""
        reset = "\033[0m"
        
        if value > 0:
            color = "\033[92m"  # Green
        elif value < 0:
            color = "\033[91m"  # Red
        
        return f"{color}{value:+.2f}%{reset}"
    
    def print_header(self):
        """Print dashboard header."""
        print("=" * 80)
        print("🤖 DayBot MCP Trading Server - Live Monitor")
        print("=" * 80)
        print(f"⏰ Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def print_health_status(self, health):
        """Print health status section."""
        print("🏥 SYSTEM HEALTH")
        print("-" * 40)
        
        if health.get("status") == "healthy":
            status_icon = "✅"
            status_color = "\033[92m"
        else:
            status_icon = "❌"
            status_color = "\033[91m"
        
        reset = "\033[0m"
        
        print(f"Status: {status_icon} {status_color}{health.get('status', 'unknown').upper()}{reset}")
        print(f"Account: {health.get('account_status', 'unknown')}")
        print(f"Market: {'🟢 OPEN' if health.get('market_open') else '🔴 CLOSED'}")
        print(f"Portfolio: {self.format_currency(health.get('portfolio_value', 0))}")
        print(f"Buying Power: {self.format_currency(health.get('buying_power', 0))}")
        print()
    
    def print_risk_status(self, risk):
        """Print risk status section."""
        print("⚠️  RISK MANAGEMENT")
        print("-" * 40)
        
        risk_level = risk.get('risk_level', 'unknown')
        risk_colors = {
            'low': '\033[92m',      # Green
            'medium': '\033[93m',   # Yellow
            'high': '\033[91m',     # Red
            'critical': '\033[95m'  # Magenta
        }
        
        color = risk_colors.get(risk_level, '')
        reset = '\033[0m'
        
        print(f"Risk Level: {color}{risk_level.upper()}{reset}")
        print(f"Daily P&L: {self.format_currency(risk.get('daily_pnl', 0))} {self.format_percentage(risk.get('daily_pnl_percent', 0))}")
        print(f"Portfolio Heat: {risk.get('portfolio_heat', {}).get('portfolio_heat_percent', 0):.1f}%")
        print(f"Max Daily Loss: {risk.get('max_daily_loss_percent', 0):.1f}%")
        print(f"Positions: {risk.get('positions_count', 0)}")
        print(f"Total Exposure: {self.format_currency(risk.get('total_exposure', 0))}")
        print()
    
    def print_positions(self, positions):
        """Print positions section."""
        print("📊 CURRENT POSITIONS")
        print("-" * 40)
        
        if not positions:
            print("No open positions")
        else:
            print(f"{'Symbol':<8} {'Qty':<8} {'Price':<10} {'P&L':<12} {'P&L%':<8}")
            print("-" * 50)
            
            for pos in positions[:10]:  # Show max 10 positions
                symbol = pos.get('symbol', '')
                qty = pos.get('qty', 0)
                price = pos.get('current_price', 0)
                pnl = pos.get('unrealized_pl', 0)
                pnl_pct = pos.get('unrealized_plpc', 0)
                
                print(f"{symbol:<8} {qty:<8.0f} {price:<10.2f} {self.format_currency(pnl):<12} {self.format_percentage(pnl_pct):<8}")
        
        print()
    
    def print_orders(self, orders):
        """Print orders section."""
        print("📋 OPEN ORDERS")
        print("-" * 40)
        
        if not orders:
            print("No open orders")
        else:
            print(f"{'Symbol':<8} {'Side':<6} {'Qty':<8} {'Type':<10} {'Price':<10}")
            print("-" * 50)
            
            for order in orders[:10]:  # Show max 10 orders
                symbol = order.get('symbol', '')
                side = order.get('side', '')
                qty = order.get('qty', 0)
                order_type = order.get('order_type', '')
                price = order.get('limit_price') or order.get('stop_price') or 'Market'
                
                print(f"{symbol:<8} {side:<6} {qty:<8.0f} {order_type:<10} {str(price):<10}")
        
        print()
    
    def print_recent_trades(self, trade_log):
        """Print recent trades section."""
        print("📈 RECENT TRADES")
        print("-" * 40)
        
        events = trade_log.get('events', [])
        if not events:
            print("No recent trades")
        else:
            print(f"{'Time':<8} {'Symbol':<8} {'Type':<8} {'Side':<6} {'Qty':<8} {'Price':<10}")
            print("-" * 60)
            
            for event in events[-5:]:  # Show last 5 trades
                timestamp = event.get('timestamp', '')
                time_str = timestamp.split('T')[1][:8] if 'T' in timestamp else ''
                symbol = event.get('symbol', '')
                event_type = event.get('event_type', '')
                side = event.get('side', '')
                qty = event.get('quantity', 0)
                price = event.get('price', 0)
                
                print(f"{time_str:<8} {symbol:<8} {event_type:<8} {side:<6} {qty:<8.0f} {price:<10.2f}")
        
        print()
    
    def print_footer(self):
        """Print dashboard footer."""
        print("-" * 80)
        print("Press Ctrl+C to exit | Refresh every 5 seconds")
        print("=" * 80)
    
    async def display_dashboard(self):
        """Display the complete dashboard."""
        # Fetch all data concurrently
        health_task = asyncio.create_task(self.get_health())
        risk_task = asyncio.create_task(self.get_risk_status())
        positions_task = asyncio.create_task(self.get_positions())
        orders_task = asyncio.create_task(self.get_orders())
        trades_task = asyncio.create_task(self.get_trade_log())
        
        # Wait for all tasks to complete
        health = await health_task
        risk = await risk_task
        positions = await positions_task
        orders = await orders_task
        trades = await trades_task
        
        # Clear screen and display dashboard
        self.clear_screen()
        self.print_header()
        self.print_health_status(health)
        self.print_risk_status(risk)
        self.print_positions(positions)
        self.print_orders(orders)
        self.print_recent_trades(trades)
        self.print_footer()
    
    async def run(self, refresh_interval=5):
        """Run the monitoring dashboard."""
        print("🚀 Starting DayBot MCP Monitor...")
        print("Connecting to server...")
        
        try:
            while self.running:
                await self.display_dashboard()
                await asyncio.sleep(refresh_interval)
        
        except KeyboardInterrupt:
            print("\n\n👋 Monitor stopped by user")
        except Exception as e:
            print(f"\n\n❌ Monitor error: {str(e)}")
        finally:
            self.running = False


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DayBot MCP Monitor")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Server URL")
    parser.add_argument("--interval", type=int, default=5, help="Refresh interval in seconds")
    
    args = parser.parse_args()
    
    async with DayBotMonitor(args.url) as monitor:
        await monitor.run(args.interval)


if __name__ == "__main__":
    asyncio.run(main())
