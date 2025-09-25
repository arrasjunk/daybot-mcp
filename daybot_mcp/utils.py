"""
Utility functions for trading operations.
Includes position closing with verification and other helper functions.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel

from .alpaca_client import AlpacaClient, Position, Order


class CloseResult(BaseModel):
    """Result of a position close operation."""
    symbol: str
    success: bool
    initial_qty: float
    closed_qty: float
    remaining_qty: float
    close_price: Optional[float]
    orders_cancelled: int
    verification_attempts: int
    error_message: Optional[str]
    timestamp: str


class TradeEvent(BaseModel):
    """Structured trade event for logging."""
    event_type: str  # "entry", "exit", "partial_exit", "stop_hit", "target_hit"
    symbol: str
    timestamp: str
    price: float
    quantity: float
    side: str  # "buy", "sell"
    order_id: Optional[str]
    pnl: Optional[float]
    reason: Optional[str]
    metadata: Dict[str, Any] = {}


async def close_with_verification(
    alpaca_client: AlpacaClient,
    symbol: str,
    qty: Optional[float] = None,
    max_attempts: int = 3,
    verification_delay: float = 2.0
) -> CloseResult:
    """
    Close a position with verification that it was actually closed.
    
    Args:
        alpaca_client: Alpaca client instance
        symbol: Symbol to close
        qty: Quantity to close (None for full position)
        max_attempts: Maximum verification attempts
        verification_delay: Seconds to wait between attempts
    
    Returns:
        CloseResult with details of the operation
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Get initial position
    initial_position = await alpaca_client.get_position(symbol)
    if not initial_position:
        return CloseResult(
            symbol=symbol,
            success=False,
            initial_qty=0.0,
            closed_qty=0.0,
            remaining_qty=0.0,
            close_price=None,
            orders_cancelled=0,
            verification_attempts=0,
            error_message=f"No position found for {symbol}",
            timestamp=timestamp
        )
    
    initial_qty = float(initial_position.qty)
    target_close_qty = qty if qty is not None else abs(initial_qty)
    
    # Cancel any existing orders for this symbol first
    orders_cancelled = await cancel_symbol_orders(alpaca_client, symbol)
    
    try:
        # Submit close order
        close_order = await alpaca_client.close_position(symbol, qty)
        close_price = None
        
        # Verification loop
        for attempt in range(max_attempts):
            await asyncio.sleep(verification_delay)
            
            # Check current position
            current_position = await alpaca_client.get_position(symbol)
            current_qty = float(current_position.qty) if current_position else 0.0
            
            # Check if order was filled
            order_status = await alpaca_client.get_order(close_order.id)
            if order_status and order_status.status == "filled":
                close_price = order_status.filled_avg_price
                break
            
            # If position is closed or reduced as expected, consider it successful
            if qty is None and current_qty == 0:
                # Full close successful
                break
            elif qty is not None and abs(current_qty) <= abs(initial_qty) - target_close_qty:
                # Partial close successful
                break
        
        # Final position check
        final_position = await alpaca_client.get_position(symbol)
        final_qty = float(final_position.qty) if final_position else 0.0
        closed_qty = abs(initial_qty) - abs(final_qty)
        
        success = (qty is None and final_qty == 0) or (qty is not None and closed_qty >= target_close_qty * 0.95)
        
        return CloseResult(
            symbol=symbol,
            success=success,
            initial_qty=initial_qty,
            closed_qty=closed_qty,
            remaining_qty=final_qty,
            close_price=close_price,
            orders_cancelled=orders_cancelled,
            verification_attempts=max_attempts,
            error_message=None if success else "Position not fully closed as expected",
            timestamp=timestamp
        )
    
    except Exception as e:
        return CloseResult(
            symbol=symbol,
            success=False,
            initial_qty=initial_qty,
            closed_qty=0.0,
            remaining_qty=initial_qty,
            close_price=None,
            orders_cancelled=orders_cancelled,
            verification_attempts=0,
            error_message=str(e),
            timestamp=timestamp
        )


async def cancel_symbol_orders(alpaca_client: AlpacaClient, symbol: str) -> int:
    """
    Cancel all open orders for a specific symbol.
    
    Returns:
        Number of orders cancelled
    """
    try:
        orders = await alpaca_client.get_orders(status="open")
        symbol_orders = [order for order in orders if order.symbol == symbol]
        
        cancelled_count = 0
        for order in symbol_orders:
            if await alpaca_client.cancel_order(order.id):
                cancelled_count += 1
        
        return cancelled_count
    except Exception:
        return 0


