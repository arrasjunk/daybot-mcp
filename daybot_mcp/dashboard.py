"""
Web-based performance dashboard for trading analytics.
Provides interactive visualization of trading performance metrics.
"""

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, List
import json
from datetime import datetime, timedelta
from pathlib import Path

from .analytics import (
    TradeAnalyzer, PerformanceDashboard, AnalyticsPeriod,
    get_analytics_engine, initialize_analytics
)

# Initialize dashboard
dashboard_app = FastAPI(title="DayBot Performance Dashboard", version="1.0.0")

# Setup templates and static files
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))
dashboard_app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@dashboard_app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@dashboard_app.get("/api/performance")
async def get_performance_data(
    period: AnalyticsPeriod = Query(AnalyticsPeriod.ALL_TIME),
    strategy: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None)
):
    """Get performance metrics for the dashboard."""
    try:
        analyzer = get_analytics_engine()
        dashboard = PerformanceDashboard(analyzer)
        
        report = dashboard.generate_performance_report(
            period=period,
            strategy=strategy,
            symbol=symbol
        )
        
        return JSONResponse(content=report)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_app.get("/api/trades")
async def get_trades_data(
    limit: int = Query(100, le=1000),
    symbol: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None)
):
    """Get recent trades data."""
    try:
        analyzer = get_analytics_engine()
        trades = analyzer.get_trades(
            limit=limit,
            symbol=symbol,
            strategy=strategy
        )
        
        trades_data = []
        for trade in trades:
            trades_data.append({
                "symbol": trade.symbol,
                "strategy": trade.strategy,
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat(),
                "pnl": trade.pnl,
                "pnl_percent": trade.pnl_percent,
                "duration": trade.duration_minutes,
                "outcome": trade.outcome.value
            })
        
        return JSONResponse(content={"trades": trades_data})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_app.post("/api/sync-logs")
