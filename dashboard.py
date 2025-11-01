#!/usr/bin/env python3
"""
Real-time Trading Dashboard
Web-based monitoring dashboard for trading signals
"""

from flask import Flask, render_template, jsonify
from datetime import datetime
import json
import threading
import time
from ema9_api import EMA9API


app = Flask(__name__)

# Global variables for real-time data
current_data = {}
signal_history = []
last_update = None
monitor_thread = None
monitoring = False


class DashboardMonitor:
    """Background monitoring for dashboard"""
    
    def __init__(self):
        self.api = EMA9API()
        self.running = False
    
    def update_data(self):
        """Update current market data and signals"""
        global current_data, signal_history, last_update
        
        try:
            # Get comprehensive data
            data = self.api.get_ema9_data()
            signal = self.api.get_trading_signal()
            
            current_data = {
                'timestamp': datetime.now().isoformat(),
                'price': data.get('current_price', 0),
                'ema20': data.get('current_ema20', 0),
                'macd': data.get('current_macd', 0),
                'rsi7': data.get('current_rsi7', 0),
                'rsi14': data.get('current_rsi14', 0),
                'signal_direction': signal.get('signal_direction', 'HOLD'),
                'confidence': signal.get('confidence', 0),
                'signal_strength': signal.get('signal_strength', 0),
                'entry_price': signal.get('entry_price'),
                'stop_loss': signal.get('stop_loss'),
                'take_profit_1': signal.get('take_profit_1'),
                'take_profit_2': signal.get('take_profit_2'),
                'take_profit_3': signal.get('take_profit_3'),
                'position_size_pct': signal.get('position_size_pct', 0),
                'signal_factors': signal.get('signal_factors', [])
            }
            
            # Add to history if signal changed
            if (not signal_history or 
                signal_history[-1].get('signal_direction') != current_data['signal_direction']):
                
                signal_history.append(current_data.copy())
                # Keep only last 50 signals
                if len(signal_history) > 50:
                    signal_history.pop(0)
            
            last_update = datetime.now()
            
        except Exception as e:
            print(f"Error updating data: {str(e)}")
    
    def run(self):
        """Run continuous monitoring"""
        self.running = True
        
        while self.running:
            self.update_data()
            time.sleep(60)  # Update every minute
    
    def stop(self):
        """Stop monitoring"""
        self.running = False


@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/data')
def get_data():
    """Get current market data"""
    return jsonify({
        'current_data': current_data,
        'signal_history': signal_history[-10:],  # Last 10 signals
        'last_update': last_update.isoformat() if last_update else None,
        'status': 'active' if monitoring else 'inactive'
    })


@app.route('/api/start_monitoring')
def start_monitoring():
    """Start background monitoring"""
    global monitor_thread, monitoring
    
    if not monitoring:
        monitor = DashboardMonitor()
        monitor_thread = threading.Thread(target=monitor.run)
        monitor_thread.daemon = True
        monitor_thread.start()
        monitoring = True
    
    return jsonify({'status': 'started'})


@app.route('/api/stop_monitoring')
def stop_monitoring():
    """Stop background monitoring"""
    global monitoring
    
    if monitoring and monitor_thread:
        monitoring = False
    
    return jsonify({'status': 'stopped'})


