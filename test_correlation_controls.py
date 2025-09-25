#!/usr/bin/env python3
"""
Test script for correlation and concentration controls.
Demonstrates how the system prevents over-concentration in correlated assets.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from daybot_mcp.correlation_controls import CorrelationManager, CorrelationLimits, Sector
from daybot_mcp.risk import RiskManager

def create_test_portfolio(scenario: str):
    """Create different portfolio scenarios for testing."""
    
    if scenario == "tech_heavy":
        # Over-concentrated in tech stocks
        return [
            {'symbol': 'AAPL', 'market_value': 25000},
            {'symbol': 'MSFT', 'market_value': 20000},
            {'symbol': 'GOOGL', 'market_value': 18000},
            {'symbol': 'NVDA', 'market_value': 15000},
            {'symbol': 'TSLA', 'market_value': 12000},
        ]
    
    elif scenario == "high_beta":
        # Too many high-beta positions
        return [
            {'symbol': 'TSLA', 'market_value': 20000},
            {'symbol': 'NVDA', 'market_value': 18000},
            {'symbol': 'AMD', 'market_value': 15000},
            {'symbol': 'META', 'market_value': 12000},
        ]
    
    elif scenario == "financial_heavy":
        # Over-concentrated in financials
        return [
            {'symbol': 'JPM', 'market_value': 20000},
            {'symbol': 'BAC', 'market_value': 18000},
            {'symbol': 'GS', 'market_value': 15000},
        ]
    
    elif scenario == "diversified":
        # Well-diversified portfolio
        return [
            {'symbol': 'AAPL', 'market_value': 15000},  # Tech
            {'symbol': 'JPM', 'market_value': 15000},   # Financial
            {'symbol': 'JNJ', 'market_value': 15000},   # Healthcare
            {'symbol': 'KO', 'market_value': 10000},    # Consumer Staples
            {'symbol': 'XOM', 'market_value': 10000},   # Energy
        ]
    
    else:
        return []

def test_sector_concentration():
    """Test sector concentration limits."""
    print("🏭 Testing Sector Concentration Controls")
    print("=" * 60)
    
    correlation_manager = CorrelationManager()
    
    # Test tech-heavy portfolio
    tech_portfolio = create_test_portfolio("tech_heavy")
    portfolio_value = sum(pos['market_value'] for pos in tech_portfolio)
    
    analysis = correlation_manager.analyze_portfolio_concentration(tech_portfolio, portfolio_value)
    
    print(f"Tech-Heavy Portfolio (${portfolio_value:,}):")
    print(f"Sector Exposure:")
    for sector, exposure in analysis['sector_exposure_pct'].items():
        print(f"  {sector}: {exposure:.1f}%")
    
    print(f"\nSector Positions:")
    for sector, positions in analysis['sector_positions'].items():
        print(f"  {sector}: {len(positions)} positions ({', '.join(positions)})")
    
    print(f"\nConcentration Warnings:")
    for warning in analysis['concentration_warnings']:
        print(f"  ⚠️  {warning}")
    
    # Test adding another tech stock
    can_add, reasons = correlation_manager.can_add_position('AMD', tech_portfolio, portfolio_value)
    print(f"\nCan add AMD to tech-heavy portfolio? {can_add}")
    if not can_add:
        for reason in reasons:
            print(f"  ❌ {reason}")

def test_beta_exposure():
    """Test beta-weighted exposure controls."""
    print("\n\n📈 Testing Beta-Weighted Exposure Controls")
    print("=" * 60)
    
    correlation_manager = CorrelationManager()
    
    # Test high-beta portfolio
    high_beta_portfolio = create_test_portfolio("high_beta")
    portfolio_value = sum(pos['market_value'] for pos in high_beta_portfolio)
    
    analysis = correlation_manager.analyze_portfolio_concentration(high_beta_portfolio, portfolio_value)
    
    print(f"High-Beta Portfolio (${portfolio_value:,}):")
    print(f"Beta-Weighted Exposure: {analysis['beta_weighted_exposure']:.2f}")
    print(f"High-Beta Positions: {analysis['high_beta_count']}")
    
    # Show individual betas
    print(f"\nIndividual Position Betas:")
    for pos in high_beta_portfolio:
        symbol = pos['symbol']
        metadata = correlation_manager.get_symbol_metadata(symbol)
        weight = pos['market_value'] / portfolio_value * 100
        print(f"  {symbol}: Beta {metadata.beta:.1f}, Weight {weight:.1f}%")
    
    print(f"\nConcentration Warnings:")
    for warning in analysis['concentration_warnings']:
        print(f"  ⚠️  {warning}")

def test_correlation_detection():
    """Test correlation detection between symbols."""
    print("\n\n🔗 Testing Correlation Detection")
    print("=" * 60)
    
    correlation_manager = CorrelationManager()
    
    # Test correlations
    test_pairs = [
        ('AAPL', 'MSFT'),    # Tech correlation
        ('JPM', 'BAC'),      # Financial correlation
        ('NVDA', 'AMD'),     # Semiconductor correlation
        ('AAPL', 'JPM'),     # Cross-sector
        ('KO', 'PG'),        # Consumer staples
    ]
    
    print("Symbol Correlations:")
    for sym1, sym2 in test_pairs:
        corr = correlation_manager.get_correlation(sym1, sym2)
        sector1 = correlation_manager.get_symbol_metadata(sym1).sector.value
        sector2 = correlation_manager.get_symbol_metadata(sym2).sector.value
        print(f"  {sym1} ({sector1}) ↔ {sym2} ({sector2}): {corr:.2f}")
    
    # Test correlated groups in portfolio
    tech_portfolio = create_test_portfolio("tech_heavy")
    portfolio_value = sum(pos['market_value'] for pos in tech_portfolio)
    analysis = correlation_manager.analyze_portfolio_concentration(tech_portfolio, portfolio_value)
    
    print(f"\nCorrelated Groups in Tech Portfolio:")
    for i, group in enumerate(analysis['correlated_groups'], 1):
        print(f"  Group {i}: {', '.join(group)}")

def test_diversified_vs_concentrated():
    """Compare diversified vs concentrated portfolios."""
    print("\n\n⚖️  Comparing Diversified vs Concentrated Portfolios")
    print("=" * 60)
    
    correlation_manager = CorrelationManager()
    
    portfolios = {
        "Diversified": create_test_portfolio("diversified"),
        "Tech-Heavy": create_test_portfolio("tech_heavy"),
        "Financial-Heavy": create_test_portfolio("financial_heavy")
    }
    
    for name, portfolio in portfolios.items():
        portfolio_value = sum(pos['market_value'] for pos in portfolio)
        analysis = correlation_manager.analyze_portfolio_concentration(portfolio, portfolio_value)
        
        print(f"\n{name} Portfolio:")
        print(f"  Portfolio Value: ${portfolio_value:,}")
        print(f"  Beta-Weighted Exposure: {analysis['beta_weighted_exposure']:.2f}")
        print(f"  High-Beta Positions: {analysis['high_beta_count']}")
        print(f"  Correlated Groups: {len(analysis['correlated_groups'])}")
        print(f"  Concentration Warnings: {len(analysis['concentration_warnings'])}")
        
        if analysis['concentration_warnings']:
            print(f"  Warnings:")
            for warning in analysis['concentration_warnings'][:2]:  # Show first 2
                print(f"    ⚠️  {warning}")

def test_risk_integration():
    """Test integration with risk management system."""
    print("\n\n🛡️  Testing Risk Management Integration")
    print("=" * 60)
    
    # Create risk manager with custom correlation limits
    custom_limits = CorrelationLimits(
        max_positions_per_sector=2,
        max_sector_exposure_percent=25.0,
        max_beta_weighted_exposure=1.3,
        max_high_beta_positions=2
    )
    
    risk_manager = RiskManager(custom_limits)
    
    # Test with tech-heavy portfolio
    tech_portfolio = create_test_portfolio("tech_heavy")
    portfolio_value = sum(pos['market_value'] for pos in tech_portfolio)
    
    print("Custom Correlation Limits:")
    print(f"  Max positions per sector: {custom_limits.max_positions_per_sector}")
    print(f"  Max sector exposure: {custom_limits.max_sector_exposure_percent}%")
    print(f"  Max beta-weighted exposure: {custom_limits.max_beta_weighted_exposure}")
    print(f"  Max high-beta positions: {custom_limits.max_high_beta_positions}")
    
    # Test adding positions to tech-heavy portfolio
    test_symbols = ['AMD', 'CRM', 'JPM', 'JNJ']
    
    print(f"\nTesting position additions to tech-heavy portfolio:")
    for symbol in test_symbols:
        can_add, reasons = risk_manager.correlation_manager.can_add_position(
            symbol, tech_portfolio, portfolio_value
        )
        
        sector = risk_manager.correlation_manager.get_symbol_metadata(symbol).sector.value
        print(f"\n  {symbol} ({sector}): {'✅ Allowed' if can_add else '❌ Blocked'}")
        
        if not can_add:
            for reason in reasons:
                print(f"    • {reason}")

def main():
    """Run all correlation control tests."""
    print("🚀 Position Correlation and Concentration Controls Test")
    print("This demonstrates how the system prevents over-concentration risks\n")
    
    test_sector_concentration()
    test_beta_exposure()
    test_correlation_detection()
    test_diversified_vs_concentrated()
    test_risk_integration()
    
    print("\n" + "=" * 80)
    print("✅ Key Benefits of Correlation Controls:")
    print("   • Prevents sector over-concentration (max 2 positions per sector)")
    print("   • Limits beta-weighted exposure to control market risk")
    print("   • Detects and limits highly correlated positions")
    print("   • Provides comprehensive portfolio risk analysis")
    print("   • Integrates seamlessly with existing risk management")
    
    print("\n💡 Your suggestion addresses a critical gap in risk management!")
    print("   Portfolio heat alone isn't enough - correlation controls are essential")
    print("   for professional-grade risk management systems.")

if __name__ == "__main__":
    main()
