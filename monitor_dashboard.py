#!/usr/bin/env python3
"""
Real-time Trading Monitor Dashboard
Enhanced web dashboard with live monitoring and signal alerts
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import json
import threading
import time
import queue
import os
from dotenv import load_dotenv
from ema9_api import EMA9API


app = Flask(__name__)

# Global variables for real-time data
current_data = {}
signal_history = []
monitoring_log = []
last_update = None
monitor_thread = None
monitoring = False
data_queue = queue.Queue()


class EnhancedDashboardMonitor:
    """Enhanced background monitoring for dashboard"""
    
    def __init__(self):
        self.api = EMA9API()
        self.running = False
        self.last_signal = None
        self.check_count = 0
        self.signal_count = 0
        self.start_time = None
    
    def log_event(self, message, event_type="INFO", signal_data=None):
        """Log monitoring events"""
        global monitoring_log
        
        timestamp = datetime.now()
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'time_str': timestamp.strftime('%H:%M:%S'),
            'type': event_type,
            'message': message,
            'signal_data': signal_data
        }
        
        monitoring_log.append(log_entry)
        
        # Keep only last 100 log entries
        if len(monitoring_log) > 100:
            monitoring_log.pop(0)
        
        print(f"[{log_entry['time_str']}] {event_type}: {message}")
    
    def update_data(self):
        """Update current market data and signals"""
        global current_data, signal_history, last_update
        
        try:
            self.check_count += 1
            
            # Get comprehensive data
            data = self.api.get_ema9_data()
            signal = self.api.get_trading_signal()
            
            if 'error' in data or 'error' in signal:
                self.log_event(f"API Error: {data.get('error', signal.get('error'))}", "ERROR")
                return
            
            # Update current data
            current_data = {
                'timestamp': datetime.now().isoformat(),
                'check_count': self.check_count,
                'signal_count': self.signal_count,
                
                # Market data
                'symbol': data.get('symbol', os.getenv('TRADING_SYMBOL', 'SOL/USDT')),
                'price': data.get('current_price', 0),
                'ema20': data.get('current_ema20', 0),
                'ema50': data.get('current_ema50', 0),
                'macd': data.get('current_macd', 0),
                'rsi7': data.get('current_rsi7', 0),
                'rsi14': data.get('current_rsi14', 0),
                
                # Signal data
                'signal_direction': signal.get('signal_direction', 'HOLD'),
                'confidence': signal.get('confidence', 0),
                'signal_strength': signal.get('signal_strength', 0),
                'entry_price': signal.get('entry_price'),
                'stop_loss': signal.get('stop_loss'),
                'take_profit_1': signal.get('take_profit_1'),
                'take_profit_2': signal.get('take_profit_2'),
                'take_profit_3': signal.get('take_profit_3'),
                'position_size_pct': signal.get('position_size_pct', 0),
                'risk_amount': signal.get('risk_amount', 0),
                'validity_hours': signal.get('validity_hours', 0),
                'signal_factors': signal.get('signal_factors', []),
                
                # Price vs EMAs
                'price_vs_ema20_pct': ((data.get('current_price', 0) - data.get('current_ema20', 0)) / data.get('current_ema20', 1)) * 100,
                'price_vs_ema50_pct': ((data.get('current_price', 0) - data.get('current_ema50', 0)) / data.get('current_ema50', 1)) * 100,
                
                # Risk/Reward ratios
                'risk_reward_1': signal.get('risk_reward_1', 0),
                'risk_reward_2': signal.get('risk_reward_2', 0),
                'risk_reward_3': signal.get('risk_reward_3', 0),
                
                # Monitoring stats
                'uptime': str(datetime.now() - self.start_time) if self.start_time else "0:00:00",
                'next_check': (datetime.now() + timedelta(minutes=3)).strftime('%H:%M:%S')
            }
            
            # Check for new signal
            direction = signal.get('signal_direction', 'HOLD')
            if direction != self.last_signal:
                
                if direction != 'HOLD':
                    # New trading signal detected
                    self.signal_count += 1
                    signal_history.append(current_data.copy())
                    
                    emoji = "📈" if direction == "LONG" else "📉"
                    self.log_event(
                        f"{emoji} {direction} signal detected - Price: ${current_data['price']}, RSI(7): {current_data['rsi7']:.1f}, Confidence: {current_data['confidence']}%",
                        "SIGNAL",
                        current_data.copy()
                    )
                    
                    # Keep only last 20 signals in history
                    if len(signal_history) > 20:
                        signal_history.pop(0)
                        
                elif self.last_signal and self.last_signal != 'HOLD':
                    # Signal cleared
                    self.log_event(f"Signal cleared - Back to HOLD", "INFO")
                
                self.last_signal = direction
            
            # Regular status log (every 5th check to avoid spam)
            if self.check_count % 5 == 0 or direction != 'HOLD':
                status_emoji = "🔄" if direction == "HOLD" else ("📈" if direction == "LONG" else "📉")
                self.log_event(
                    f"{status_emoji} Check #{self.check_count}: {direction} | ${current_data['price']} | RSI7: {current_data['rsi7']:.1f}",
                    "STATUS"
                )
            
            last_update = datetime.now()
            
        except Exception as e:
            self.log_event(f"Update failed: {str(e)}", "ERROR")
    
    def run(self):
        """Run continuous monitoring"""
        self.running = True
        self.start_time = datetime.now()
        
        self.log_event("Monitor started - checking every 3 minutes", "INFO")
        
        while self.running:
            self.update_data()
            
            # Wait 3 minutes (180 seconds) between checks
            for _ in range(180):  # 180 seconds = 3 minutes
                if not self.running:
                    break
                time.sleep(1)
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        self.log_event(f"Monitor stopped - {self.check_count} checks, {self.signal_count} signals detected", "INFO")


@app.route('/')
def dashboard():
    """Main dashboard page"""
    # Load environment variables
    load_dotenv()
    trading_symbol = os.getenv('TRADING_SYMBOL', 'SOL/USDT')
    
    # Debug: Print the trading symbol being used
    print(f"📊 Dashboard loading with symbol: {trading_symbol}")
    
    return render_template('monitor_dashboard.html', trading_symbol=trading_symbol)


@app.route('/api/data')
def get_data():
    """Get current monitoring data"""
    return jsonify({
        'current_data': current_data,
        'signal_history': signal_history[-10:],  # Last 10 signals
        'monitoring_log': monitoring_log[-20:],  # Last 20 log entries
        'last_update': last_update.isoformat() if last_update else None,
        'monitoring_active': monitoring
    })


@app.route('/api/start_monitoring')
def start_monitoring():
    """Start background monitoring"""
    global monitor_thread, monitoring
    
    if not monitoring:
        monitor = EnhancedDashboardMonitor()
        monitor_thread = threading.Thread(target=monitor.run)
        monitor_thread.daemon = True
        monitor_thread.start()
        monitoring = True
        return jsonify({'status': 'started', 'message': 'Monitoring started'})
    else:
        return jsonify({'status': 'already_running', 'message': 'Monitoring already active'})


@app.route('/api/stop_monitoring')
def stop_monitoring():
    """Stop background monitoring"""
    global monitoring
    
    if monitoring and monitor_thread:
        monitoring = False
        return jsonify({'status': 'stopped', 'message': 'Monitoring stopped'})
    else:
        return jsonify({'status': 'not_running', 'message': 'Monitoring not active'})


@app.route('/api/get_signal')
def get_current_signal():
    """Get current signal immediately and update dashboard data"""
    global current_data, signal_history, monitoring_log, last_update
    
    try:
        api = EMA9API()
        
        # Get comprehensive data and signal
        data = api.get_ema9_data()
        signal = api.get_trading_signal()
        
        if 'error' in data or 'error' in signal:
            error_msg = data.get('error', signal.get('error', 'Unknown error'))
            return jsonify({'success': False, 'error': error_msg})
        
        # Update current_data immediately with fresh data
        timestamp = datetime.now()
        
        # Get comprehensive intraday series and longer-term context
        try:
            intraday_series = api.get_intraday_series_data()  # Get last 10 minutes of 1m data
            if 'error' in intraday_series:
                intraday_series = {}  # Use empty dict as fallback
        except:
            intraday_series = {}
            
        try:
            longer_context = api.get_longer_term_context()    # Get 4H context data
            if 'error' in longer_context:
                longer_context = {}  # Use empty dict as fallback
        except:
            longer_context = {}
        
        current_data.update({
            'timestamp': timestamp.isoformat(),
            'manual_check': True,  # Flag to indicate this was a manual check            # Market data
            'symbol': data.get('symbol', os.getenv('TRADING_SYMBOL', 'SOL/USDT')),
            'price': data.get('current_price', 0),
            'ema20': data.get('current_ema20', 0),
            'ema50': data.get('current_ema50', 0),
            'macd': data.get('current_macd', 0),
            'rsi7': data.get('current_rsi7', 0),
            'rsi14': data.get('current_rsi14', 0),
            
            # Signal data
            'signal_direction': signal.get('signal_direction', 'HOLD'),
            'confidence': signal.get('confidence', 0),
            'signal_strength': signal.get('signal_strength', 0),
            'entry_price': signal.get('entry_price'),
            'stop_loss': signal.get('stop_loss'),
            'take_profit_1': signal.get('take_profit_1'),
            'take_profit_2': signal.get('take_profit_2'),
            'take_profit_3': signal.get('take_profit_3'),
            'position_size_pct': signal.get('position_size_pct', 0),
            'risk_amount': signal.get('risk_amount', 0),
            'validity_hours': signal.get('validity_hours', 0),
            'signal_factors': signal.get('signal_factors', []),
            
            # Price vs EMAs
            'price_vs_ema20_pct': ((data.get('current_price', 0) - data.get('current_ema20', 0)) / data.get('current_ema20', 1)) * 100,
            'price_vs_ema50_pct': ((data.get('current_price', 0) - data.get('current_ema50', 0)) / data.get('current_ema50', 1)) * 100,
            
            # Risk/Reward ratios
            'risk_reward_1': signal.get('risk_reward_1', 0),
            'risk_reward_2': signal.get('risk_reward_2', 0),
            'risk_reward_3': signal.get('risk_reward_3', 0),
            
            # Intraday series data for comprehensive analysis
            'intraday_series': intraday_series,
            'longer_term_context': longer_context,
        })
        
        # Log the manual check
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'time_str': timestamp.strftime('%H:%M:%S'),
            'type': 'INFO',
            'message': f"📋 Manual check - {signal.get('signal_direction', 'HOLD')} | Price: ${data.get('current_price', 0)} | RSI(7): {data.get('current_rsi7', 0):.1f} | Confidence: {signal.get('confidence', 0)}%",
            'signal_data': current_data.copy()
        }
        
        monitoring_log.append(log_entry)
        if len(monitoring_log) > 100:
            monitoring_log.pop(0)
        
        last_update = timestamp
        
        return jsonify({
            'success': True, 
            'signal': signal,
            'data': data,
            'current_data': current_data,
            'message': 'Manual check completed - dashboard updated with latest data'
        })
        
    except Exception as e:
        error_msg = f"Manual check failed: {str(e)}"
        
        # Log the error
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'type': 'ERROR',
            'message': error_msg,
            'signal_data': None
        }
        
        monitoring_log.append(log_entry)
        if len(monitoring_log) > 100:
            monitoring_log.pop(0)
        
        return jsonify({'success': False, 'error': error_msg})





if __name__ == '__main__':
    print("🚀 Starting Enhanced Trading Monitor Dashboard...")
    print("📊 Dashboard available at: http://localhost:5001")
    print("🔍 Real-time monitoring with alerts and signal detection")
    print("📈 Features: Live price data, RSI gauges, signal history, monitoring log")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5001)