async def sync_log_data():
    """Sync trade data from log files."""
    try:
        analyzer = get_analytics_engine()
        trades_added = analyzer.parse_log_files()
        
        return JSONResponse(content={
            "success": True,
            "trades_added": trades_added,
            "message": f"Successfully synced {trades_added} trades from log files"
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Create dashboard HTML template
dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DayBot Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .metric-card { @apply bg-white rounded-lg shadow-md p-6 border-l-4; }
        .metric-positive { @apply border-green-500; }
        .metric-negative { @apply border-red-500; }
        .metric-neutral { @apply border-blue-500; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">DayBot Performance Dashboard</h1>
            <p class="text-gray-600">Real-time trading performance analytics and insights</p>
        </div>

        <!-- Controls -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-8">
            <div class="flex flex-wrap gap-4 items-center">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Period</label>
                    <select id="periodSelect" class="border border-gray-300 rounded-md px-3 py-2">
                        <option value="all_time">All Time</option>
                        <option value="yearly">Last Year</option>
                        <option value="quarterly">Last Quarter</option>
                        <option value="monthly">Last Month</option>
                        <option value="weekly">Last Week</option>
                        <option value="daily">Today</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Strategy</label>
                    <select id="strategySelect" class="border border-gray-300 rounded-md px-3 py-2">
                        <option value="">All Strategies</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Symbol</label>
                    <input type="text" id="symbolInput" placeholder="e.g., AAPL" 
                           class="border border-gray-300 rounded-md px-3 py-2">
                </div>
                <div class="flex gap-2 mt-6">
                    <button id="refreshBtn" class="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600">
                        Refresh
                    </button>
                    <button id="syncBtn" class="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600">
                        Sync Logs
                    </button>
                </div>
            </div>
        </div>

        <!-- Key Metrics -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="metric-card metric-neutral">
                <h3 class="text-lg font-semibold text-gray-700 mb-2">Total Trades</h3>
                <p id="totalTrades" class="text-3xl font-bold text-blue-600">-</p>
            </div>
            <div class="metric-card metric-positive">
                <h3 class="text-lg font-semibold text-gray-700 mb-2">Win Rate</h3>
                <p id="winRate" class="text-3xl font-bold text-green-600">-</p>
            </div>
            <div class="metric-card metric-positive">
                <h3 class="text-lg font-semibold text-gray-700 mb-2">Net Profit</h3>
                <p id="netProfit" class="text-3xl font-bold text-green-600">-</p>
            </div>
            <div class="metric-card metric-negative">
                <h3 class="text-lg font-semibold text-gray-700 mb-2">Max Drawdown</h3>
                <p id="maxDrawdown" class="text-3xl font-bold text-red-600">-</p>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h3 class="text-lg font-semibold text-gray-700 mb-4">P&L Distribution</h3>
                <canvas id="pnlChart"></canvas>
            </div>
            <div class="bg-white rounded-lg shadow-md p-6">
                <h3 class="text-lg font-semibold text-gray-700 mb-4">Performance by Strategy</h3>
                <canvas id="strategyChart"></canvas>
            </div>
        </div>

        <!-- Detailed Metrics -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h3 class="text-lg font-semibold text-gray-700 mb-4">Risk Metrics</h3>
                <div id="riskMetrics" class="space-y-3">
                    <!-- Risk metrics will be populated here -->
                </div>
            </div>
            <div class="bg-white rounded-lg shadow-md p-6">
                <h3 class="text-lg font-semibold text-gray-700 mb-4">Execution Quality</h3>
                <div id="executionMetrics" class="space-y-3">
                    <!-- Execution metrics will be populated here -->
                </div>
            </div>
        </div>

        <!-- Recommendations -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-8">
            <h3 class="text-lg font-semibold text-gray-700 mb-4">Optimization Recommendations</h3>
            <div id="recommendations" class="space-y-2">
                <!-- Recommendations will be populated here -->
            </div>
        </div>

        <!-- Recent Trades -->
        <div class="bg-white rounded-lg shadow-md p-6">
            <h3 class="text-lg font-semibold text-gray-700 mb-4">Recent Trades</h3>
            <div class="overflow-x-auto">
                <table class="min-w-full table-auto">
                    <thead>
                        <tr class="bg-gray-50">
                            <th class="px-4 py-2 text-left">Symbol</th>
                            <th class="px-4 py-2 text-left">Strategy</th>
                            <th class="px-4 py-2 text-left">Entry Time</th>
                            <th class="px-4 py-2 text-left">Duration</th>
                            <th class="px-4 py-2 text-left">P&L</th>
                            <th class="px-4 py-2 text-left">P&L %</th>
                            <th class="px-4 py-2 text-left">Outcome</th>
                        </tr>
                    </thead>
                    <tbody id="tradesTable">
                        <!-- Trades will be populated here -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // Dashboard JavaScript
        let pnlChart, strategyChart;

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initializeCharts();
            loadDashboardData();
            
            // Event listeners
            document.getElementById('refreshBtn').addEventListener('click', loadDashboardData);
            document.getElementById('syncBtn').addEventListener('click', syncLogData);
            document.getElementById('periodSelect').addEventListener('change', loadDashboardData);
        });

        function initializeCharts() {
            // P&L Distribution Chart
            const pnlCtx = document.getElementById('pnlChart').getContext('2d');
            pnlChart = new Chart(pnlCtx, {
                type: 'bar',
                data: {
                    labels: ['Wins', 'Losses', 'Breakeven'],
                    datasets: [{
                        label: 'Trade Count',
                        data: [0, 0, 0],
                        backgroundColor: ['#10B981', '#EF4444', '#6B7280']
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

            // Strategy Performance Chart
            const strategyCtx = document.getElementById('strategyChart').getContext('2d');
            strategyChart = new Chart(strategyCtx, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444']
                    }]
                },
                options: {
                    responsive: true
                }
            });
        }

        async function loadDashboardData() {
            try {
                const period = document.getElementById('periodSelect').value;
                const strategy = document.getElementById('strategySelect').value;
                const symbol = document.getElementById('symbolInput').value;

                const params = new URLSearchParams({ period });
                if (strategy) params.append('strategy', strategy);
                if (symbol) params.append('symbol', symbol);

                const response = await fetch(`/api/performance?${params}`);
                const data = await response.json();

                updateMetrics(data);
                updateCharts(data);
                updateDetailedMetrics(data);
                updateRecommendations(data);
                
                await loadTradesData();
            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }
        }

        function updateMetrics(data) {
            const summary = data.summary;
            document.getElementById('totalTrades').textContent = summary.total_trades;
            document.getElementById('winRate').textContent = summary.win_rate;
            document.getElementById('netProfit').textContent = summary.net_profit;
            document.getElementById('maxDrawdown').textContent = summary.max_drawdown;
        }

        function updateCharts(data) {
            const detailed = data.detailed_metrics;
            
            // Update P&L chart
            pnlChart.data.datasets[0].data = [
                detailed.trade_distribution.winning_trades,
                detailed.trade_distribution.losing_trades,
                detailed.trade_distribution.breakeven_trades
            ];
            pnlChart.update();

            // Update strategy chart
            const strategies = data.trade_analysis.by_strategy || {};
            strategyChart.data.labels = Object.keys(strategies);
            strategyChart.data.datasets[0].data = Object.values(strategies).map(s => s.count);
            strategyChart.update();
        }

        function updateDetailedMetrics(data) {
            const risk = data.detailed_metrics.risk_metrics;
            const execution = data.detailed_metrics.execution_quality;

            document.getElementById('riskMetrics').innerHTML = `
                <div class="flex justify-between"><span>Sharpe Ratio:</span><span>${data.summary.sharpe_ratio}</span></div>
                <div class="flex justify-between"><span>Sortino Ratio:</span><span>${risk.sortino_ratio}</span></div>
                <div class="flex justify-between"><span>Recovery Factor:</span><span>${risk.recovery_factor}</span></div>
                <div class="flex justify-between"><span>Kelly Criterion:</span><span>${data.detailed_metrics.kelly_criterion}</span></div>
            `;

            document.getElementById('executionMetrics').innerHTML = `
                <div class="flex justify-between"><span>Avg Slippage:</span><span>${execution.avg_slippage}</span></div>
                <div class="flex justify-between"><span>Total Commission:</span><span>${execution.total_commission}</span></div>
                <div class="flex justify-between"><span>Avg Duration:</span><span>${execution.avg_trade_duration}</span></div>
                <div class="flex justify-between"><span>Max Consecutive Wins:</span><span>${data.detailed_metrics.streaks.max_consecutive_wins}</span></div>
            `;
        }

        function updateRecommendations(data) {
            const recommendations = data.recommendations || [];
            const container = document.getElementById('recommendations');
            
            if (recommendations.length === 0) {
                container.innerHTML = '<p class="text-gray-500">No specific recommendations at this time.</p>';
                return;
            }

            container.innerHTML = recommendations.map(rec => 
                `<div class="p-3 bg-gray-50 rounded-md">${rec}</div>`
            ).join('');
        }

        async function loadTradesData() {
            try {
                const response = await fetch('/api/trades?limit=50');
                const data = await response.json();
                
                const tbody = document.getElementById('tradesTable');
                tbody.innerHTML = data.trades.map(trade => `
                    <tr class="border-b">
                        <td class="px-4 py-2">${trade.symbol}</td>
                        <td class="px-4 py-2">${trade.strategy}</td>
                        <td class="px-4 py-2">${new Date(trade.entry_time).toLocaleString()}</td>
                        <td class="px-4 py-2">${trade.duration}m</td>
                        <td class="px-4 py-2 ${trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'}">
                            $${trade.pnl.toFixed(2)}
                        </td>
                        <td class="px-4 py-2 ${trade.pnl_percent >= 0 ? 'text-green-600' : 'text-red-600'}">
                            ${trade.pnl_percent.toFixed(2)}%
                        </td>
                        <td class="px-4 py-2">
                            <span class="px-2 py-1 rounded text-sm ${
                                trade.outcome === 'win' ? 'bg-green-100 text-green-800' :
                                trade.outcome === 'loss' ? 'bg-red-100 text-red-800' :
                                'bg-gray-100 text-gray-800'
                            }">${trade.outcome}</span>
                        </td>
                    </tr>
                `).join('');
            } catch (error) {
                console.error('Error loading trades data:', error);
            }
        }

        async function syncLogData() {
            try {
                const btn = document.getElementById('syncBtn');
                btn.textContent = 'Syncing...';
                btn.disabled = true;

                const response = await fetch('/api/sync-logs', { method: 'POST' });
                const data = await response.json();

                if (data.success) {
                    alert(`Successfully synced ${data.trades_added} trades from log files`);
                    loadDashboardData();
                } else {
                    alert('Error syncing log data');
                }
            } catch (error) {
                console.error('Error syncing logs:', error);
                alert('Error syncing log data');
            } finally {
                const btn = document.getElementById('syncBtn');
                btn.textContent = 'Sync Logs';
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>'''

# Write the dashboard template
def create_dashboard_template():
    """Create the dashboard HTML template."""
    template_path = templates_dir / "dashboard.html"
    with open(template_path, 'w') as f:
        f.write(dashboard_html)

# Initialize template on import
create_dashboard_template()
