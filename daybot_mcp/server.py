"""
FastAPI server with MCP tool endpoints for algorithmic trading.
Provides REST endpoints following MCP schema for trading operations.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging

from .config import settings, validate_config
from .alpaca_client import AlpacaClient
from .risk import RiskManager, PositionSizeResult
from .utils import (
    close_with_verification, 
    flatten_all_positions, 
    create_trade_event,
    TradeEvent
)
from .indicators import IndicatorManager
from .audit_logger import (
    initialize_audit_logger, 
    get_audit_logger, 
    close_audit_logger,
    EventType,
    LogLevel
)
from .log_analyzer import LogAnalyzer
from .analytics import initialize_analytics, get_analytics_engine, AnalyticsPeriod
from .dashboard import dashboard_app
from .risk_analytics import RiskAnalyzer
from .execution_analytics import ExecutionAnalyzer
from .strategy_optimizer import StrategyOptimizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DayBot MCP Server",
    description="MCP tool server for algorithmic trading with Alpaca",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
risk_manager = RiskManager()
indicator_managers: Dict[str, IndicatorManager] = {}
trade_log: List[TradeEvent] = []
log_analyzer: Optional[LogAnalyzer] = None

# Mount the dashboard app
app.mount("/dashboard", dashboard_app, name="dashboard")


# Pydantic models for request/response
class ScanSymbolsRequest(BaseModel):
    """Request model for symbol scanning."""
    market_cap_min: Optional[float] = None
    volume_min: Optional[float] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    sector: Optional[str] = None


class ScanSymbolsResponse(BaseModel):
    """Response model for symbol scanning."""
    symbols: List[str]
    scan_time: str
    criteria: Dict[str, Any]


class EnterTradeRequest(BaseModel):
    """Request model for entering a trade."""
    symbol: str
    side: str = Field(..., pattern="^(buy|sell)$")
    quantity: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    order_type: str = Field(default="market", pattern="^(market|limit)$")
    time_in_force: str = Field(default="day", pattern="^(day|gtc|ioc|fok)$")
    risk_percent: Optional[float] = None


class EnterTradeResponse(BaseModel):
    """Response model for entering a trade."""
    success: bool
    order_ids: List[str]
    symbol: str
    quantity: float
    entry_price: Optional[float]
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    position_size_info: Optional[PositionSizeResult]
    message: str
    timestamp: str


class ManageTradeRequest(BaseModel):
    """Request model for managing a trade."""
    symbol: str
    action: str = Field(..., pattern="^(adjust_stop|trail_stop|partial_exit|add_to_position)$")
    new_stop_price: Optional[float] = None
    trail_amount: Optional[float] = None
    exit_quantity: Optional[float] = None
    add_quantity: Optional[float] = None


class ManageTradeResponse(BaseModel):
    """Response model for managing a trade."""
    success: bool
    symbol: str
    action: str
    message: str
    new_orders: List[str]
    cancelled_orders: List[str]
    timestamp: str


class CloseSymbolRequest(BaseModel):
    """Request model for closing a symbol."""
    symbol: str
    quantity: Optional[float] = None


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str
    account_status: str
    market_open: bool
    buying_power: float
    portfolio_value: float
    timestamp: str
    config_valid: bool


class RiskStatusResponse(BaseModel):
    """Response model for risk status."""
    portfolio_value: float
    daily_pnl: float
    daily_pnl_percent: float
    max_daily_loss_percent: float
    total_exposure: float
    positions_count: int
    risk_level: str
    portfolio_heat: Dict[str, Any]
    timestamp: str


class RecordTradeRequest(BaseModel):
    """Request model for recording a trade."""
    event_type: str
    symbol: str
    price: float
    quantity: float
    side: str
    order_id: Optional[str] = None
    pnl: Optional[float] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


# MCP Tool Endpoints

@app.post("/tools/scan_symbols", response_model=ScanSymbolsResponse)
async def scan_symbols(request: ScanSymbolsRequest):
    """
    Scan for symbols based on criteria.
    Currently returns a stubbed watchlist - extend with actual scanner later.
    """
    # Log symbol scan event
    audit_logger = get_audit_logger()
    audit_logger.log_strategy_event(
        EventType.SYMBOL_SCAN,
        f"Symbol scan requested with criteria: {request.dict()}",
        "scanner",
        metadata=request.dict()
    )
    
    # Stubbed implementation - replace with actual scanner
    watchlist = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
        "NVDA", "META", "NFLX", "AMD", "CRM",
        "SPY", "QQQ", "IWM", "ARKK", "TQQQ"
    ]
    
    # Apply basic filtering if criteria provided
    filtered_symbols = watchlist
    
    if request.price_min or request.price_max:
        # In a real implementation, you would filter by actual prices
        pass
    
    audit_logger.log_strategy_event(
        EventType.SYMBOL_SCAN,
        f"Symbol scan completed, found {len(filtered_symbols)} symbols",
        "scanner",
        metadata={"symbol_count": len(filtered_symbols), "symbols": filtered_symbols}
    )
    
    return ScanSymbolsResponse(
        symbols=filtered_symbols,
        scan_time=datetime.now(timezone.utc).isoformat(),
        criteria=request.dict()
    )


@app.post("/tools/enter_trade", response_model=EnterTradeResponse)
async def enter_trade(request: EnterTradeRequest):
    """Submit bracket orders with stop loss and take profit."""
    timestamp = datetime.now(timezone.utc).isoformat()
    audit_logger = get_audit_logger()
    
    # Log trade entry attempt
    audit_logger.log_strategy_event(
        EventType.ENTRY_SIGNAL,
        f"Trade entry requested: {request.side} {request.symbol}",
        "trading",
        symbol=request.symbol,
        metadata=request.dict()
    )
    
    try:
        async with AlpacaClient() as client:
            # Check if we can open new position
            can_open, reasons = await risk_manager.can_open_new_position(
                client, request.symbol, 0  # We'll calculate size below
            )
            
            if not can_open:
                audit_logger.log_risk_event(
                    EventType.RISK_LIMIT_HIT,
                    f"Trade entry blocked for {request.symbol}: {', '.join(reasons)}",
                    metadata={"symbol": request.symbol, "reasons": reasons}
                )
                return EnterTradeResponse(
                    success=False,
                    order_ids=[],
                    symbol=request.symbol,
                    quantity=0,
                    entry_price=None,
                    stop_loss_price=None,
                    take_profit_price=None,
                    position_size_info=None,
                    message=f"Cannot open position: {', '.join(reasons)}",
                    timestamp=timestamp
                )
            
            # Get current price if not provided
            entry_price = request.entry_price
            if entry_price is None:
                if request.order_type == "market":
                    # For market orders, we'll use a placeholder price for position sizing
                    # The actual execution price will be determined by the market
                    try:
                        latest_trade = await client.get_latest_trade(request.symbol)
                        entry_price = latest_trade.get("p", 100.0)  # Fallback price
                    except Exception:
                        # If we can't get market data, use a reasonable default for position sizing
                        entry_price = 100.0 if request.symbol in ["SPY", "QQQ"] else 150.0
                        logger.warning(f"Could not get market price for {request.symbol}, using fallback: ${entry_price}")
                else:
                    raise HTTPException(status_code=400, detail="Entry price required for limit orders")
            
            # Calculate position size if quantity not provided
            quantity = request.quantity
            position_size_info = None
            
            if quantity is None:
                account = await client.get_account()
                
                # Get ATR for dynamic stop loss
                atr_value = None
                if request.symbol in indicator_managers:
                    indicators = indicator_managers[request.symbol].get_current_values()
                    atr_value = indicators.get("atr")
                
                position_size_info = risk_manager.shares_for_trade(
                    symbol=request.symbol,
                    entry_price=entry_price,
                    stop_loss_price=request.stop_loss_price,
                    portfolio_value=account.portfolio_value,
                    risk_percent=request.risk_percent,
                    atr_value=atr_value
                )
                
                quantity = position_size_info.recommended_shares
            
            # Determine if we should use bracket order or simple order
            stop_loss_price = request.stop_loss_price or (position_size_info.stop_loss_price if position_size_info else None)
            take_profit_price = request.take_profit_price or (position_size_info.take_profit_price if position_size_info else None)
            
            if stop_loss_price and take_profit_price:
                # Submit bracket order with both stop and target
                orders = await client.submit_bracket_order(
                    symbol=request.symbol,
                    qty=quantity,
                    side=request.side,
                    limit_price=entry_price if request.order_type == "limit" else None,
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                    time_in_force=request.time_in_force
                )
            else:
                # Submit simple order
                order = await client.submit_order(
                    symbol=request.symbol,
                    qty=quantity,
                    side=request.side,
                    order_type=request.order_type,
                    limit_price=entry_price if request.order_type == "limit" else None,
                    time_in_force=request.time_in_force
                )
                orders = [order]
            
            order_ids = [order.id for order in orders]
            
            # Log successful trade entry
            audit_logger.log_trade_entry(
                symbol=request.symbol,
                side=request.side,
                quantity=quantity,
                price=entry_price,
                order_id=order_ids[0] if order_ids else None,
                strategy_name="manual",
                risk_percent=request.risk_percent or 0.01,
                metadata={
                    "order_type": request.order_type,
                    "stop_loss_price": stop_loss_price,
                    "take_profit_price": take_profit_price,
                    "position_size_info": position_size_info.dict() if position_size_info else None
                }
            )
            
            # Record trade event (legacy)
            trade_event = create_trade_event(
                event_type="entry",
                symbol=request.symbol,
                price=entry_price,
                quantity=quantity,
                side=request.side,
                order_id=order_ids[0] if order_ids else None,
                reason="bracket_order"
            )
            trade_log.append(trade_event)
            
            # Update trade counter
            risk_manager.update_trade_count()
            
            return EnterTradeResponse(
                success=True,
                order_ids=order_ids,
                symbol=request.symbol,
                quantity=quantity,
                entry_price=entry_price,
                stop_loss_price=request.stop_loss_price or (position_size_info.stop_loss_price if position_size_info else None),
                take_profit_price=request.take_profit_price or (position_size_info.take_profit_price if position_size_info else None),
                position_size_info=position_size_info,
                message=f"Successfully submitted bracket order for {quantity} shares of {request.symbol}",
                timestamp=timestamp
            )
    
    except Exception as e:
        logger.error(f"Error entering trade: {str(e)}")
        audit_logger.log_error(
            f"Trade entry failed for {request.symbol}: {str(e)}",
            "trading",
            error=e,
            metadata={"symbol": request.symbol, "request": request.dict()}
        )
        return EnterTradeResponse(
            success=False,
            order_ids=[],
            symbol=request.symbol,
            quantity=0,
            entry_price=None,
            stop_loss_price=None,
            take_profit_price=None,
            position_size_info=None,
            message=f"Error: {str(e)}",
            timestamp=timestamp
        )


@app.post("/tools/manage_trade", response_model=ManageTradeResponse)
async def manage_trade(request: ManageTradeRequest):
    """Adjust stop loss, trail stop, or exit partial position."""
    timestamp = datetime.now(timezone.utc).isoformat()
    
    try:
        async with AlpacaClient() as client:
            new_orders = []
            cancelled_orders = []
            
            if request.action == "adjust_stop":
                # Cancel existing stop orders and create new one
                orders = await client.get_orders(status="open")
                symbol_orders = [o for o in orders if o.symbol == request.symbol and o.order_type == "stop"]
                
                for order in symbol_orders:
                    if await client.cancel_order(order.id):
                        cancelled_orders.append(order.id)
                
                # Create new stop order
                position = await client.get_position(request.symbol)
                if position:
                    side = "sell" if float(position.qty) > 0 else "buy"
                    new_order = await client.submit_order(
                        symbol=request.symbol,
                        qty=abs(float(position.qty)),
                        side=side,
                        order_type="stop",
                        stop_price=request.new_stop_price
                    )
                    new_orders.append(new_order.id)
            
            elif request.action == "trail_stop":
                # Implement trailing stop logic
                orders = await client.get_orders(status="open")
                symbol_orders = [o for o in orders if o.symbol == request.symbol and "stop" in o.order_type]
                
                for order in symbol_orders:
                    if await client.cancel_order(order.id):
                        cancelled_orders.append(order.id)
                
                position = await client.get_position(request.symbol)
                if position:
                    side = "sell" if float(position.qty) > 0 else "buy"
                    new_order = await client.submit_order(
                        symbol=request.symbol,
                        qty=abs(float(position.qty)),
                        side=side,
                        order_type="trailing_stop",
                        trail_price=request.trail_amount
                    )
                    new_orders.append(new_order.id)
            
            elif request.action == "partial_exit":
                # Exit partial position
                position = await client.get_position(request.symbol)
                if position:
                    exit_qty = request.exit_quantity or abs(float(position.qty)) * 0.5
                    side = "sell" if float(position.qty) > 0 else "buy"
                    
                    new_order = await client.submit_order(
                        symbol=request.symbol,
                        qty=exit_qty,
                        side=side,
                        order_type="market"
                    )
                    new_orders.append(new_order.id)
                    
                    # Record trade event
                    latest_trade = await client.get_latest_trade(request.symbol)
                    trade_event = create_trade_event(
                        event_type="partial_exit",
                        symbol=request.symbol,
                        price=latest_trade.get("p", 0),
                        quantity=exit_qty,
                        side=side,
                        order_id=new_order.id,
                        reason="manual_partial_exit"
                    )
                    trade_log.append(trade_event)
            
            return ManageTradeResponse(
                success=True,
                symbol=request.symbol,
                action=request.action,
                message=f"Successfully executed {request.action} for {request.symbol}",
                new_orders=new_orders,
                cancelled_orders=cancelled_orders,
                timestamp=timestamp
            )
    
    except Exception as e:
        logger.error(f"Error managing trade: {str(e)}")
        return ManageTradeResponse(
            success=False,
            symbol=request.symbol,
            action=request.action,
            message=f"Error: {str(e)}",
            new_orders=[],
            cancelled_orders=[],
            timestamp=timestamp
        )


@app.post("/tools/close_symbol")
async def close_symbol(request: CloseSymbolRequest):
    """Idempotent close with verification."""
    audit_logger = get_audit_logger()
    try:
        async with AlpacaClient() as client:
            result = await close_with_verification(
                client, 
                request.symbol, 
                request.quantity
            )
            
            # Record trade event if successful
            if result.success and result.close_price:
                audit_logger.log_trade_exit(
                    symbol=request.symbol,
                    quantity=result.closed_qty,
                    price=result.close_price,
                    pnl=0.0,  # P&L would need to be calculated
                    order_id="manual_close",
                    reason="manual_close",
                    metadata={
                        "initial_qty": result.initial_qty,
                        "remaining_qty": result.remaining_qty,
                        "verification_attempts": result.verification_attempts
                    }
                )
                
                trade_event = create_trade_event(
                    event_type="exit",
                    symbol=request.symbol,
                    price=result.close_price,
                    quantity=result.closed_qty,
                    side="sell" if result.initial_qty > 0 else "buy",
                    reason="manual_close"
                )
                trade_log.append(trade_event)
            
            return result.dict()

    except Exception as e:
        logger.error(f"Error closing symbol: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/flat_all")
async def flat_all():
    """Flatten all positions and cancel open orders."""
    try:
        async with AlpacaClient() as client:
            result = await flatten_all_positions(client)
            
            # Record trade events for each closed position
            if result.get("success"):
                for close_result in result.get("close_results", []):
                    if close_result.get("success") and close_result.get("close_price"):
                        trade_event = create_trade_event(
                            event_type="exit",
                            symbol=close_result["symbol"],
                            price=close_result["close_price"],
                            quantity=close_result["closed_qty"],
                            side="sell" if close_result["initial_qty"] > 0 else "buy",
                            reason="flatten_all"
                        )
                        trade_log.append(trade_event)
            
            return result
    
    except Exception as e:
        logger.error(f"Error flattening all positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/healthcheck", response_model=HealthCheckResponse)
async def healthcheck():
    """Check account, clock, and connectivity."""
    try:
        async with AlpacaClient() as client:
            health_data = await client.health_check()
            
            # Log health check
            audit_logger = get_audit_logger()
            audit_logger.log_system_event(
                EventType.HEALTH_CHECK,
                f"Health check completed: {health_data['status']}",
                metadata=health_data
            )
            
            return HealthCheckResponse(
                status=health_data["status"],
                account_status=health_data.get("account_status", "unknown"),
                market_open=health_data.get("market_open", False),
                buying_power=health_data.get("buying_power", 0),
                portfolio_value=health_data.get("portfolio_value", 0),
                timestamp=health_data["timestamp"],
                config_valid=validate_config()
            )
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        audit_logger = get_audit_logger()
        audit_logger.log_error(
            f"Health check failed: {str(e)}",
            "system",
            error=e
        )
        return HealthCheckResponse(
            status="unhealthy",
            account_status="error",
            market_open=False,
            buying_power=0,
            portfolio_value=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            config_valid=False
        )


@app.get("/tools/risk_status", response_model=RiskStatusResponse)
async def risk_status():
    """Return P&L and drawdown counters."""
    try:
        async with AlpacaClient() as client:
            risk_metrics = await risk_manager.get_risk_metrics(client)
            portfolio_heat = await risk_manager.get_portfolio_heat(client)
            
            return RiskStatusResponse(
                portfolio_value=risk_metrics.portfolio_value,
                daily_pnl=risk_metrics.daily_pnl,
                daily_pnl_percent=risk_metrics.daily_pnl_percent,
                max_daily_loss_percent=settings.max_daily_loss * 100,
                total_exposure=risk_metrics.total_exposure,
                positions_count=risk_metrics.positions_count,
                risk_level=risk_metrics.risk_level,
                portfolio_heat=portfolio_heat,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    except Exception as e:
        logger.error(f"Error getting risk status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/record_trade")
async def record_trade(request: RecordTradeRequest):
    """Log structured trade events."""
    try:
        trade_event = create_trade_event(
            event_type=request.event_type,
            symbol=request.symbol,
            price=request.price,
            quantity=request.quantity,
            side=request.side,
            order_id=request.order_id,
            pnl=request.pnl,
            reason=request.reason,
            **request.metadata
        )
        
        trade_log.append(trade_event)
        
        return {
            "success": True,
            "message": f"Recorded {request.event_type} event for {request.symbol}",
            "event_id": len(trade_log) - 1,
            "timestamp": trade_event.timestamp
        }
    
    except Exception as e:
        logger.error(f"Error recording trade: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Additional utility endpoints

@app.get("/trade_log")
async def get_trade_log(limit: int = 100):
    """Get recent trade events."""
    return {
        "events": trade_log[-limit:],
        "total_events": len(trade_log)
    }


# Audit logging and analysis endpoints

@app.get("/audit/daily_report")
async def get_daily_report(date: Optional[str] = None):
    """Get comprehensive daily trading report."""
    try:
        if not log_analyzer:
            raise HTTPException(status_code=503, detail="Log analyzer not initialized")
        
        target_date = None
        if date:
            try:
                target_date = datetime.fromisoformat(date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        report = log_analyzer.generate_daily_report(target_date)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/trading_metrics")
async def get_trading_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get trading performance metrics for a date range."""
    try:
        if not log_analyzer:
            raise HTTPException(status_code=503, detail="Log analyzer not initialized")
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        metrics = log_analyzer.get_trading_metrics(start_dt, end_dt)
        return metrics.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/system_metrics")
