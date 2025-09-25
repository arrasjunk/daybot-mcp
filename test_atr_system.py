#!/usr/bin/env python3
"""
Test script to demonstrate the ATR-based dynamic stop/target system.
Shows the difference between fixed percentage and ATR-based approaches.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from daybot_mcp.risk import RiskManager
from daybot_mcp.indicators import ATR
import random

def simulate_price_data(base_price: float, volatility: float, periods: int = 20):
    """Generate simulated OHLC data with specified volatility."""
    data = []
    current_price = base_price
    
    for _ in range(periods):
        # Generate random price movement
        change_pct = random.gauss(0, volatility)
        new_price = current_price * (1 + change_pct)
        
        # Generate OHLC
        high = new_price * (1 + abs(random.gauss(0, volatility/2)))
        low = new_price * (1 - abs(random.gauss(0, volatility/2)))
        close = new_price
        
        data.append({
            'h': high,
            'l': low,
            'c': close,
            'o': current_price
        })
        
        current_price = close
    
    return data

def test_atr_vs_fixed_stops():
    """Compare ATR-based vs fixed percentage stops for different volatility scenarios."""
    
    print("🧪 Testing ATR-Based vs Fixed Percentage Stops\n")
    print("=" * 80)
    
    risk_manager = RiskManager()
    portfolio_value = 100000  # $100k portfolio
    
    # Test scenarios with different volatility levels
    scenarios = [
        {"name": "Low Volatility Stock (KO)", "base_price": 60.0, "volatility": 0.01},
        {"name": "Medium Volatility Stock (AAPL)", "base_price": 180.0, "volatility": 0.025},
        {"name": "High Volatility Stock (TSLA)", "base_price": 250.0, "volatility": 0.05}
    ]
    
    for scenario in scenarios:
        print(f"\n📊 {scenario['name']}")
        print("-" * 50)
        
        # Generate price data and calculate ATR
        price_data = simulate_price_data(scenario['base_price'], scenario['volatility'])
        atr_indicator = ATR(14)
        atr_values = atr_indicator.calculate_from_bars(price_data)
        current_atr = atr_values[-1]
        current_price = price_data[-1]['c']
        
        print(f"Current Price: ${current_price:.2f}")
        print(f"ATR (14): ${current_atr:.2f}")
        print(f"ATR as % of price: {(current_atr/current_price)*100:.2f}%")
        
        # Test fixed percentage approach (2% stop, 4% target)
        fixed_result = risk_manager.shares_for_trade(
            symbol="TEST",
            entry_price=current_price,
            portfolio_value=portfolio_value,
            risk_percent=0.02,
            use_atr_dynamic=False
        )
        
        # Test ATR-based approach (1.5 ATR stop, 3 ATR target)
        atr_result = risk_manager.shares_for_trade(
            symbol="TEST",
            entry_price=current_price,
            portfolio_value=portfolio_value,
            risk_percent=0.02,
            atr_value=current_atr,
            atr_stop_multiplier=1.5,
            atr_target_multiplier=3.0,
            use_atr_dynamic=True
        )
        
        print(f"\n🔴 Fixed 2% Stop Approach:")
        print(f"  Stop Loss: ${fixed_result.stop_loss_price:.2f} ({((current_price - fixed_result.stop_loss_price)/current_price)*100:.1f}%)")
        print(f"  Take Profit: ${fixed_result.take_profit_price:.2f} ({((fixed_result.take_profit_price - current_price)/current_price)*100:.1f}%)")
        print(f"  Position Size: {fixed_result.recommended_shares} shares (${fixed_result.dollar_amount:.0f})")
        print(f"  Risk Amount: ${fixed_result.risk_amount:.2f}")
        print(f"  Risk/Reward: {fixed_result.risk_reward_ratio:.2f}:1")
        
        print(f"\n🟢 ATR-Based Dynamic Approach:")
        print(f"  Stop Loss: ${atr_result.stop_loss_price:.2f} ({((current_price - atr_result.stop_loss_price)/current_price)*100:.1f}%)")
        print(f"  Take Profit: ${atr_result.take_profit_price:.2f} ({((atr_result.take_profit_price - current_price)/current_price)*100:.1f}%)")
        print(f"  Position Size: {atr_result.recommended_shares} shares (${atr_result.dollar_amount:.0f})")
        print(f"  Risk Amount: ${atr_result.risk_amount:.2f}")
        print(f"  Risk/Reward: {atr_result.risk_reward_ratio:.2f}:1")
        
        # Analysis
        stop_diff = abs(fixed_result.stop_loss_price - atr_result.stop_loss_price)
        target_diff = abs(fixed_result.take_profit_price - atr_result.take_profit_price)
        
        print(f"\n📈 Analysis:")
        print(f"  Stop difference: ${stop_diff:.2f}")
        print(f"  Target difference: ${target_diff:.2f}")
        
        if atr_result.warnings:
            print(f"  ATR Warnings: {', '.join(atr_result.warnings)}")

def test_volatility_regime_detection():
    """Test volatility regime detection and adaptive ATR multipliers."""
    
    print("\n\n🌡️  Testing Volatility Regime Detection\n")
    print("=" * 80)
    
    risk_manager = RiskManager()
    
    # Test different ATR scenarios
    test_cases = [
        {"current_atr": 2.0, "atr_sma": 2.5, "expected": "low"},
        {"current_atr": 3.0, "atr_sma": 3.0, "expected": "normal"},
        {"current_atr": 4.0, "atr_sma": 3.0, "expected": "high"},
    ]
    
    for case in test_cases:
        regime = risk_manager.detect_volatility_regime(case["current_atr"], case["atr_sma"])
        print(f"ATR: {case['current_atr']:.1f}, ATR SMA: {case['atr_sma']:.1f} → {regime.upper()} volatility")
        
        # Show how this affects position sizing
        result = risk_manager.calculate_atr_position_size(
            symbol="TEST",
            entry_price=100.0,
            atr_value=case["current_atr"],
            portfolio_value=100000,
            risk_percent=0.02,
            volatility_regime=regime
        )
        
        print(f"  → Stop: ${result.stop_loss_price:.2f}, Target: ${result.take_profit_price:.2f}")
        print()

def main():
    """Run all tests."""
    print("🚀 ATR-Based Dynamic Stop/Target System Test")
    print("This demonstrates why ATR-based stops are superior to fixed percentages\n")
    
    test_atr_vs_fixed_stops()
    test_volatility_regime_detection()
    
    print("\n" + "=" * 80)
    print("✅ Key Benefits of ATR-Based Approach:")
    print("   • Adapts to instrument volatility automatically")
    print("   • Provides consistent risk across different stocks")
    print("   • Adjusts to changing market conditions")
    print("   • Reduces false stops in volatile markets")
    print("   • Optimizes risk/reward ratios based on price action")
    print("\n💡 Your suggestion to use 1.5 ATR stops and 3 ATR targets is excellent!")
    print("   This provides a professional, adaptive approach to risk management.")

if __name__ == "__main__":
    main()