# Create basic dashboard template
dashboard_html = '''<!DOCTYPE html>
<html>
<head>
    <title>SOL/USDT Trading Monitor</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #ffffff; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; padding: 20px; background: #2d2d2d; border-radius: 10px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #2d2d2d; padding: 20px; border-radius: 10px; }
        .metric { display: flex; justify-content: space-between; margin: 10px 0; }
        .signal-long { background: #4ade80; color: black; }
        .signal-short { background: #f87171; color: black; }
        .signal-hold { background: #6b7280; }
        .price { font-size: 24px; font-weight: bold; }
        .status { padding: 10px; border-radius: 5px; text-align: center; margin: 10px 0; }
        .button { background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        .button:hover { background: #2563eb; }
        #last-update { color: #9ca3af; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 SOL/USDT Trading Monitor</h1>
            <div id="last-update">Last Update: Never</div>
            <button class="button" onclick="toggleMonitoring()">Start Monitoring</button>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>📊 Current Price</h3>
                <div class="price" id="current-price">$0.00</div>
                <div class="metric">
                    <span>EMA20:</span>
                    <span id="ema20">$0.00</span>
                </div>
                <div class="metric">
                    <span>MACD:</span>
                    <span id="macd">0.000</span>
                </div>
            </div>
            
            <div class="card">
                <h3>📈 RSI Indicators</h3>
                <div class="metric">
                    <span>RSI(7):</span>
                    <span id="rsi7">0.0</span>
                </div>
                <div class="metric">
                    <span>RSI(14):</span>
                    <span id="rsi14">0.0</span>
                </div>
            </div>
            
            <div class="card">
                <h3>🎯 Trading Signal</h3>
                <div class="status" id="signal-status">HOLD</div>
                <div class="metric">
                    <span>Confidence:</span>
                    <span id="confidence">0%</span>
                </div>
                <div class="metric">
                    <span>Strength:</span>
                    <span id="strength">0/100</span>
                </div>
            </div>
            
            <div class="card">
                <h3>💰 Trade Levels</h3>
                <div class="metric">
                    <span>Entry:</span>
                    <span id="entry">-</span>
                </div>
                <div class="metric">
                    <span>Stop Loss:</span>
                    <span id="stop-loss">-</span>
                </div>
                <div class="metric">
                    <span>Take Profit 1:</span>
                    <span id="tp1">-</span>
                </div>
                <div class="metric">
                    <span>Take Profit 2:</span>
                    <span id="tp2">-</span>
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h3>📝 Signal Factors</h3>
            <div id="signal-factors">No active signal factors</div>
        </div>
    </div>

    <script>
        let monitoring = false;
        
        function updateData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    const current = data.current_data;
                    if (current && Object.keys(current).length > 0) {
                        document.getElementById('current-price').textContent = `$${current.price}`;
                        document.getElementById('ema20').textContent = `$${current.ema20}`;
                        document.getElementById('macd').textContent = current.macd.toFixed(3);
                        document.getElementById('rsi7').textContent = current.rsi7.toFixed(1);
                        document.getElementById('rsi14').textContent = current.rsi14.toFixed(1);
                        document.getElementById('confidence').textContent = `${current.confidence}%`;
                        document.getElementById('strength').textContent = `${current.signal_strength}/100`;
                        
                        // Update signal status
                        const signalEl = document.getElementById('signal-status');
                        signalEl.textContent = current.signal_direction;
                        signalEl.className = 'status signal-' + current.signal_direction.toLowerCase();
                        
                        // Update trade levels
                        document.getElementById('entry').textContent = current.entry_price ? `$${current.entry_price}` : '-';
                        document.getElementById('stop-loss').textContent = current.stop_loss ? `$${current.stop_loss}` : '-';
                        document.getElementById('tp1').textContent = current.take_profit_1 ? `$${current.take_profit_1}` : '-';
                        document.getElementById('tp2').textContent = current.take_profit_2 ? `$${current.take_profit_2}` : '-';
                        
                        // Update signal factors
                        const factorsEl = document.getElementById('signal-factors');
                        if (current.signal_factors && current.signal_factors.length > 0) {
                            factorsEl.innerHTML = current.signal_factors.map(f => `• ${f}`).join('<br>');
                        } else {
                            factorsEl.textContent = 'No active signal factors';
                        }
                    }
                    
                    if (data.last_update) {
                        const updateTime = new Date(data.last_update).toLocaleTimeString();
                        document.getElementById('last-update').textContent = `Last Update: ${updateTime}`;
                    }
                })
                .catch(error => console.error('Error fetching data:', error));
        }
        
        function toggleMonitoring() {
            const button = document.querySelector('.button');
            
            if (!monitoring) {
                fetch('/api/start_monitoring')
                    .then(() => {
                        monitoring = true;
                        button.textContent = 'Stop Monitoring';
                        setInterval(updateData, 5000); // Update every 5 seconds
                        updateData(); // Initial update
                    });
            } else {
                fetch('/api/stop_monitoring')
                    .then(() => {
                        monitoring = false;
                        button.textContent = 'Start Monitoring';
                    });
            }
        }
    </script>
</body>
</html>'''

# Ensure templates directory exists and create dashboard template
import os
if not os.path.exists('templates'):
    os.makedirs('templates')

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(dashboard_html)


if __name__ == '__main__':
    print("🚀 Starting Trading Dashboard...")
    print("📊 Dashboard available at: http://localhost:5000")
    print("🔍 Click 'Start Monitoring' to begin real-time monitoring")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=False, host='0.0.0.0', port=5000)