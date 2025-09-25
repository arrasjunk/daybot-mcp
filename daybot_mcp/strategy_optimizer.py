"""
Strategy optimization and recommendation engine.
Analyzes trading performance to provide actionable insights for strategy improvement.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from .analytics import Trade, TradeAnalyzer, PerformanceMetrics
from .risk_analytics import RiskAnalyzer, RiskMetrics
from .execution_analytics import ExecutionAnalyzer, ExecutionMetrics


class OptimizationCategory(str, Enum):
    """Categories of optimization recommendations."""
    ENTRY_TIMING = "entry_timing"
    EXIT_STRATEGY = "exit_strategy"
    POSITION_SIZING = "position_sizing"
    RISK_MANAGEMENT = "risk_management"
    SYMBOL_SELECTION = "symbol_selection"
    TIME_FILTERS = "time_filters"
    EXECUTION_QUALITY = "execution_quality"
    PORTFOLIO_MANAGEMENT = "portfolio_management"


@dataclass
class OptimizationRecommendation:
    """Individual optimization recommendation."""
    category: OptimizationCategory
    priority: str  # "high", "medium", "low"
    title: str
    description: str
    expected_impact: str
    implementation_difficulty: str  # "easy", "medium", "hard"
    metrics_supporting: List[str]
    specific_actions: List[str]
    estimated_improvement: Optional[float] = None  # Expected percentage improvement


@dataclass
class StrategyAnalysis:
    """Comprehensive strategy analysis results."""
    strategy_name: str
    total_trades: int
    performance_score: float  # 0-100 score
    strengths: List[str]
    weaknesses: List[str]
    optimization_potential: float  # Estimated improvement potential
    
    # Performance breakdown
    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float
    sharpe_ratio: float
    
    # Pattern analysis
    best_performing_symbols: List[Tuple[str, float]]
    worst_performing_symbols: List[Tuple[str, float]]
    best_time_periods: List[Tuple[str, float]]
    worst_time_periods: List[Tuple[str, float]]


class StrategyOptimizer:
    """Strategy optimization and recommendation engine."""
    
    def __init__(self, analyzer: TradeAnalyzer):
        """Initialize strategy optimizer."""
        self.analyzer = analyzer
        self.risk_analyzer = RiskAnalyzer(analyzer)
        self.execution_analyzer = ExecutionAnalyzer(analyzer)
    
    def analyze_strategy_performance(self, trades: List[Trade], strategy_name: str) -> StrategyAnalysis:
        """Analyze performance of a specific strategy."""
        if not trades:
            return StrategyAnalysis(
                strategy_name=strategy_name,
                total_trades=0,
                performance_score=0.0,
                strengths=[],
                weaknesses=[],
                optimization_potential=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                expectancy=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                best_performing_symbols=[],
                worst_performing_symbols=[],
                best_time_periods=[],
                worst_time_periods=[]
            )
        
        # Calculate basic metrics
        metrics = self.analyzer.calculate_performance_metrics(trades)
        
        # Calculate performance score (0-100)
        performance_score = self._calculate_performance_score(metrics)
        
        # Analyze patterns
        symbol_performance = self._analyze_symbol_performance(trades)
        time_performance = self._analyze_time_performance(trades)
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(metrics, trades)
        
        # Estimate optimization potential
        optimization_potential = self._estimate_optimization_potential(metrics, trades)
        
        return StrategyAnalysis(
            strategy_name=strategy_name,
            total_trades=len(trades),
            performance_score=performance_score,
            strengths=strengths,
            weaknesses=weaknesses,
            optimization_potential=optimization_potential,
            win_rate=metrics.win_rate,
            profit_factor=metrics.profit_factor,
            expectancy=metrics.expectancy,
            max_drawdown=metrics.max_drawdown_percent,
            sharpe_ratio=metrics.sharpe_ratio,
            best_performing_symbols=symbol_performance[:5],
            worst_performing_symbols=symbol_performance[-5:],
            best_time_periods=time_performance[:3],
            worst_time_periods=time_performance[-3:]
        )
    
    def generate_optimization_recommendations(self, trades: List[Trade]) -> List[OptimizationRecommendation]:
        """Generate comprehensive optimization recommendations."""
        recommendations = []
        
        # Calculate all metrics
        performance_metrics = self.analyzer.calculate_performance_metrics(trades)
        risk_metrics = self.risk_analyzer.calculate_comprehensive_risk_metrics(trades)
        execution_metrics = self.execution_analyzer.calculate_comprehensive_execution_metrics(trades)
        
        # Generate recommendations by category
        recommendations.extend(self._analyze_entry_timing(trades, performance_metrics))
        recommendations.extend(self._analyze_exit_strategy(trades, performance_metrics))
        recommendations.extend(self._analyze_position_sizing(trades, risk_metrics))
        recommendations.extend(self._analyze_risk_management(trades, risk_metrics))
        recommendations.extend(self._analyze_symbol_selection(trades, performance_metrics))
        recommendations.extend(self._analyze_time_filters(trades, performance_metrics))
        recommendations.extend(self._analyze_execution_quality(trades, execution_metrics))
        recommendations.extend(self._analyze_portfolio_management(trades, risk_metrics))
        
        # Sort by priority and expected impact
        recommendations.sort(key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}[x.priority],
            -x.estimated_improvement if x.estimated_improvement else 0
        ))
        
        return recommendations
    
    def _calculate_performance_score(self, metrics: PerformanceMetrics) -> float:
        """Calculate overall performance score (0-100)."""
        if metrics.total_trades == 0:
            return 0.0
        
        # Weight different metrics
        win_rate_score = min(metrics.win_rate / 60 * 25, 25)  # Max 25 points for 60%+ win rate
        profit_factor_score = min(metrics.profit_factor / 2 * 25, 25)  # Max 25 points for 2.0+ PF
        expectancy_score = min(max(metrics.expectancy / 100 * 20, 0), 20)  # Max 20 points for $100+ expectancy
        drawdown_score = max(20 - (metrics.max_drawdown_percent / 20 * 20), 0)  # Penalty for drawdown
        sharpe_score = min(max(metrics.sharpe_ratio / 2 * 10, 0), 10)  # Max 10 points for 2.0+ Sharpe
        
        return win_rate_score + profit_factor_score + expectancy_score + drawdown_score + sharpe_score
    
    def _analyze_symbol_performance(self, trades: List[Trade]) -> List[Tuple[str, float]]:
        """Analyze performance by symbol."""
        symbol_stats = defaultdict(lambda: {"pnl": 0.0, "count": 0})
        
        for trade in trades:
            symbol_stats[trade.symbol]["pnl"] += trade.pnl
            symbol_stats[trade.symbol]["count"] += 1
        
        # Calculate average P&L per trade by symbol
        symbol_performance = []
        for symbol, stats in symbol_stats.items():
            if stats["count"] >= 3:  # Minimum 3 trades for statistical significance
                avg_pnl = stats["pnl"] / stats["count"]
                symbol_performance.append((symbol, avg_pnl))
        
        return sorted(symbol_performance, key=lambda x: x[1], reverse=True)
    
    def _analyze_time_performance(self, trades: List[Trade]) -> List[Tuple[str, float]]:
        """Analyze performance by time of day."""
        time_stats = defaultdict(lambda: {"pnl": 0.0, "count": 0})
        
        for trade in trades:
            hour = trade.entry_time.hour
            if 9 <= hour <= 10:
                period = "Market Open (9-10 AM)"
            elif 10 <= hour <= 12:
                period = "Morning (10-12 PM)"
            elif 12 <= hour <= 14:
                period = "Midday (12-2 PM)"
            elif 14 <= hour <= 16:
                period = "Afternoon (2-4 PM)"
            else:
                period = "Extended Hours"
            
            time_stats[period]["pnl"] += trade.pnl
            time_stats[period]["count"] += 1
        
        # Calculate average P&L per trade by time period
        time_performance = []
        for period, stats in time_stats.items():
            if stats["count"] >= 2:
                avg_pnl = stats["pnl"] / stats["count"]
                time_performance.append((period, avg_pnl))
        
        return sorted(time_performance, key=lambda x: x[1], reverse=True)
    
    def _identify_strengths_weaknesses(self, metrics: PerformanceMetrics, trades: List[Trade]) -> Tuple[List[str], List[str]]:
        """Identify strategy strengths and weaknesses."""
        strengths = []
        weaknesses = []
        
        # Win rate analysis
        if metrics.win_rate >= 60:
            strengths.append(f"High win rate ({metrics.win_rate:.1f}%) indicates good entry timing")
        elif metrics.win_rate <= 40:
            weaknesses.append(f"Low win rate ({metrics.win_rate:.1f}%) suggests poor entry signals")
        
        # Profit factor analysis
        if metrics.profit_factor >= 2.0:
            strengths.append(f"Excellent profit factor ({metrics.profit_factor:.2f}) shows strong edge")
        elif metrics.profit_factor <= 1.2:
            weaknesses.append(f"Low profit factor ({metrics.profit_factor:.2f}) indicates weak edge")
        
        # Expectancy analysis
        if metrics.expectancy >= 50:
            strengths.append(f"Positive expectancy (${metrics.expectancy:.2f}) per trade")
        elif metrics.expectancy <= 0:
            weaknesses.append(f"Negative expectancy (${metrics.expectancy:.2f}) per trade")
        
        # Drawdown analysis
        if metrics.max_drawdown_percent <= 10:
            strengths.append(f"Low maximum drawdown ({metrics.max_drawdown_percent:.1f}%)")
        elif metrics.max_drawdown_percent >= 25:
            weaknesses.append(f"High maximum drawdown ({metrics.max_drawdown_percent:.1f}%)")
        
        # Sharpe ratio analysis
        if metrics.sharpe_ratio >= 1.5:
            strengths.append(f"Strong risk-adjusted returns (Sharpe: {metrics.sharpe_ratio:.2f})")
        elif metrics.sharpe_ratio <= 0.5:
            weaknesses.append(f"Poor risk-adjusted returns (Sharpe: {metrics.sharpe_ratio:.2f})")
        
        # Consecutive losses
        if metrics.max_consecutive_losses >= 8:
            weaknesses.append(f"High consecutive losses ({metrics.max_consecutive_losses}) suggest lack of filters")
        
        return strengths, weaknesses
    
    def _estimate_optimization_potential(self, metrics: PerformanceMetrics, trades: List[Trade]) -> float:
        """Estimate potential improvement percentage."""
        potential = 0.0
        
        # Win rate improvement potential
        if metrics.win_rate < 50:
            potential += 15.0  # High potential for improvement
        elif metrics.win_rate < 60:
            potential += 8.0   # Medium potential
        
        # Profit factor improvement potential
        if metrics.profit_factor < 1.5:
            potential += 20.0  # High potential
        elif metrics.profit_factor < 2.0:
            potential += 10.0  # Medium potential
        
        # Drawdown reduction potential
        if metrics.max_drawdown_percent > 20:
            potential += 15.0  # High potential
        elif metrics.max_drawdown_percent > 15:
            potential += 8.0   # Medium potential
        
        # Execution improvement potential
        avg_slippage = sum(t.slippage for t in trades) / len(trades) if trades else 0
        if avg_slippage < -0.02:  # High negative slippage
            potential += 10.0
        
        return min(potential, 50.0)  # Cap at 50% potential improvement
    
    def _analyze_entry_timing(self, trades: List[Trade], metrics: PerformanceMetrics) -> List[OptimizationRecommendation]:
        """Analyze entry timing optimization opportunities."""
        recommendations = []
        
        if metrics.win_rate < 45:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.ENTRY_TIMING,
                priority="high",
                title="Improve Entry Signal Quality",
                description="Low win rate suggests entry signals need refinement",
                expected_impact="10-20% improvement in win rate",
                implementation_difficulty="medium",
                metrics_supporting=[f"Win rate: {metrics.win_rate:.1f}%"],
                specific_actions=[
                    "Add confirmation indicators to entry signals",
                    "Implement trend filters to avoid counter-trend trades",
                    "Use volume confirmation for breakout entries",
                    "Add volatility filters to avoid low-probability setups"
                ],
                estimated_improvement=15.0
            ))
        
        # Analyze time-based patterns
        time_performance = self._analyze_time_performance(trades)
        if time_performance:
            worst_period = time_performance[-1]
            if worst_period[1] < -10:  # Losing more than $10 per trade on average
                recommendations.append(OptimizationRecommendation(
                    category=OptimizationCategory.TIME_FILTERS,
                    priority="medium",
                    title="Avoid Poor Performance Time Periods",
                    description=f"Consistently poor performance during {worst_period[0]}",
                    expected_impact="5-10% improvement in overall performance",
                    implementation_difficulty="easy",
                    metrics_supporting=[f"Average P&L during {worst_period[0]}: ${worst_period[1]:.2f}"],
                    specific_actions=[
                        f"Implement time filter to avoid trading during {worst_period[0]}",
                        "Analyze market conditions during poor performance periods",
                        "Consider different strategies for different time periods"
                    ],
                    estimated_improvement=8.0
                ))
        
        return recommendations
    
    def _analyze_exit_strategy(self, trades: List[Trade], metrics: PerformanceMetrics) -> List[OptimizationRecommendation]:
        """Analyze exit strategy optimization opportunities."""
        recommendations = []
        
        # Analyze win/loss ratio
        if metrics.avg_loss != 0 and abs(metrics.avg_win / metrics.avg_loss) < 1.5:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.EXIT_STRATEGY,
                priority="high",
                title="Improve Risk/Reward Ratio",
                description="Average win to average loss ratio is suboptimal",
                expected_impact="15-25% improvement in profit factor",
                implementation_difficulty="medium",
                metrics_supporting=[
                    f"Average win: ${metrics.avg_win:.2f}",
                    f"Average loss: ${metrics.avg_loss:.2f}",
                    f"Win/Loss ratio: {abs(metrics.avg_win / metrics.avg_loss):.2f}"
                ],
                specific_actions=[
                    "Implement trailing stops to capture larger wins",
                    "Use ATR-based targets instead of fixed percentages",
                    "Add partial profit-taking at key levels",
                    "Tighten stops after reaching 1R profit"
                ],
                estimated_improvement=20.0
            ))
        
        # Analyze holding periods
        durations = [t.duration_minutes for t in trades]
        if durations:
            avg_duration = sum(durations) / len(durations)
            if avg_duration > 240:  # More than 4 hours average
                recommendations.append(OptimizationRecommendation(
                    category=OptimizationCategory.EXIT_STRATEGY,
                    priority="medium",
                    title="Reduce Average Holding Time",
                    description="Long holding periods may indicate poor exit timing",
                    expected_impact="5-10% improvement in capital efficiency",
                    implementation_difficulty="medium",
                    metrics_supporting=[f"Average holding time: {avg_duration:.1f} minutes"],
                    specific_actions=[
                        "Implement time-based exits for stalled positions",
                        "Use momentum indicators for exit signals",
                        "Consider intraday mean reversion patterns"
                    ],
                    estimated_improvement=7.0
                ))
        
        return recommendations
    
    def _analyze_position_sizing(self, trades: List[Trade], risk_metrics: RiskMetrics) -> List[OptimizationRecommendation]:
        """Analyze position sizing optimization opportunities."""
        recommendations = []
        
        if risk_metrics.max_drawdown_percent > 20:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.POSITION_SIZING,
                priority="high",
                title="Reduce Position Sizes",
                description="High drawdown indicates excessive position sizing",
                expected_impact="30-50% reduction in drawdown",
                implementation_difficulty="easy",
                metrics_supporting=[f"Maximum drawdown: {risk_metrics.max_drawdown_percent:.1f}%"],
                specific_actions=[
                    "Reduce position size by 25-50%",
                    "Implement Kelly Criterion for optimal sizing",
                    "Use volatility-adjusted position sizing",
                    "Add correlation limits between positions"
                ],
                estimated_improvement=25.0
            ))
        
        if risk_metrics.max_heat > 80:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.PORTFOLIO_MANAGEMENT,
                priority="high",
                title="Reduce Portfolio Heat",
                description="Excessive concurrent risk exposure",
                expected_impact="20-30% reduction in portfolio volatility",
                implementation_difficulty="medium",
                metrics_supporting=[f"Maximum portfolio heat: {risk_metrics.max_heat:.1f}%"],
                specific_actions=[
                    "Limit maximum concurrent positions",
                    "Implement sector/correlation limits",
                    "Use dynamic position sizing based on portfolio heat",
                    "Add position correlation monitoring"
                ],
                estimated_improvement=15.0
            ))
        
        return recommendations
    
    def _analyze_risk_management(self, trades: List[Trade], risk_metrics: RiskMetrics) -> List[OptimizationRecommendation]:
        """Analyze risk management optimization opportunities."""
        recommendations = []
        
        if risk_metrics.sharpe_ratio < 1.0:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.RISK_MANAGEMENT,
                priority="medium",
                title="Improve Risk-Adjusted Returns",
                description="Low Sharpe ratio indicates poor risk management",
                expected_impact="50-100% improvement in Sharpe ratio",
                implementation_difficulty="medium",
                metrics_supporting=[f"Sharpe ratio: {risk_metrics.sharpe_ratio:.2f}"],
                specific_actions=[
                    "Implement volatility-based position sizing",
                    "Add market regime filters",
                    "Use dynamic stop losses based on volatility",
                    "Implement correlation-based risk limits"
                ],
                estimated_improvement=12.0
            ))
        
        if len(risk_metrics.drawdown_periods) > 5:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.RISK_MANAGEMENT,
                priority="medium",
                title="Reduce Drawdown Frequency",
                description="Frequent drawdown periods suggest insufficient risk controls",
                expected_impact="25-40% reduction in drawdown frequency",
                implementation_difficulty="medium",
                metrics_supporting=[f"Drawdown periods: {len(risk_metrics.drawdown_periods)}"],
                specific_actions=[
                    "Implement daily loss limits",
                    "Add maximum consecutive loss limits",
                    "Use portfolio heat monitoring",
                    "Implement market condition filters"
                ],
                estimated_improvement=10.0
            ))
        
        return recommendations
    
    def _analyze_symbol_selection(self, trades: List[Trade], metrics: PerformanceMetrics) -> List[OptimizationRecommendation]:
        """Analyze symbol selection optimization opportunities."""
        recommendations = []
        
        symbol_performance = self._analyze_symbol_performance(trades)
        if len(symbol_performance) >= 5:
            # Check if there's a significant performance difference
            best_avg = symbol_performance[0][1]
            worst_avg = symbol_performance[-1][1]
            
            if best_avg - worst_avg > 20:  # $20 difference in average P&L
                recommendations.append(OptimizationRecommendation(
                    category=OptimizationCategory.SYMBOL_SELECTION,
                    priority="medium",
                    title="Focus on Best Performing Symbols",
                    description="Significant performance variation across symbols",
                    expected_impact="10-20% improvement in average P&L per trade",
                    implementation_difficulty="easy",
                    metrics_supporting=[
                        f"Best symbol avg P&L: ${best_avg:.2f}",
                        f"Worst symbol avg P&L: ${worst_avg:.2f}"
                    ],
                    specific_actions=[
                        f"Increase allocation to top performers: {', '.join([s[0] for s in symbol_performance[:3]])}",
                        f"Reduce or eliminate poor performers: {', '.join([s[0] for s in symbol_performance[-2:]])}",
                        "Analyze characteristics of best performing symbols",
                        "Implement symbol scoring system"
                    ],
                    estimated_improvement=15.0
                ))
        
        return recommendations
    
    def _analyze_time_filters(self, trades: List[Trade], metrics: PerformanceMetrics) -> List[OptimizationRecommendation]:
        """Analyze time-based filter opportunities."""
        # This is handled in _analyze_entry_timing to avoid duplication
        return []
    
    def _analyze_execution_quality(self, trades: List[Trade], execution_metrics: ExecutionMetrics) -> List[OptimizationRecommendation]:
        """Analyze execution quality optimization opportunities."""
        recommendations = []
        
        if execution_metrics.avg_slippage < -0.02:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.EXECUTION_QUALITY,
                priority="medium",
                title="Improve Order Execution",
                description="High negative slippage impacting profitability",
                expected_impact="5-15% improvement in net returns",
                implementation_difficulty="medium",
                metrics_supporting=[f"Average slippage: ${execution_metrics.avg_slippage:.4f}"],
                specific_actions=[
                    "Use limit orders instead of market orders when possible",
                    "Implement smart order routing",
                    "Avoid trading during high volatility periods",
                    "Use smaller order sizes to reduce market impact"
                ],
                estimated_improvement=8.0
            ))
        
        return recommendations
    
    def _analyze_portfolio_management(self, trades: List[Trade], risk_metrics: RiskMetrics) -> List[OptimizationRecommendation]:
        """Analyze portfolio management optimization opportunities."""
        # This is handled in _analyze_position_sizing to avoid duplication
        return []
    
    def generate_optimization_report(self, trades: List[Trade]) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        recommendations = self.generate_optimization_recommendations(trades)
        
        # Group recommendations by category
        by_category = defaultdict(list)
        for rec in recommendations:
            by_category[rec.category.value].append(rec)
        
        # Calculate total estimated improvement
        total_improvement = sum(
            rec.estimated_improvement for rec in recommendations 
            if rec.estimated_improvement and rec.priority == "high"
        )
        
        report = {
            "summary": {
                "total_recommendations": len(recommendations),
                "high_priority": len([r for r in recommendations if r.priority == "high"]),
                "estimated_total_improvement": f"{min(total_improvement, 100):.1f}%",
                "quick_wins": len([r for r in recommendations if r.implementation_difficulty == "easy"])
            },
            "by_priority": {
                "high": [self._format_recommendation(r) for r in recommendations if r.priority == "high"],
                "medium": [self._format_recommendation(r) for r in recommendations if r.priority == "medium"],
                "low": [self._format_recommendation(r) for r in recommendations if r.priority == "low"]
            },
            "by_category": {
                category: [self._format_recommendation(r) for r in recs]
                for category, recs in by_category.items()
            },
            "implementation_roadmap": self._create_implementation_roadmap(recommendations)
        }
        
        return report
    
    def _format_recommendation(self, rec: OptimizationRecommendation) -> Dict[str, Any]:
        """Format recommendation for output."""
        return {
            "title": rec.title,
            "description": rec.description,
            "expected_impact": rec.expected_impact,
            "difficulty": rec.implementation_difficulty,
            "actions": rec.specific_actions,
            "supporting_metrics": rec.metrics_supporting,
            "estimated_improvement": f"{rec.estimated_improvement:.1f}%" if rec.estimated_improvement else "N/A"
        }
    
    def _create_implementation_roadmap(self, recommendations: List[OptimizationRecommendation]) -> Dict[str, List[str]]:
        """Create implementation roadmap."""
        roadmap = {
            "immediate": [],  # Easy, high-impact
            "short_term": [], # Medium difficulty, high-impact
            "long_term": []   # Hard or low-impact
        }
        
        for rec in recommendations:
            if rec.implementation_difficulty == "easy" and rec.priority == "high":
                roadmap["immediate"].append(rec.title)
            elif rec.priority == "high" or rec.implementation_difficulty == "medium":
                roadmap["short_term"].append(rec.title)
            else:
                roadmap["long_term"].append(rec.title)
        
        return roadmap