async def flatten_all_positions(alpaca_client: AlpacaClient) -> Dict[str, Any]:
    """
    Flatten all positions and cancel all orders.
    
    Returns:
        Summary of the flattening operation
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    try:
        # Get all positions and orders
        positions = await alpaca_client.get_positions()
        orders = await alpaca_client.get_orders(status="open")
        
        # Cancel all orders first
        orders_cancelled = 0
        if await alpaca_client.cancel_all_orders():
            orders_cancelled = len(orders)
        
        # Close all positions
        close_results = []
        for position in positions:
            result = await close_with_verification(alpaca_client, position.symbol)
            close_results.append(result)
        
        successful_closes = sum(1 for result in close_results if result.success)
        
        return {
            "success": successful_closes == len(positions),
            "timestamp": timestamp,
            "positions_closed": successful_closes,
            "total_positions": len(positions),
            "orders_cancelled": orders_cancelled,
            "close_results": [result.dict() for result in close_results]
        }
    
    except Exception as e:
        return {
            "success": False,
            "timestamp": timestamp,
            "error": str(e),
            "positions_closed": 0,
            "total_positions": 0,
            "orders_cancelled": 0
        }


def calculate_pnl(
    entry_price: float,
    exit_price: float,
    quantity: float,
    side: str
) -> float:
    """
    Calculate P&L for a trade.
    
    Args:
        entry_price: Entry price per share
        exit_price: Exit price per share
        quantity: Number of shares (positive)
        side: "buy" for long, "sell" for short
    
    Returns:
        P&L in dollars
    """
    if side.lower() == "buy":
        # Long position
        return (exit_price - entry_price) * quantity
    else:
        # Short position
        return (entry_price - exit_price) * quantity


def format_currency(amount: float) -> str:
    """Format a dollar amount for display."""
    if abs(amount) >= 1000000:
        return f"${amount/1000000:.2f}M"
    elif abs(amount) >= 1000:
        return f"${amount/1000:.1f}K"
    else:
        return f"${amount:.2f}"


def format_percentage(value: float) -> str:
    """Format a percentage for display."""
    return f"{value:.2f}%"


def is_market_hours() -> bool:
    """
    Check if current time is during regular market hours (9:30 AM - 4:00 PM ET).
    This is a simple check and doesn't account for holidays.
    """
    from datetime import datetime
    import pytz
    
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)
    
    # Check if it's a weekday
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check if it's during market hours (9:30 AM - 4:00 PM ET)
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now <= market_close


def calculate_position_size_by_dollar_risk(
    account_value: float,
    risk_percent: float,
    entry_price: float,
    stop_price: float
) -> int:
    """
    Calculate position size based on dollar risk.
    
    Args:
        account_value: Total account value
        risk_percent: Risk as percentage (e.g., 0.02 for 2%)
        entry_price: Entry price per share
        stop_price: Stop loss price per share
    
    Returns:
        Number of shares to buy
    """
    dollar_risk = account_value * risk_percent
    risk_per_share = abs(entry_price - stop_price)
    
    if risk_per_share == 0:
        return 0
    
    shares = int(dollar_risk / risk_per_share)
    return max(0, shares)


def create_trade_event(
    event_type: str,
    symbol: str,
    price: float,
    quantity: float,
    side: str,
    order_id: Optional[str] = None,
    pnl: Optional[float] = None,
    reason: Optional[str] = None,
    **metadata
) -> TradeEvent:
    """Create a structured trade event for logging."""
    return TradeEvent(
        event_type=event_type,
        symbol=symbol,
        timestamp=datetime.now(timezone.utc).isoformat(),
        price=price,
        quantity=quantity,
        side=side,
        order_id=order_id,
        pnl=pnl,
        reason=reason,
        metadata=metadata
    )


async def wait_for_order_fill(
    alpaca_client: AlpacaClient,
    order_id: str,
    timeout_seconds: int = 60,
    check_interval: float = 1.0
) -> Optional[Order]:
    """
    Wait for an order to be filled.
    
    Args:
        alpaca_client: Alpaca client instance
        order_id: Order ID to monitor
        timeout_seconds: Maximum time to wait
        check_interval: How often to check (seconds)
    
    Returns:
        Order object if filled, None if timeout
    """
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
        order = await alpaca_client.get_order(order_id)
        
        if order and order.status in ["filled", "partially_filled"]:
            return order
        elif order and order.status in ["cancelled", "rejected", "expired"]:
            return order
        
        await asyncio.sleep(check_interval)
    
    return None


def validate_symbol(symbol: str) -> bool:
    """
    Basic symbol validation.
    
    Args:
        symbol: Stock symbol to validate
    
    Returns:
        True if symbol appears valid
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Remove whitespace and convert to uppercase
    symbol = symbol.strip().upper()
    
    # Basic checks
    if len(symbol) < 1 or len(symbol) > 5:
        return False
    
    # Should only contain letters
    if not symbol.isalpha():
        return False
    
    return True


def round_to_tick_size(price: float, tick_size: float = 0.01) -> float:
    """
    Round price to the nearest tick size.
    
    Args:
        price: Price to round
        tick_size: Minimum price increment (default 0.01 for stocks)
    
    Returns:
        Rounded price
    """
    return round(price / tick_size) * tick_size
