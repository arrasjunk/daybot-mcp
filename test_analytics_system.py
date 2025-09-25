#!/usr/bin/env python3
"""
Comprehensive test suite for the DayBot Analytics System.
Tests all components: analytics engine, risk analysis, execution analysis, and optimization.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from daybot_mcp.analytics import (
    TradeAnalyzer, Trade, PerformanceMetrics, TradeOutcome, AnalyticsPeriod
)
from daybot_mcp.risk_analytics import RiskAnalyzer, DrawdownPeriod
from daybot_mcp.execution_analytics import ExecutionAnalyzer, TimeOfDay
from daybot_mcp.strategy_optimizer import StrategyOptimizer, OptimizationCategory


class TestTradeAnalyzer:
    """Test the core trade analytics engine."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def analyzer(self, temp_dir):
        """Create analyzer instance for testing."""
        return TradeAnalyzer(log_dir=temp_dir)
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample trades for testing."""
        base_time = datetime.now(timezone.utc)
        
        trades = [
            # Winning trade
            Trade(
                symbol="AAPL",
                strategy="momentum",
                entry_time=base_time,
                exit_time=base_time + timedelta(hours=1),
                entry_price=150.0,
                exit_price=155.0,
                quantity=100,
                side="buy",
                pnl=500.0,
                pnl_percent=3.33,
                commission=1.0,
                slippage=0.01,
                exit_reason="take_profit",
                max_favorable_excursion=600.0,
                max_adverse_excursion=50.0
            ),
            # Losing trade
            Trade(
                symbol="MSFT",
                strategy="momentum",
                entry_time=base_time + timedelta(hours=2),
                exit_time=base_time + timedelta(hours=3),
                entry_price=300.0,
                exit_price=294.0,
                quantity=50,
                side="buy",
                pnl=-300.0,
                pnl_percent=-2.0,
                commission=0.5,
                slippage=-0.02,
                exit_reason="stop_loss",
                max_favorable_excursion=100.0,
                max_adverse_excursion=350.0
            ),
            # Breakeven trade
            Trade(
                symbol="GOOGL",
                strategy="scalping",
                entry_time=base_time + timedelta(hours=4),
                exit_time=base_time + timedelta(hours=4, minutes=30),
                entry_price=2500.0,
                exit_price=2500.5,
                quantity=10,
                side="buy",
                pnl=0.0,
                pnl_percent=0.02,
                commission=5.0,
                slippage=0.0,
                exit_reason="time_exit"
            )
        ]
        return trades
    
    def test_add_and_retrieve_trades(self, analyzer, sample_trades):
        """Test adding and retrieving trades."""
        # Add trades
        for trade in sample_trades:
            trade_id = analyzer.add_trade(trade)
            assert trade_id > 0
        
        # Retrieve all trades
        retrieved_trades = analyzer.get_trades()
        assert len(retrieved_trades) == len(sample_trades)
        
        # Check trade data integrity without assuming order
        symbols = {t.symbol for t in retrieved_trades}
        assert symbols == {"AAPL", "MSFT", "GOOGL"}
        aapl_trade = next(t for t in retrieved_trades if t.symbol == "AAPL")
        assert aapl_trade.pnl == 500.0
        assert aapl_trade.outcome == TradeOutcome.WIN
    
    def test_trade_filtering(self, analyzer, sample_trades):
        """Test trade filtering capabilities."""
        # Add trades
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        # Filter by symbol
        aapl_trades = analyzer.get_trades(symbol="AAPL")
        assert len(aapl_trades) == 1
        assert aapl_trades[0].symbol == "AAPL"
        
        # Filter by strategy
        momentum_trades = analyzer.get_trades(strategy="momentum")
        assert len(momentum_trades) == 2
        
        # Filter by limit
        limited_trades = analyzer.get_trades(limit=1)
        assert len(limited_trades) == 1
    def test_performance_metrics_calculation(self, analyzer, sample_trades):
        """Test performance metrics calculation."""
        # Add trades
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        trades = analyzer.get_trades()
        metrics = analyzer.calculate_performance_metrics(trades)
        
        # P&L metrics
        assert metrics.total_pnl == pytest.approx(200.0, abs=1e-6)  # 500 - 300 + 0
        assert metrics.gross_profit == pytest.approx(500.0, abs=1e-6)  # 500 + 0
        assert metrics.gross_loss == pytest.approx(300.0, abs=1e-6)
        
        # Ratios
        assert metrics.total_trades == 3
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
        assert metrics.breakeven_trades == 1
        assert abs(metrics.win_rate - 33.33) < 0.1  # 1/3 * 100
        assert abs(metrics.profit_factor - 1.67) < 0.1  # 500/300
        assert abs(metrics.expectancy - 66.67) < 0.2  # 200/3
    
    def test_empty_trades_handling(self, analyzer):
        """Test handling of empty trade lists."""
        trades = analyzer.get_trades()
        assert len(trades) == 0
        
        metrics = analyzer.calculate_performance_metrics(trades)
        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.profit_factor == 0.0


class TestRiskAnalyzer:
    """Test the risk analytics engine."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def analyzer(self, temp_dir):
        """Create analyzer instance for testing."""
        return TradeAnalyzer(log_dir=temp_dir)
    
    @pytest.fixture
    def risk_analyzer(self, analyzer):
        """Create risk analyzer instance."""
        return RiskAnalyzer(analyzer)
    
    @pytest.fixture
    def drawdown_trades(self):
        """Create trades that simulate a drawdown scenario."""
        base_time = datetime.now(timezone.utc)
        
        trades = [
            # Initial winning trades
            Trade("AAPL", "test", base_time, base_time + timedelta(hours=1),
                  100.0, 105.0, 100, "buy", 500.0, 5.0),
            Trade("MSFT", "test", base_time + timedelta(hours=2), base_time + timedelta(hours=3),
                  200.0, 210.0, 50, "buy", 500.0, 5.0),
            
            # Drawdown period - series of losses
            Trade("GOOGL", "test", base_time + timedelta(hours=4), base_time + timedelta(hours=5),
                  300.0, 285.0, 30, "buy", -450.0, -5.0),
            Trade("TSLA", "test", base_time + timedelta(hours=6), base_time + timedelta(hours=7),
                  400.0, 380.0, 25, "buy", -500.0, -5.0),
            Trade("NVDA", "test", base_time + timedelta(hours=8), base_time + timedelta(hours=9),
                  500.0, 475.0, 20, "buy", -500.0, -5.0),
            
            # Recovery
            Trade("META", "test", base_time + timedelta(hours=10), base_time + timedelta(hours=11),
                  250.0, 275.0, 40, "buy", 1000.0, 10.0),
        ]
        return trades
    
    def test_drawdown_analysis(self, risk_analyzer, drawdown_trades):
        """Test drawdown period identification."""
        drawdown_periods = risk_analyzer.analyze_drawdowns(drawdown_trades, initial_capital=100000)
        
        # Should identify at least one drawdown period
        assert len(drawdown_periods) >= 1
        
        # Check drawdown calculations
        main_drawdown = drawdown_periods[0]
        assert main_drawdown.drawdown_amount > 0
        assert main_drawdown.drawdown_percent > 0
        assert main_drawdown.trades_in_drawdown > 0
    
    def test_risk_metrics_calculation(self, risk_analyzer, drawdown_trades):
        """Test comprehensive risk metrics calculation."""
        risk_metrics = risk_analyzer.calculate_comprehensive_risk_metrics(drawdown_trades)
        
        # Check that metrics are calculated
        assert risk_metrics.max_drawdown_absolute >= 0
        assert risk_metrics.max_drawdown_percent >= 0
        assert risk_metrics.daily_volatility >= 0
        assert risk_metrics.annual_volatility >= 0
        
        # Risk-adjusted returns should be calculated
        assert isinstance(risk_metrics.sharpe_ratio, float)
        assert isinstance(risk_metrics.sortino_ratio, float)
    
    def test_var_calculation(self, risk_analyzer):
        """Test Value at Risk calculation."""
        # Create sample returns
        returns = [-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.03, 0.04, -0.01, 0.01]
        
        var_95, var_99, cvar_95 = risk_analyzer.calculate_var_metrics(returns)
        
        # VaR should be negative (indicating potential losses)
        assert var_95 <= 0
        assert var_99 <= var_95  # 99% VaR should be worse than 95% VaR
        assert cvar_95 <= var_95  # Conditional VaR should be worse than VaR
    
    def test_portfolio_heat_calculation(self, risk_analyzer, drawdown_trades):
        """Test portfolio heat calculation."""
        current_heat, max_heat, avg_heat = risk_analyzer.calculate_portfolio_heat(drawdown_trades)
        
        assert current_heat >= 0
        assert max_heat >= current_heat
        assert avg_heat >= 0
        assert max_heat <= 100  # Heat should be percentage


