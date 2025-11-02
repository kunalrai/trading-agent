// Trading Dashboard JavaScript
class TradingDashboard {
    constructor() {
        this.portfolioChart = null;
        this.isTrading = false;
        this.updateInterval = null;
        this.currentChartType = 'portfolio';
        this.currentTimePeriod = '24h';
        
        this.init();
    }

    init() {
        this.initChart();
        this.bindEvents();
        this.loadInitialData();
        this.startPeriodicUpdates();
    }

    // Initialize Chart.js
    initChart() {
        const canvas = document.getElementById('portfolioChart');
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.portfolioChart) {
            this.portfolioChart.destroy();
        }
        
        this.portfolioChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Portfolio Value',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 41, 59, 0.95)',
                        titleColor: '#ffffff',
                        bodyColor: '#e2e8f0',
                        borderColor: '#334155',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false,
                        callbacks: {
                            title: function(context) {
                                const timestamp = context[0].parsed.x;
                                return new Date(timestamp).toLocaleString();
                            },
                            label: function(context) {
                                return `$${context.parsed.y.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        grid: {
                            color: '#334155',
                            borderColor: '#475569'
                        },
                        ticks: {
                            color: '#94a3b8',
                            maxTicksLimit: 8,
                            callback: function(value, index, values) {
                                // Simple time formatting for now
                                return new Date(value).toLocaleTimeString('en-US', { 
                                    hour: '2-digit', 
                                    minute: '2-digit' 
                                });
                            }
                        }
                    },
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: '#334155',
                            borderColor: '#475569'
                        },
                        ticks: {
                            color: '#94a3b8',
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    // Bind event listeners
    bindEvents() {
        // Time period selectors
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentTimePeriod = e.target.dataset.period;
                this.updateChart();
            });
        });

        // Chart type selectors
        document.querySelectorAll('.chart-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentChartType = e.target.dataset.chart;
                this.updateChartType();
            });
        });

        // Control buttons
        document.getElementById('start-trading').addEventListener('click', () => this.startTrading());
        document.getElementById('stop-trading').addEventListener('click', () => this.stopTrading());
        document.getElementById('refresh-data').addEventListener('click', () => this.refreshData());
        document.getElementById('reset-portfolio').addEventListener('click', () => this.resetPortfolio());
        document.getElementById('export-trades').addEventListener('click', () => this.exportTrades());

        // Close position buttons (delegated event)
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('close-position-btn')) {
                const tradeId = e.target.dataset.tradeId;
                this.closePosition(tradeId);
            }
        });
    }

    // Load initial data
    async loadInitialData() {
        try {
            await Promise.all([
                this.updatePortfolioData().catch(() => this.loadSamplePortfolioData()),
                this.updateOpenPositions().catch(() => this.loadSamplePositions()),
                this.updateTradeHistory().catch(() => this.loadSampleTrades()),
                this.updateMarketAnalysis().catch(() => this.loadSampleAnalysis()),
                this.updateChart().catch(() => this.loadSampleChartData())
            ]);
            this.updateStatus('connected');
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.updateStatus('disconnected');
            this.loadAllSampleData();
        }
    }
    
    // Load sample data when API is not available
    loadAllSampleData() {
        this.loadSamplePortfolioData();
        this.loadSamplePositions();
        this.loadSampleTrades();
        this.loadSampleAnalysis();
        this.loadSampleChartData();
    }
    
    loadSamplePortfolioData() {
        document.getElementById('portfolio-value').textContent = '$1,047.23';
        document.getElementById('cash-balance').textContent = '$850.15';
        document.getElementById('unrealized-pnl').textContent = '$12.45';
        document.getElementById('max-drawdown').textContent = '3.2%';
        
        document.getElementById('total-pnl').textContent = '$47.23';
        document.getElementById('win-rate').textContent = '65%';
        document.getElementById('active-trades').textContent = '2';
        
        const changeElement = document.getElementById('portfolio-change');
        changeElement.textContent = '+4.72%';
        changeElement.className = 'stat-change positive';
    }
    
    loadSamplePositions() {
        const tbody = document.getElementById('positions-tbody');
        tbody.innerHTML = `
            <tr>
                <td>ZEC/USDT</td>
                <td><span class="signal-type LONG">LONG</span></td>
                <td>$412.30</td>
                <td>$415.67</td>
                <td>0.2430</td>
                <td class="pnl-positive">+$8.19</td>
                <td><button class="action-btn close-position-btn" data-trade-id="sample1">Close</button></td>
            </tr>
            <tr>
                <td>ZEC/USDT</td>
                <td><span class="signal-type SHORT">SHORT</span></td>
                <td>$418.90</td>
                <td>$416.23</td>
                <td>0.1850</td>
                <td class="pnl-positive">+$4.94</td>
                <td><button class="action-btn close-position-btn" data-trade-id="sample2">Close</button></td>
            </tr>
        `;
        document.getElementById('positions-count').textContent = '2 positions';
    }
    
    loadSampleTrades() {
        const tbody = document.getElementById('trades-tbody');
        tbody.innerHTML = `
            <tr>
                <td>Nov 02</td>
                <td>ZEC/USDT</td>
                <td><span class="signal-type LONG">LONG</span></td>
                <td>$408.50</td>
                <td>$412.30</td>
                <td class="pnl-positive">+$9.22</td>
                <td>CLOSED</td>
            </tr>
            <tr>
                <td>Nov 02</td>
                <td>ZEC/USDT</td>
                <td><span class="signal-type SHORT">SHORT</span></td>
                <td>$420.15</td>
                <td>$416.80</td>
                <td class="pnl-positive">+$8.18</td>
                <td>CLOSED</td>
            </tr>
            <tr>
                <td>Nov 01</td>
                <td>ZEC/USDT</td>
                <td><span class="signal-type LONG">LONG</span></td>
                <td>$405.20</td>
                <td>$403.45</td>
                <td class="pnl-negative">-$4.27</td>
                <td>STOPPED</td>
            </tr>
        `;
    }
    
    loadSampleAnalysis() {
        document.getElementById('current-signal').innerHTML = `
            <span class="signal-type LONG">LONG</span>
            <span class="signal-confidence">High (75%)</span>
        `;
        
        const trendIntraday = document.getElementById('trend-intraday');
        const trend4h = document.getElementById('trend-4h');
        
        trendIntraday.textContent = 'Bullish';
        trendIntraday.className = 'trend-value bullish';
        
        trend4h.textContent = 'Bullish';
        trend4h.className = 'trend-value bullish';
        
        document.getElementById('current-price').textContent = '$415.67';
        document.getElementById('current-ema').textContent = '$412.45';
        document.getElementById('current-rsi').textContent = '68.5';
        document.getElementById('current-macd').textContent = '2.341';
        
        document.getElementById('support-level').textContent = '$410.20';
        document.getElementById('resistance-level').textContent = '$420.50';
        
        document.getElementById('trading-rationale').textContent = 
            'Strong bullish momentum with price above EMA50, positive MACD crossover, and RSI in healthy range. 4H trend alignment supports long bias.';
        
        document.getElementById('analysis-time').textContent = 
            `Last updated: ${new Date().toLocaleTimeString()}`;
    }

    // Start periodic updates
    startPeriodicUpdates() {
        this.updateInterval = setInterval(() => {
            this.loadInitialData();
        }, 30000); // Update every 30 seconds
    }

    // Update portfolio data
    async updatePortfolioData() {
        try {
            const response = await fetch('/api/portfolio');
            const data = await response.json();
            
            // Update portfolio stats
            document.getElementById('portfolio-value').textContent = this.formatCurrency(data.total_value);
            document.getElementById('cash-balance').textContent = this.formatCurrency(data.cash_balance);
            document.getElementById('unrealized-pnl').textContent = this.formatCurrency(data.unrealized_pnl);
            document.getElementById('max-drawdown').textContent = this.formatPercentage(data.max_drawdown);
            
            // Update header stats
            document.getElementById('total-pnl').textContent = this.formatCurrency(data.total_pnl);
            document.getElementById('win-rate').textContent = this.formatPercentage(data.win_rate);
            document.getElementById('active-trades').textContent = data.open_positions.toString();
            
            // Update portfolio change
            const changeElement = document.getElementById('portfolio-change');
            const changePercent = ((data.total_value - data.initial_balance) / data.initial_balance) * 100;
            changeElement.textContent = this.formatPercentage(changePercent, true);
            changeElement.className = `stat-change ${changePercent >= 0 ? 'positive' : 'negative'}`;
            
        } catch (error) {
            console.error('Error updating portfolio data:', error);
        }
    }

    // Update open positions
    async updateOpenPositions() {
        try {
            const response = await fetch('/api/positions');
            const positions = await response.json();
            
            const tbody = document.getElementById('positions-tbody');
            const countElement = document.getElementById('positions-count');
            
            countElement.textContent = `${positions.length} position${positions.length !== 1 ? 's' : ''}`;
            
            if (positions.length === 0) {
                tbody.innerHTML = '<tr class="no-data"><td colspan="7">No open positions</td></tr>';
                return;
            }
            
            tbody.innerHTML = positions.map(position => `
                <tr>
                    <td>${position.symbol}</td>
                    <td>
                        <span class="signal-type ${position.trade_type}">${position.trade_type}</span>
                    </td>
                    <td>${this.formatCurrency(position.entry_price)}</td>
                    <td>${this.formatCurrency(position.current_price || position.entry_price)}</td>
                    <td>${position.quantity.toFixed(4)}</td>
                    <td class="${this.getPnLClass(position.unrealized_pnl || 0)}">
                        ${this.formatCurrency(position.unrealized_pnl || 0, true)}
                    </td>
                    <td>
                        <button class="action-btn close-position-btn" data-trade-id="${position.id}">
                            Close
                        </button>
                    </td>
                </tr>
            `).join('');
            
        } catch (error) {
            console.error('Error updating open positions:', error);
        }
    }

    // Update trade history
    async updateTradeHistory() {
        try {
            const response = await fetch('/api/trades');
            const trades = await response.json();
            
            const tbody = document.getElementById('trades-tbody');
            
            if (trades.length === 0) {
                tbody.innerHTML = '<tr class="no-data"><td colspan="7">No trades yet</td></tr>';
                return;
            }
            
            tbody.innerHTML = trades.slice(0, 10).map(trade => `
                <tr>
                    <td>${new Date(trade.entry_time).toLocaleDateString()}</td>
                    <td>${trade.symbol}</td>
                    <td>
                        <span class="signal-type ${trade.trade_type}">${trade.trade_type}</span>
                    </td>
                    <td>${this.formatCurrency(trade.entry_price)}</td>
                    <td>${this.formatCurrency(trade.exit_price || 0)}</td>
                    <td class="${this.getPnLClass(trade.pnl)}">
                        ${this.formatCurrency(trade.pnl, true)}
                    </td>
                    <td>
                        <span class="status-${trade.status.toLowerCase()}">${trade.status}</span>
                    </td>
                </tr>
            `).join('');
            
        } catch (error) {
            console.error('Error updating trade history:', error);
        }
    }

    // Update market analysis
    async updateMarketAnalysis() {
        try {
            const response = await fetch('/api/analysis');
            const analysis = await response.json();
            
            // Update signal display
            document.getElementById('current-signal').innerHTML = `
                <span class="signal-type ${analysis.trade_type}">${analysis.trade_type}</span>
                <span class="signal-confidence">${analysis.confidence}</span>
            `;
            
            // Update trends
            const trendIntraday = document.getElementById('trend-intraday');
            const trend4h = document.getElementById('trend-4h');
            
            trendIntraday.textContent = this.capitalize(analysis.trend_intraday);
            trendIntraday.className = `trend-value ${analysis.trend_intraday}`;
            
            trend4h.textContent = this.capitalize(analysis.trend_4h);
            trend4h.className = `trend-value ${analysis.trend_4h}`;
            
            // Update technical indicators
            document.getElementById('current-price').textContent = this.formatCurrency(analysis.current_price);
            document.getElementById('current-ema').textContent = this.formatCurrency(analysis.ema);
            document.getElementById('current-rsi').textContent = analysis.rsi.toFixed(1);
            document.getElementById('current-macd').textContent = analysis.macd.toFixed(3);
            
            // Update key levels
            document.getElementById('support-level').textContent = this.formatCurrency(analysis.support);
            document.getElementById('resistance-level').textContent = this.formatCurrency(analysis.resistance);
            
            // Update rationale
            document.getElementById('trading-rationale').textContent = analysis.rationale;
            
            // Update timestamp
            document.getElementById('analysis-time').textContent = 
                `Last updated: ${new Date(analysis.timestamp).toLocaleTimeString()}`;
                
        } catch (error) {
            console.error('Error updating market analysis:', error);
        }
    }

    // Update chart
    async updateChart() {
        try {
            const response = await fetch(`/api/chart-data?period=${this.currentTimePeriod}`);
            const data = await response.json();
            
            // Convert timestamps to numbers for Chart.js
            const chartData = data.timestamps.map((timestamp, index) => ({
                x: new Date(timestamp).getTime(),
                y: data.values[index]
            }));
            
            this.portfolioChart.data.labels = [];
            this.portfolioChart.data.datasets[0].data = chartData;
            this.portfolioChart.update('none');
            
        } catch (error) {
            console.error('Error updating chart:', error);
            // Fallback with sample data
            this.loadSampleChartData();
        }
    }
    
    // Load sample chart data for testing
    loadSampleChartData() {
        const now = new Date();
        const sampleData = [];
        
        for (let i = 23; i >= 0; i--) {
            const timestamp = new Date(now.getTime() - (i * 60 * 60 * 1000)); // Every hour
            const value = 1000 + (Math.random() * 100) - 50 + (23 - i) * 2; // Growing trend with noise
            
            sampleData.push({
                x: timestamp.getTime(),
                y: Math.max(900, value) // Keep above 900
            });
        }
        
        this.portfolioChart.data.labels = [];
        this.portfolioChart.data.datasets[0].data = sampleData;
        this.portfolioChart.update('none');
    }

    // Update chart type
    updateChartType() {
        if (this.currentChartType === 'portfolio') {
            this.portfolioChart.data.datasets[0].label = 'Portfolio Value';
            this.portfolioChart.data.datasets[0].borderColor = '#10b981';
            this.portfolioChart.data.datasets[0].backgroundColor = 'rgba(16, 185, 129, 0.1)';
        } else if (this.currentChartType === 'pnl') {
            this.portfolioChart.data.datasets[0].label = 'P&L';
            this.portfolioChart.data.datasets[0].borderColor = '#3b82f6';
            this.portfolioChart.data.datasets[0].backgroundColor = 'rgba(59, 130, 246, 0.1)';
        }
        
        this.updateChart();
    }

    // Trading controls
    async startTrading() {
        try {
            const response = await fetch('/api/start-trading', { method: 'POST' });
            if (response.ok) {
                this.isTrading = true;
                document.getElementById('start-trading').classList.add('hidden');
                document.getElementById('stop-trading').classList.remove('hidden');
                this.updateStatus('connected');
            }
        } catch (error) {
            console.error('Error starting trading:', error);
        }
    }

    async stopTrading() {
        try {
            const response = await fetch('/api/stop-trading', { method: 'POST' });
            if (response.ok) {
                this.isTrading = false;
                document.getElementById('stop-trading').classList.add('hidden');
                document.getElementById('start-trading').classList.remove('hidden');
                this.updateStatus('disconnected');
            }
        } catch (error) {
            console.error('Error stopping trading:', error);
        }
    }

    async refreshData() {
        const refreshBtn = document.getElementById('refresh-data');
        refreshBtn.classList.add('loading');
        
        try {
            await this.loadInitialData();
        } finally {
            refreshBtn.classList.remove('loading');
        }
    }

    async resetPortfolio() {
        if (confirm('Are you sure you want to reset your portfolio? This will close all positions and reset to $1000.')) {
            try {
                const response = await fetch('/api/reset-portfolio', { method: 'POST' });
                if (response.ok) {
                    await this.loadInitialData();
                }
            } catch (error) {
                console.error('Error resetting portfolio:', error);
            }
        }
    }

    async closePosition(tradeId) {
        if (confirm('Are you sure you want to close this position?')) {
            try {
                const response = await fetch(`/api/close-position/${tradeId}`, { method: 'POST' });
                if (response.ok) {
                    await Promise.all([
                        this.updatePortfolioData(),
                        this.updateOpenPositions(),
                        this.updateTradeHistory()
                    ]);
                }
            } catch (error) {
                console.error('Error closing position:', error);
            }
        }
    }

    async exportTrades() {
        try {
            const response = await fetch('/api/export-trades');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `trades_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error exporting trades:', error);
        }
    }

