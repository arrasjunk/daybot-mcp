"""
Technical indicators for trading analysis.
Includes VWAP, EMA, ATR, and other common indicators.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class VWAP:
    """Volume Weighted Average Price indicator."""
    
    def __init__(self):
        self.prices = []
        self.volumes = []
        self.cumulative_pv = 0.0
        self.cumulative_volume = 0.0
    
    def add_data(self, price: float, volume: float) -> float:
        """Add new price/volume data and return current VWAP."""
        self.prices.append(price)
        self.volumes.append(volume)
        
        pv = price * volume
        self.cumulative_pv += pv
        self.cumulative_volume += volume
        
        if self.cumulative_volume == 0:
            return price
        
        return self.cumulative_pv / self.cumulative_volume
    
    def calculate_from_bars(self, bars: List[Dict[str, Any]]) -> List[float]:
        """Calculate VWAP from a list of OHLCV bars."""
        vwap_values = []
        cumulative_pv = 0.0
        cumulative_volume = 0.0
        
        for bar in bars:
            # Use typical price (HLC/3) for VWAP calculation
            typical_price = (bar['h'] + bar['l'] + bar['c']) / 3
            volume = bar['v']
            
            pv = typical_price * volume
            cumulative_pv += pv
            cumulative_volume += volume
            
            if cumulative_volume > 0:
                vwap = cumulative_pv / cumulative_volume
            else:
                vwap = typical_price
            
            vwap_values.append(vwap)
        
        return vwap_values
    
    def reset(self):
        """Reset the VWAP calculation (typically done at market open)."""
        self.prices.clear()
        self.volumes.clear()
        self.cumulative_pv = 0.0
        self.cumulative_volume = 0.0


class EMA:
    """Exponential Moving Average indicator."""
    
    def __init__(self, period: int):
        self.period = period
        self.alpha = 2.0 / (period + 1)
        self.ema_value: Optional[float] = None
        self.initialized = False
    
    def add_data(self, price: float) -> float:
        """Add new price data and return current EMA."""
        if not self.initialized:
            self.ema_value = price
            self.initialized = True
        else:
            self.ema_value = (price * self.alpha) + (self.ema_value * (1 - self.alpha))
        
        return self.ema_value
    
    def calculate_from_prices(self, prices: List[float]) -> List[float]:
        """Calculate EMA from a list of prices."""
        if not prices:
            return []
        
        ema_values = []
        ema = prices[0]  # Initialize with first price
        ema_values.append(ema)
        
        for price in prices[1:]:
            ema = (price * self.alpha) + (ema * (1 - self.alpha))
            ema_values.append(ema)
        
        return ema_values
    
    def get_value(self) -> Optional[float]:
        """Get current EMA value."""
        return self.ema_value
    
    def reset(self):
        """Reset the EMA calculation."""
        self.ema_value = None
        self.initialized = False


class ATR:
    """Average True Range indicator."""
    
    def __init__(self, period: int = 14):
        self.period = period
        self.true_ranges = []
        self.atr_value: Optional[float] = None
        self.previous_close: Optional[float] = None
    
    def add_data(self, high: float, low: float, close: float) -> float:
        """Add new OHLC data and return current ATR."""
        if self.previous_close is not None:
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - self.previous_close)
            tr3 = abs(low - self.previous_close)
            true_range = max(tr1, tr2, tr3)
        else:
            # First bar, use high - low
            true_range = high - low
        
        self.true_ranges.append(true_range)
        
        # Keep only the last 'period' values
        if len(self.true_ranges) > self.period:
            self.true_ranges.pop(0)
        
        # Calculate ATR (simple moving average of true ranges)
        self.atr_value = sum(self.true_ranges) / len(self.true_ranges)
        self.previous_close = close
        
        return self.atr_value
    
    def calculate_from_bars(self, bars: List[Dict[str, Any]]) -> List[float]:
        """Calculate ATR from a list of OHLC bars."""
        if len(bars) < 2:
            return [bars[0]['h'] - bars[0]['l']] if bars else []
        
        atr_values = []
        true_ranges = []
        
        for i, bar in enumerate(bars):
            high, low, close = bar['h'], bar['l'], bar['c']
            
            if i == 0:
                # First bar
                true_range = high - low
            else:
                prev_close = bars[i-1]['c']
                tr1 = high - low
                tr2 = abs(high - prev_close)
                tr3 = abs(low - prev_close)
                true_range = max(tr1, tr2, tr3)
            
            true_ranges.append(true_range)
            
            # Keep only the last 'period' values
            if len(true_ranges) > self.period:
                true_ranges.pop(0)
            
            # Calculate ATR
            atr = sum(true_ranges) / len(true_ranges)
            atr_values.append(atr)
        
        return atr_values
    
    def get_value(self) -> Optional[float]:
        """Get current ATR value."""
        return self.atr_value
    
    def reset(self):
        """Reset the ATR calculation."""
        self.true_ranges.clear()
        self.atr_value = None
        self.previous_close = None


class RSI:
    """Relative Strength Index indicator."""
    
    def __init__(self, period: int = 14):
        self.period = period
        self.prices = []
        self.gains = []
        self.losses = []
        self.rsi_value: Optional[float] = None
    
    def add_data(self, price: float) -> Optional[float]:
        """Add new price data and return current RSI."""
        self.prices.append(price)
        
        if len(self.prices) < 2:
            return None
        
        # Calculate price change
        change = price - self.prices[-2]
        
        if change > 0:
            self.gains.append(change)
            self.losses.append(0)
        else:
            self.gains.append(0)
            self.losses.append(abs(change))
        
        # Keep only the last 'period' values
        if len(self.gains) > self.period:
            self.gains.pop(0)
            self.losses.pop(0)
        
        if len(self.gains) < self.period:
            return None
        
        # Calculate RSI
        avg_gain = sum(self.gains) / self.period
        avg_loss = sum(self.losses) / self.period
        
        if avg_loss == 0:
            self.rsi_value = 100
        else:
            rs = avg_gain / avg_loss
            self.rsi_value = 100 - (100 / (1 + rs))
        
        return self.rsi_value
    
    def get_value(self) -> Optional[float]:
        """Get current RSI value."""
        return self.rsi_value


class BollingerBands:
    """Bollinger Bands indicator."""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
        self.prices = []
        self.upper_band: Optional[float] = None
        self.middle_band: Optional[float] = None  # SMA
        self.lower_band: Optional[float] = None
    
    def add_data(self, price: float) -> Dict[str, Optional[float]]:
        """Add new price data and return current Bollinger Bands."""
        self.prices.append(price)
        
        # Keep only the last 'period' values
        if len(self.prices) > self.period:
            self.prices.pop(0)
        
        if len(self.prices) < self.period:
            return {
                "upper": None,
                "middle": None,
                "lower": None
            }
        
        # Calculate SMA (middle band)
        self.middle_band = sum(self.prices) / self.period
        
        # Calculate standard deviation
        variance = sum((p - self.middle_band) ** 2 for p in self.prices) / self.period
        std = variance ** 0.5
        
        # Calculate bands
        self.upper_band = self.middle_band + (self.std_dev * std)
        self.lower_band = self.middle_band - (self.std_dev * std)
        
        return {
            "upper": self.upper_band,
            "middle": self.middle_band,
            "lower": self.lower_band
        }
    
    def get_values(self) -> Dict[str, Optional[float]]:
        """Get current Bollinger Bands values."""
        return {
            "upper": self.upper_band,
            "middle": self.middle_band,
            "lower": self.lower_band
        }


class IndicatorManager:
    """Manages multiple indicators for a symbol."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.vwap = VWAP()
        self.ema_9 = EMA(9)
        self.ema_21 = EMA(21)
        self.ema_50 = EMA(50)
        self.atr = ATR(14)
        self.rsi = RSI(14)
        self.bb = BollingerBands(20, 2.0)
        
        self.last_update: Optional[datetime] = None
    
    def update(self, bar: Dict[str, Any]) -> Dict[str, Any]:
        """Update all indicators with new bar data."""
        high, low, close, volume = bar['h'], bar['l'], bar['c'], bar['v']
        
        # Update indicators
        vwap_val = self.vwap.add_data(close, volume)
        ema9_val = self.ema_9.add_data(close)
        ema21_val = self.ema_21.add_data(close)
        ema50_val = self.ema_50.add_data(close)
        atr_val = self.atr.add_data(high, low, close)
        rsi_val = self.rsi.add_data(close)
        bb_vals = self.bb.add_data(close)
        
        self.last_update = datetime.now()
        
        return {
            "symbol": self.symbol,
            "timestamp": self.last_update.isoformat(),
            "price": close,
            "vwap": vwap_val,
            "ema_9": ema9_val,
            "ema_21": ema21_val,
            "ema_50": ema50_val,
            "atr": atr_val,
            "rsi": rsi_val,
            "bb_upper": bb_vals["upper"],
            "bb_middle": bb_vals["middle"],
            "bb_lower": bb_vals["lower"]
        }
    
    def reset_daily_indicators(self):
        """Reset indicators that should reset daily (like VWAP)."""
        self.vwap.reset()
    
    def get_current_values(self) -> Dict[str, Any]:
        """Get current values of all indicators."""
        return {
            "symbol": self.symbol,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "vwap": self.vwap.cumulative_pv / self.vwap.cumulative_volume if self.vwap.cumulative_volume > 0 else None,
            "ema_9": self.ema_9.get_value(),
            "ema_21": self.ema_21.get_value(),
            "ema_50": self.ema_50.get_value(),
            "atr": self.atr.get_value(),
            "rsi": self.rsi.get_value(),
            "bollinger_bands": self.bb.get_values()
        }