class TestExecutionAnalyzer:
    """Test the execution analytics engine."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def analyzer(self, temp_dir):
        """Create analyzer instance for testing."""
        return TradeAnalyzer(log_dir=temp_dir)
    
    @pytest.fixture
    def execution_analyzer(self, analyzer):
        """Create execution analyzer instance."""
        return ExecutionAnalyzer(analyzer)
    
    @pytest.fixture
    def slippage_trades(self):
        """Create trades with various slippage scenarios."""
        base_time = datetime.now(timezone.utc).replace(hour=10, minute=0)  # Market hours
        
        trades = [
            # Good execution (positive slippage)
            Trade("AAPL", "test", base_time, base_time + timedelta(hours=1),
                  100.0, 101.0, 100, "buy", 100.0, 1.0, slippage=0.02),
            
            # Poor execution (negative slippage)
            Trade("MSFT", "test", base_time + timedelta(hours=1), base_time + timedelta(hours=2),
                  200.0, 202.0, 50, "buy", 100.0, 1.0, slippage=-0.05),
            
            # Market open trade (typically higher slippage)
            Trade("GOOGL", "test", base_time.replace(hour=9, minute=30), 
                  base_time.replace(hour=9, minute=45),
                  300.0, 303.0, 30, "buy", 90.0, 1.0, slippage=-0.03),
            
            # Market close trade
            Trade("TSLA", "test", base_time.replace(hour=15, minute=45),
                  base_time.replace(hour=16, minute=0),
                  400.0, 404.0, 25, "buy", 100.0, 1.0, slippage=-0.02),
        ]
        return trades
    
    def test_slippage_calculation(self, execution_analyzer):
        """Test slippage calculation logic."""
        # Buy order - negative slippage when paying more
        slippage = execution_analyzer.calculate_slippage(100.0, 100.05, "buy")
        assert slippage == pytest.approx(-0.05, abs=1e-6)
        
        # Sell order - negative slippage when receiving less
        slippage = execution_analyzer.calculate_slippage(100.0, 99.95, "sell")
        assert slippage == pytest.approx(-0.05, abs=1e-6)
        
        # Positive slippage scenarios
        slippage = execution_analyzer.calculate_slippage(100.0, 99.95, "buy")
        assert slippage == pytest.approx(0.05, abs=1e-6)
    
    def test_time_classification(self, execution_analyzer):
        """Test time of day classification."""
        # Market open
        market_open = datetime.now().replace(hour=9, minute=45)
        assert execution_analyzer.classify_time_of_day(market_open) == TimeOfDay.MARKET_OPEN
        
        # Morning
        morning = datetime.now().replace(hour=11, minute=0)
        assert execution_analyzer.classify_time_of_day(morning) == TimeOfDay.MORNING
        
        # Market close
        market_close = datetime.now().replace(hour=15, minute=45)
        assert execution_analyzer.classify_time_of_day(market_close) == TimeOfDay.MARKET_CLOSE
    
    def test_execution_metrics_calculation(self, execution_analyzer, slippage_trades):
        """Test comprehensive execution metrics calculation."""
        metrics = execution_analyzer.calculate_comprehensive_execution_metrics(slippage_trades)
        
        # Basic slippage metrics
        assert isinstance(metrics.avg_slippage, float)
        assert isinstance(metrics.median_slippage, float)
        assert isinstance(metrics.slippage_std, float)
        assert 0 <= metrics.positive_slippage_rate <= 100
        
        # Execution quality metrics
        assert metrics.avg_fill_time > 0
        assert 0 <= metrics.fill_rate <= 100
        assert metrics.avg_market_impact >= 0
    
    def test_slippage_by_symbol_analysis(self, execution_analyzer, slippage_trades):
        """Test symbol-specific slippage analysis."""
        slippage_breakdown = execution_analyzer.analyze_slippage_by_symbol(slippage_trades)
        
        # Should have breakdown for each symbol
        symbols = set(trade.symbol for trade in slippage_trades)
        for symbol in symbols:
            assert symbol in slippage_breakdown
            breakdown = slippage_breakdown[symbol]
            assert breakdown.total_trades > 0
            assert isinstance(breakdown.avg_slippage, float)


class TestStrategyOptimizer:
    """Test the strategy optimization engine."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def analyzer(self, temp_dir):
        """Create analyzer instance for testing."""
        return TradeAnalyzer(log_dir=temp_dir)
    
    @pytest.fixture
    def optimizer(self, analyzer):
        """Create strategy optimizer instance."""
        return StrategyOptimizer(analyzer)
    
    @pytest.fixture
    def strategy_trades(self):
        """Create trades for strategy analysis."""
        base_time = datetime.now(timezone.utc)
        
        # Create a strategy with clear weaknesses for optimization
        trades = []
        
        # Poor win rate strategy
        for i in range(20):
            entry_time = base_time + timedelta(hours=i)
            exit_time = entry_time + timedelta(hours=1)
            
            # 30% win rate with poor risk/reward
            if i < 6:  # 6 winners out of 20
                pnl = 50.0  # Small wins
            else:  # 14 losers
                pnl = -100.0  # Large losses
            
            trade = Trade(
                symbol=f"STOCK{i % 5}",  # 5 different symbols
                strategy="poor_strategy",
                entry_time=entry_time,
                exit_time=exit_time,
                entry_price=100.0,
                exit_price=100.0 + (pnl / 100),
                quantity=100,
                side="buy",
                pnl=pnl,
                pnl_percent=pnl / 100,
                slippage=-0.02 if pnl < 0 else 0.01  # Poor execution on losses
            )
            trades.append(trade)
        
        return trades
    
    def test_strategy_analysis(self, optimizer, strategy_trades):
        """Test strategy performance analysis."""
        analysis = optimizer.analyze_strategy_performance(strategy_trades, "poor_strategy")
        
        assert analysis.strategy_name == "poor_strategy"
        assert analysis.total_trades == len(strategy_trades)
        assert analysis.performance_score < 50  # Should be low due to poor performance
        assert analysis.optimization_potential > 0  # Should have improvement potential
        
        # Should identify weaknesses
        assert len(analysis.weaknesses) > 0
        
        # Should have symbol performance data
        assert len(analysis.best_performing_symbols) >= 0
        assert len(analysis.worst_performing_symbols) >= 0
    
    def test_optimization_recommendations(self, optimizer, strategy_trades):
        """Test optimization recommendation generation."""
        recommendations = optimizer.generate_optimization_recommendations(strategy_trades)
        
        # Should generate recommendations for poor strategy
        assert len(recommendations) > 0
        
        # Check recommendation structure
        for rec in recommendations:
            assert hasattr(rec, 'category')
            assert hasattr(rec, 'priority')
            assert hasattr(rec, 'title')
            assert hasattr(rec, 'description')
            assert hasattr(rec, 'specific_actions')
            assert rec.priority in ['high', 'medium', 'low']
    
    def test_performance_score_calculation(self, optimizer):
        """Test performance score calculation."""
        # Create metrics for a good strategy
        from daybot_mcp.analytics import PerformanceMetrics
        
        good_metrics = PerformanceMetrics(
            total_trades=100,
            winning_trades=70,
            win_rate=70.0,
            profit_factor=2.5,
            expectancy=150.0,
            max_drawdown_percent=8.0,
            sharpe_ratio=1.8
        )
        
        score = optimizer._calculate_performance_score(good_metrics)
        assert score > 70  # Should be high score
        
        # Create metrics for a poor strategy
        poor_metrics = PerformanceMetrics(
            total_trades=100,
            winning_trades=30,
            win_rate=30.0,
            profit_factor=0.8,
            expectancy=-50.0,
            max_drawdown_percent=35.0,
            sharpe_ratio=-0.5
        )
        
        score = optimizer._calculate_performance_score(poor_metrics)
        assert score < 30  # Should be low score
    
    def test_optimization_report_generation(self, optimizer, strategy_trades):
        """Test comprehensive optimization report generation."""
        report = optimizer.generate_optimization_report(strategy_trades)
        
        # Check report structure
        assert "summary" in report
        assert "by_priority" in report
        assert "by_category" in report
        assert "implementation_roadmap" in report
        
        # Check summary
        summary = report["summary"]
        assert "total_recommendations" in summary
        assert "high_priority" in summary
        assert "estimated_total_improvement" in summary
        
        # Check roadmap
        roadmap = report["implementation_roadmap"]
        assert "immediate" in roadmap
        assert "short_term" in roadmap
        assert "long_term" in roadmap