async def get_system_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get system performance metrics for a date range."""
    try:
        if not log_analyzer:
            raise HTTPException(status_code=503, detail="Log analyzer not initialized")
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        metrics = log_analyzer.get_system_metrics(start_dt, end_dt)
        return metrics.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/risk_metrics")
async def get_risk_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get risk management metrics for a date range."""
    try:
        if not log_analyzer:
            raise HTTPException(status_code=503, detail="Log analyzer not initialized")
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        metrics = log_analyzer.get_risk_metrics(start_dt, end_dt)
        return metrics.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/symbol_performance")
async def get_symbol_performance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get performance metrics by symbol."""
    try:
        if not log_analyzer:
            raise HTTPException(status_code=503, detail="Log analyzer not initialized")
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        performance = log_analyzer.get_symbol_performance(start_dt, end_dt)
        return performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/error_summary")
async def get_error_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get error and issue summary."""
    try:
        if not log_analyzer:
            raise HTTPException(status_code=503, detail="Log analyzer not initialized")
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        summary = log_analyzer.get_error_summary(start_dt, end_dt)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/export_logs")
async def export_logs_csv(
    output_file: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_types: Optional[List[str]] = None
):
    """Export logs to CSV format."""
    try:
        if not log_analyzer:
            raise HTTPException(status_code=503, detail="Log analyzer not initialized")
        
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        # Convert string event types to EventType enums
        event_type_enums = None
        if event_types:
            try:
                event_type_enums = [EventType(et) for et in event_types]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")
        
        log_analyzer.export_logs_to_csv(output_file, start_dt, end_dt, event_type_enums)
        
        return {
            "success": True,
            "message": f"Logs exported to {output_file}",
            "export_params": {
                "start_date": start_date,
                "end_date": end_date,
                "event_types": event_types
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions")
async def get_positions():
    """Get current positions."""
    try:
        async with AlpacaClient() as client:
            positions = await client.get_positions()
            return [pos.dict() for pos in positions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders")
async def get_orders(status: str = "open"):
    """Get orders by status."""
    try:
        async with AlpacaClient() as client:
            orders = await client.get_orders(status=status)
            return [order.dict() for order in orders]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/account")
async def get_account():
    """Get account information."""
    try:
        async with AlpacaClient() as client:
            account = await client.get_account()
            return account.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Analytics Endpoints

@app.get("/analytics/performance")
async def get_performance_analytics(
    period: AnalyticsPeriod = AnalyticsPeriod.ALL_TIME,
    strategy: Optional[str] = None,
    symbol: Optional[str] = None
):
    """Get comprehensive performance analytics."""
    try:
        analyzer = get_analytics_engine()
        
        # Calculate date range based on period
        end_date = datetime.now(timezone.utc)
        start_date = None
        
        if period != AnalyticsPeriod.ALL_TIME:
            from datetime import timedelta
            period_map = {
                AnalyticsPeriod.DAILY: timedelta(days=1),
                AnalyticsPeriod.WEEKLY: timedelta(weeks=1),
                AnalyticsPeriod.MONTHLY: timedelta(days=30),
                AnalyticsPeriod.QUARTERLY: timedelta(days=90),
                AnalyticsPeriod.YEARLY: timedelta(days=365)
            }
            start_date = end_date - period_map[period]
        
        # Get trades
        trades = analyzer.get_trades(
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            symbol=symbol
        )
        
        # Calculate metrics
        metrics = analyzer.calculate_performance_metrics(trades)
        
        return {
            "period": period.value,
            "filters": {"strategy": strategy, "symbol": symbol},
            "metrics": {
                "total_trades": metrics.total_trades,
                "win_rate": metrics.win_rate,
                "profit_factor": metrics.profit_factor,
                "expectancy": metrics.expectancy,
                "net_profit": metrics.net_profit,
                "max_drawdown": metrics.max_drawdown_percent,
                "sharpe_ratio": metrics.sharpe_ratio,
                "avg_win": metrics.avg_win,
                "avg_loss": metrics.avg_loss,
                "kelly_criterion": metrics.kelly_criterion
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/risk")
async def get_risk_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get comprehensive risk analytics."""
    try:
        analyzer = get_analytics_engine()
        risk_analyzer = RiskAnalyzer(analyzer)
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Get trades
        trades = analyzer.get_trades(start_date=start_dt, end_date=end_dt)
        
        # Generate risk report
        risk_report = risk_analyzer.generate_risk_report(trades)
        
        return risk_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/execution")
async def get_execution_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get execution quality analytics."""
    try:
        analyzer = get_analytics_engine()
        execution_analyzer = ExecutionAnalyzer(analyzer)
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Get trades
        trades = analyzer.get_trades(start_date=start_dt, end_date=end_dt)
        
        # Generate execution report
        execution_report = execution_analyzer.generate_execution_report(trades)
        
        return execution_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/optimization")
async def get_optimization_recommendations(
    strategy: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get strategy optimization recommendations."""
    try:
        analyzer = get_analytics_engine()
        optimizer = StrategyOptimizer(analyzer)
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Get trades
        trades = analyzer.get_trades(
            start_date=start_dt,
            end_date=end_dt,
            strategy=strategy
        )
        
        # Generate optimization report
        optimization_report = optimizer.generate_optimization_report(trades)
        
        return optimization_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/strategy/{strategy_name}")
async def analyze_strategy(
    strategy_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Analyze specific strategy performance."""
    try:
        analyzer = get_analytics_engine()
        optimizer = StrategyOptimizer(analyzer)
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Get trades for strategy
        trades = analyzer.get_trades(
            start_date=start_dt,
            end_date=end_dt,
            strategy=strategy_name
        )
        
        # Analyze strategy
        strategy_analysis = optimizer.analyze_strategy_performance(trades, strategy_name)
        
        return {
            "strategy_analysis": {
                "name": strategy_analysis.strategy_name,
                "total_trades": strategy_analysis.total_trades,
                "performance_score": strategy_analysis.performance_score,
                "optimization_potential": strategy_analysis.optimization_potential,
                "metrics": {
                    "win_rate": strategy_analysis.win_rate,
                    "profit_factor": strategy_analysis.profit_factor,
                    "expectancy": strategy_analysis.expectancy,
                    "max_drawdown": strategy_analysis.max_drawdown,
                    "sharpe_ratio": strategy_analysis.sharpe_ratio
                },
                "strengths": strategy_analysis.strengths,
                "weaknesses": strategy_analysis.weaknesses,
                "top_symbols": strategy_analysis.best_performing_symbols,
                "worst_symbols": strategy_analysis.worst_performing_symbols
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics/sync")
async def sync_analytics_data():
    """Sync trade data from log files to analytics database."""
    try:
        analyzer = get_analytics_engine()
        trades_added = analyzer.parse_log_files()
        
        return {
            "success": True,
            "trades_synced": trades_added,
            "message": f"Successfully synced {trades_added} trades from log files"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/trades")
async def get_trades_data(
    limit: int = 100,
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get trades data with filtering."""
    try:
        analyzer = get_analytics_engine()
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Get trades
        trades = analyzer.get_trades(
            start_date=start_dt,
            end_date=end_dt,
            symbol=symbol,
            strategy=strategy,
            limit=limit
        )
        
        # Format trades for response
        trades_data = []
        for trade in trades:
            trades_data.append({
                "symbol": trade.symbol,
                "strategy": trade.strategy,
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat(),
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "quantity": trade.quantity,
                "side": trade.side,
                "pnl": trade.pnl,
                "pnl_percent": trade.pnl_percent,
                "duration_minutes": trade.duration_minutes,
                "outcome": trade.outcome.value,
                "exit_reason": trade.exit_reason
            })
        
        return {
            "trades": trades_data,
            "total_count": len(trades_data),
            "filters": {
                "symbol": symbol,
                "strategy": strategy,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Background tasks

@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    global log_analyzer
    
    logger.info("Starting DayBot MCP Server")
    
    # Initialize audit logging
    initialize_audit_logger(
        log_dir="logs",
        environment=getattr(settings, 'environment', 'development')
    )
    
    # Initialize log analyzer
    log_analyzer = LogAnalyzer("logs")
    
    # Initialize analytics engine
    initialize_analytics("logs")
    
    # Validate configuration
    if not validate_config():
        logger.error("Invalid configuration - check environment variables")
        get_audit_logger().log_system_event(
            EventType.SYSTEM_ERROR,
            "Invalid configuration detected",
            LogLevel.ERROR
        )
    
    # Reset daily counters
    risk_manager.reset_daily_counters()
    
    get_audit_logger().log_system_event(
        EventType.SYSTEM_START,
        f"DayBot MCP Server started on {settings.server_host}:{settings.server_port}",
        metadata={
            "host": settings.server_host,
            "port": settings.server_port,
            "config_valid": validate_config()
        }
    )
    
    logger.info(f"Server started on {settings.server_host}:{settings.server_port}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down DayBot MCP Server")
    
    # Close audit logger
    try:
        get_audit_logger().log_system_event(
            EventType.SYSTEM_STOP,
            "DayBot MCP Server shutting down"
        )
        close_audit_logger()
    except Exception as e:
        logger.error(f"Error closing audit logger: {e}")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "DayBot MCP Server",
        "version": "1.0.0",
        "description": "MCP tool server for algorithmic trading with Alpaca",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": [
            "/tools/scan_symbols",
            "/tools/enter_trade", 
            "/tools/manage_trade",
            "/tools/close_symbol",
            "/tools/flat_all",
            "/tools/healthcheck",
            "/tools/risk_status",
            "/tools/record_trade",
            "/analytics/performance",
            "/analytics/risk",
            "/analytics/execution",
            "/analytics/optimization",
            "/analytics/trades",
            "/dashboard/"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "daybot_mcp.server:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug_mode
    )
