"""
Position correlation and concentration risk controls.
Prevents over-concentration in correlated assets and sectors.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import math

class Sector(Enum):
    """Major market sectors for classification."""
    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    FINANCIALS = "Financials"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    CONSUMER_STAPLES = "Consumer Staples"
    INDUSTRIALS = "Industrials"
    ENERGY = "Energy"
    UTILITIES = "Utilities"
    MATERIALS = "Materials"
    REAL_ESTATE = "Real Estate"
    TELECOMMUNICATIONS = "Telecommunications"
    UNKNOWN = "Unknown"

@dataclass
class SymbolMetadata:
    """Metadata for correlation analysis."""
    symbol: str
    sector: Sector
    beta: float  # Market beta (correlation to SPY)
    market_cap: Optional[float] = None
    industry: Optional[str] = None

@dataclass
class CorrelationLimits:
    """Configuration for correlation controls."""
    max_positions_per_sector: int = 2
    max_sector_exposure_percent: float = 30.0  # Max % of portfolio in one sector
    max_beta_weighted_exposure: float = 1.5    # Max beta-weighted exposure
    max_high_beta_positions: int = 3           # Max positions with beta > 1.5
    correlation_threshold: float = 0.7         # Consider symbols correlated above this
    max_correlated_positions: int = 2          # Max positions in highly correlated symbols

class CorrelationManager:
    """Manages position correlation and concentration controls."""
    
    def __init__(self, limits: Optional[CorrelationLimits] = None):
        self.limits = limits or CorrelationLimits()
        self.symbol_metadata: Dict[str, SymbolMetadata] = {}
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}
        self._initialize_symbol_metadata()
    
    def _initialize_symbol_metadata(self):
        """Initialize metadata for common symbols."""
        # Technology sector
        tech_symbols = {
            'AAPL': SymbolMetadata('AAPL', Sector.TECHNOLOGY, 1.2),
            'MSFT': SymbolMetadata('MSFT', Sector.TECHNOLOGY, 0.9),
            'GOOGL': SymbolMetadata('GOOGL', Sector.TECHNOLOGY, 1.1),
            'AMZN': SymbolMetadata('AMZN', Sector.TECHNOLOGY, 1.3),
            'TSLA': SymbolMetadata('TSLA', Sector.TECHNOLOGY, 2.0),
            'NVDA': SymbolMetadata('NVDA', Sector.TECHNOLOGY, 1.8),
            'META': SymbolMetadata('META', Sector.TECHNOLOGY, 1.4),
            'NFLX': SymbolMetadata('NFLX', Sector.TECHNOLOGY, 1.2),
            'AMD': SymbolMetadata('AMD', Sector.TECHNOLOGY, 1.9),
            'CRM': SymbolMetadata('CRM', Sector.TECHNOLOGY, 1.1),
        }
        
        # Financial sector
        financial_symbols = {
            'JPM': SymbolMetadata('JPM', Sector.FINANCIALS, 1.1),
            'BAC': SymbolMetadata('BAC', Sector.FINANCIALS, 1.3),
            'WFC': SymbolMetadata('WFC', Sector.FINANCIALS, 1.2),
            'GS': SymbolMetadata('GS', Sector.FINANCIALS, 1.4),
            'MS': SymbolMetadata('MS', Sector.FINANCIALS, 1.5),
        }
        
        # Healthcare sector
        healthcare_symbols = {
            'JNJ': SymbolMetadata('JNJ', Sector.HEALTHCARE, 0.7),
            'PFE': SymbolMetadata('PFE', Sector.HEALTHCARE, 0.8),
            'UNH': SymbolMetadata('UNH', Sector.HEALTHCARE, 0.9),
            'ABBV': SymbolMetadata('ABBV', Sector.HEALTHCARE, 0.8),
        }
        
        # Consumer sectors
        consumer_symbols = {
            'KO': SymbolMetadata('KO', Sector.CONSUMER_STAPLES, 0.6),
            'PG': SymbolMetadata('PG', Sector.CONSUMER_STAPLES, 0.5),
            'WMT': SymbolMetadata('WMT', Sector.CONSUMER_STAPLES, 0.5),
            'DIS': SymbolMetadata('DIS', Sector.CONSUMER_DISCRETIONARY, 1.1),
            'NKE': SymbolMetadata('NKE', Sector.CONSUMER_DISCRETIONARY, 0.9),
        }
        
        # Energy sector
        energy_symbols = {
            'XOM': SymbolMetadata('XOM', Sector.ENERGY, 1.0),
            'CVX': SymbolMetadata('CVX', Sector.ENERGY, 1.1),
        }
        
        # Combine all symbols
        self.symbol_metadata.update(tech_symbols)
        self.symbol_metadata.update(financial_symbols)
        self.symbol_metadata.update(healthcare_symbols)
        self.symbol_metadata.update(consumer_symbols)
        self.symbol_metadata.update(energy_symbols)
        
        # Initialize some correlation data (in practice, this would come from historical analysis)
        self._initialize_correlations()
    
    def _initialize_correlations(self):
        """Initialize correlation matrix for known symbol pairs."""
        # High correlations within tech sector
        tech_correlations = [
            (('AAPL', 'MSFT'), 0.75),
            (('GOOGL', 'META'), 0.82),
            (('NVDA', 'AMD'), 0.85),
            (('TSLA', 'NVDA'), 0.72),
        ]
        
        # Financial sector correlations
        financial_correlations = [
            (('JPM', 'BAC'), 0.88),
            (('GS', 'MS'), 0.91),
            (('JPM', 'WFC'), 0.83),
        ]
        
        # Cross-sector correlations (generally lower)
        cross_sector_correlations = [
            (('AAPL', 'JPM'), 0.45),
            (('TSLA', 'DIS'), 0.35),
            (('KO', 'PG'), 0.65),  # Consumer staples correlation
        ]
        
        # Add correlations (symmetric)
        for correlations in [tech_correlations, financial_correlations, cross_sector_correlations]:
            for (sym1, sym2), corr in correlations:
                self.correlation_matrix[(sym1, sym2)] = corr
                self.correlation_matrix[(sym2, sym1)] = corr
    
    def get_symbol_metadata(self, symbol: str) -> SymbolMetadata:
        """Get metadata for a symbol, with fallback for unknown symbols."""
        if symbol in self.symbol_metadata:
            return self.symbol_metadata[symbol]
        
        # Fallback for unknown symbols
        return SymbolMetadata(
            symbol=symbol,
            sector=Sector.UNKNOWN,
            beta=1.0  # Assume market beta for unknown symbols
        )
    
    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Get correlation between two symbols."""
        if symbol1 == symbol2:
            return 1.0
        
        key1 = (symbol1, symbol2)
        key2 = (symbol2, symbol1)
        
        if key1 in self.correlation_matrix:
            return self.correlation_matrix[key1]
        elif key2 in self.correlation_matrix:
            return self.correlation_matrix[key2]
        
        # Estimate correlation based on sector
        meta1 = self.get_symbol_metadata(symbol1)
        meta2 = self.get_symbol_metadata(symbol2)
        
        if meta1.sector == meta2.sector and meta1.sector != Sector.UNKNOWN:
            # Same sector - assume moderate correlation
            return 0.6
        else:
            # Different sectors - assume low correlation
            return 0.3
    
    def analyze_portfolio_concentration(
        self, 
        current_positions: List[Dict[str, any]], 
        portfolio_value: float
    ) -> Dict[str, any]:
        """Analyze current portfolio for concentration risks."""
        
        # Group positions by sector
        sector_exposure = {}
        sector_positions = {}
        beta_weighted_exposure = 0.0
        high_beta_count = 0
        
        for position in current_positions:
            symbol = position.get('symbol', '')
            market_value = abs(position.get('market_value', 0))
            
            metadata = self.get_symbol_metadata(symbol)
            sector = metadata.sector.value
            
            # Track sector exposure
            if sector not in sector_exposure:
                sector_exposure[sector] = 0.0
                sector_positions[sector] = []
            
            sector_exposure[sector] += market_value
            sector_positions[sector].append(symbol)
            
            # Calculate beta-weighted exposure
            position_weight = market_value / portfolio_value if portfolio_value > 0 else 0
            beta_weighted_exposure += position_weight * metadata.beta
            
            # Count high beta positions
            if metadata.beta > 1.5:
                high_beta_count += 1
        
        # Convert to percentages
        sector_exposure_pct = {
            sector: (exposure / portfolio_value * 100) if portfolio_value > 0 else 0
            for sector, exposure in sector_exposure.items()
        }
        
        # Find highly correlated position groups
        correlated_groups = self._find_correlated_groups(
            [pos.get('symbol', '') for pos in current_positions]
        )
        
        return {
            'sector_exposure_pct': sector_exposure_pct,
            'sector_positions': sector_positions,
            'beta_weighted_exposure': beta_weighted_exposure,
            'high_beta_count': high_beta_count,
            'correlated_groups': correlated_groups,
            'concentration_warnings': self._generate_concentration_warnings(
                sector_exposure_pct, sector_positions, beta_weighted_exposure, 
                high_beta_count, correlated_groups
            )
        }
    
    def _find_correlated_groups(self, symbols: List[str]) -> List[List[str]]:
        """Find groups of highly correlated symbols."""
        groups = []
        processed = set()
        
        for symbol in symbols:
            if symbol in processed:
                continue
            
            # Find all symbols correlated with this one
            correlated = [symbol]
            for other_symbol in symbols:
                if (other_symbol != symbol and 
                    other_symbol not in processed and
                    self.get_correlation(symbol, other_symbol) >= self.limits.correlation_threshold):
                    correlated.append(other_symbol)
            
            if len(correlated) > 1:
                groups.append(correlated)
                processed.update(correlated)
            else:
                processed.add(symbol)
        
        return groups
    
    def _generate_concentration_warnings(
        self, 
        sector_exposure_pct: Dict[str, float],
        sector_positions: Dict[str, List[str]],
        beta_weighted_exposure: float,
        high_beta_count: int,
        correlated_groups: List[List[str]]
    ) -> List[str]:
        """Generate warnings for concentration risks."""
        warnings = []
        
        # Check sector concentration
        for sector, exposure_pct in sector_exposure_pct.items():
            if exposure_pct > self.limits.max_sector_exposure_percent:
                warnings.append(
                    f"Sector concentration risk: {sector} exposure is {exposure_pct:.1f}% "
                    f"(limit: {self.limits.max_sector_exposure_percent:.1f}%)"
                )
            
            position_count = len(sector_positions.get(sector, []))
            if position_count > self.limits.max_positions_per_sector:
                warnings.append(
                    f"Too many positions in {sector}: {position_count} "
                    f"(limit: {self.limits.max_positions_per_sector})"
                )
        
        # Check beta-weighted exposure
        if beta_weighted_exposure > self.limits.max_beta_weighted_exposure:
            warnings.append(
                f"High beta-weighted exposure: {beta_weighted_exposure:.2f} "
                f"(limit: {self.limits.max_beta_weighted_exposure:.2f})"
            )
        
        # Check high beta positions
        if high_beta_count > self.limits.max_high_beta_positions:
            warnings.append(
                f"Too many high-beta positions: {high_beta_count} "
                f"(limit: {self.limits.max_high_beta_positions})"
            )
        
        # Check correlated groups
        for group in correlated_groups:
            if len(group) > self.limits.max_correlated_positions:
                warnings.append(
                    f"Too many correlated positions: {', '.join(group)} "
                    f"({len(group)} positions, limit: {self.limits.max_correlated_positions})"
                )
        
        return warnings
    
    def can_add_position(
        self, 
        symbol: str, 
        current_positions: List[Dict[str, any]], 
        portfolio_value: float
    ) -> Tuple[bool, List[str]]:
        """Check if a new position can be added without violating correlation controls."""
        reasons = []
        
        # Get symbol metadata
        metadata = self.get_symbol_metadata(symbol)
        
        # Analyze current portfolio
        analysis = self.analyze_portfolio_concentration(current_positions, portfolio_value)
        
        # Check sector limits
        sector = metadata.sector.value
        current_sector_positions = analysis['sector_positions'].get(sector, [])
        
        if len(current_sector_positions) >= self.limits.max_positions_per_sector:
            reasons.append(
                f"Sector limit reached: {len(current_sector_positions)} positions in {sector} "
                f"(limit: {self.limits.max_positions_per_sector})"
            )
        
        # Check if adding this position would exceed sector exposure limit
        # (This is a simplified check - in practice, you'd need the position size)
        current_sector_exposure = analysis['sector_exposure_pct'].get(sector, 0)
        if current_sector_exposure > self.limits.max_sector_exposure_percent * 0.8:  # 80% of limit
            reasons.append(
                f"Sector exposure approaching limit: {sector} at {current_sector_exposure:.1f}% "
                f"(limit: {self.limits.max_sector_exposure_percent:.1f}%)"
            )
        
        # Check beta limits
        if metadata.beta > 1.5 and analysis['high_beta_count'] >= self.limits.max_high_beta_positions:
            reasons.append(
                f"High-beta position limit reached: {analysis['high_beta_count']} positions "
                f"(limit: {self.limits.max_high_beta_positions})"
            )
        
        # Check correlation with existing positions
        current_symbols = [pos.get('symbol', '') for pos in current_positions]
        highly_correlated = []
        
        for existing_symbol in current_symbols:
            correlation = self.get_correlation(symbol, existing_symbol)
            if correlation >= self.limits.correlation_threshold:
                highly_correlated.append(existing_symbol)
        
        if len(highly_correlated) >= self.limits.max_correlated_positions:
            reasons.append(
                f"Correlation limit reached: {symbol} is highly correlated with "
                f"{', '.join(highly_correlated)} ({len(highly_correlated)} positions, "
                f"limit: {self.limits.max_correlated_positions})"
            )
        
        return len(reasons) == 0, reasons