    // Update connection status
    updateStatus(status) {
        const statusElement = document.getElementById('status-indicator');
        const statusText = statusElement.querySelector('span');
        
        statusElement.className = `status-indicator ${status}`;
        statusText.textContent = status === 'connected' ? 'Connected' : 'Disconnected';
    }

    // Utility functions
    formatCurrency(amount, showSign = false) {
        const formatted = Math.abs(amount).toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        
        if (showSign && amount !== 0) {
            return (amount >= 0 ? '+' : '-') + formatted;
        }
        
        return formatted;
    }

    formatPercentage(value, showSign = false) {
        const formatted = Math.abs(value).toFixed(2) + '%';
        
        if (showSign && value !== 0) {
            return (value >= 0 ? '+' : '-') + formatted;
        }
        
        return formatted;
    }

    getPnLClass(pnl) {
        if (pnl > 0) return 'pnl-positive';
        if (pnl < 0) return 'pnl-negative';
        return 'pnl-neutral';
    }

    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
}

// Store dashboard instance globally
window.dashboard = null;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Prevent multiple instances
    if (window.dashboard) {
        return;
    }
    
    window.dashboard = new TradingDashboard();
});

// Handle page visibility changes to pause/resume updates
document.addEventListener('visibilitychange', () => {
    if (document.hidden && window.dashboard) {
        clearInterval(window.dashboard.updateInterval);
    } else if (!document.hidden && window.dashboard) {
        window.dashboard.startPeriodicUpdates();
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard && window.dashboard.portfolioChart) {
        window.dashboard.portfolioChart.destroy();
    }
});