class TestIntegration:
    """Integration tests for the complete analytics system."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_end_to_end_analytics_workflow(self, temp_dir):
        """Test complete analytics workflow from trades to recommendations."""
        # Initialize system
        analyzer = TradeAnalyzer(log_dir=temp_dir)
        risk_analyzer = RiskAnalyzer(analyzer)
        execution_analyzer = ExecutionAnalyzer(analyzer)
        optimizer = StrategyOptimizer(analyzer)
        
        # Create comprehensive test data
        base_time = datetime.now(timezone.utc)
        trades = []
        
        for i in range(50):
            # Mix of winning and losing trades across multiple strategies
            strategy = ["momentum", "mean_reversion", "breakout"][i % 3]
            symbol = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"][i % 5]
            
            # 60% win rate overall
            is_winner = i % 5 < 3
            pnl = 100.0 if is_winner else -80.0
            
            trade = Trade(
                symbol=symbol,
                strategy=strategy,
                entry_time=base_time + timedelta(hours=i),
                exit_time=base_time + timedelta(hours=i+1),
                entry_price=100.0,
                exit_price=100.0 + (pnl / 100),
                quantity=100,
                side="buy",
                pnl=pnl,
                pnl_percent=pnl / 100,
                commission=1.0,
                slippage=0.01 if is_winner else -0.02
            )
            trades.append(trade)
            analyzer.add_trade(trade)
        
        # Test performance analytics
        all_trades = analyzer.get_trades()
        assert len(all_trades) == 50
        
        performance_metrics = analyzer.calculate_performance_metrics(all_trades)
        assert performance_metrics.total_trades == 50
        assert 50 <= performance_metrics.win_rate <= 70  # Should be around 60%
        
        # Test risk analytics
        risk_report = risk_analyzer.generate_risk_report(all_trades)
        assert "drawdown_analysis" in risk_report
        assert "risk_adjusted_returns" in risk_report
        
        # Test execution analytics
        execution_report = execution_analyzer.generate_execution_report(all_trades)
        assert "summary" in execution_report
        assert "slippage_analysis" in execution_report
        
        # Test optimization
        optimization_report = optimizer.generate_optimization_report(all_trades)
        assert "summary" in optimization_report
        assert "by_priority" in optimization_report
        
        # Verify recommendations are generated
        assert optimization_report["summary"]["total_recommendations"] > 0


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
