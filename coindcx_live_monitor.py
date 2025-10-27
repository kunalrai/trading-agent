#!/usr/bin/env python3
"""
CoinDCX Live Market Monitor

This script demonstrates real-time market monitoring using the CoinDCX API.
It shows live price updates, market analysis, and breakout detection.
"""

import time
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from exchanges.coindcx_exchange import CoinDCXExchange

class CoinDCXMarketMonitor:
    """Live market monitor using CoinDCX API"""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.exchange = CoinDCXExchange(api_key, api_secret)
        self.running = False
        
        # Monitoring configuration
        self.symbols = ['SOL/USDT', 'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
        self.timeframe = '15m'
        self.update_interval = 60  # seconds
        
        # Market data cache
        self.price_history: Dict[str, List[float]] = {}
        self.last_prices: Dict[str, float] = {}
        self.alerts_triggered: Dict[str, int] = {}
        
        print("CoinDCX Market Monitor initialized")
        print(f"Symbols: {self.symbols}")
        print(f"Timeframe: {self.timeframe}")
        print(f"Update interval: {self.update_interval}s")
    
    def initialize(self):
        """Initialize the monitor"""
        try:
            self.exchange.initialize()
            print("✅ Exchange connection established")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize exchange: {e}")
            return False
    
    def get_market_overview(self) -> Dict[str, Any]:
        """Get overall market overview"""
        overview = {
            'timestamp': datetime.now(),
            'total_symbols': len(self.symbols),
            'active_alerts': sum(self.alerts_triggered.values()),
            'market_data': {}
        }
        
        try:
            # Get futures prices for overview
            futures_prices = self.exchange.get_futures_prices()
            
            if 'prices' in futures_prices:
                overview['futures_markets'] = len(futures_prices['prices'])
                overview['market_timestamp'] = futures_prices.get('ts', 0)
            
        except Exception as e:
            print(f"Warning: Could not fetch market overview: {e}")
        
        return overview
    
    def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Analyze a single symbol"""
        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'status': 'unknown',
            'error': None
        }
        
        try:
            # Get latest ticker
            ticker = self.exchange.get_ticker(symbol)
            analysis['ticker'] = ticker
            analysis['current_price'] = ticker.get('last_price', 0)
            analysis['price_change_24h'] = ticker.get('price_change_percent', 0)
            analysis['source'] = ticker.get('source', 'unknown')
            
            # Get latest OHLCV
            ohlcv = self.exchange.get_latest_ohlcv(symbol, self.timeframe)
            analysis['ohlcv'] = {
                'timestamp': datetime.fromtimestamp(ohlcv[0]/1000),
                'open': ohlcv[1],
                'high': ohlcv[2],
                'low': ohlcv[3],
                'close': ohlcv[4],
                'volume': ohlcv[5]
            }
            
            # Calculate basic indicators
            try:
                historical_data = self.exchange.get_historical_data(symbol, self.timeframe, limit=20)
                if len(historical_data) >= 20:
                    closes = [candle[4] for candle in historical_data]
                    
                    # Simple moving averages
                    sma_10 = sum(closes[-10:]) / 10
                    sma_20 = sum(closes[-20:]) / 20
                    
                    analysis['indicators'] = {
                        'sma_10': sma_10,
                        'sma_20': sma_20,
                        'above_sma_10': analysis['current_price'] > sma_10,
                        'above_sma_20': analysis['current_price'] > sma_20,
                        'bullish_cross': sma_10 > sma_20
                    }
                    
                    # Price change analysis
                    if len(closes) >= 2:
                        price_change = ((closes[-1] - closes[-2]) / closes[-2]) * 100
                        analysis['price_change_last_candle'] = price_change
                    
                    # Volume analysis
                    volumes = [candle[5] for candle in historical_data]
                    avg_volume = sum(volumes[-10:]) / 10
                    current_volume = volumes[-1]
                    analysis['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 0
            
            except Exception as e:
                analysis['indicators_error'] = str(e)
            
            # Update price history
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            self.price_history[symbol].append(analysis['current_price'])
            
            # Keep only last 100 prices
            if len(self.price_history[symbol]) > 100:
                self.price_history[symbol] = self.price_history[symbol][-100:]
            
            # Price movement analysis
            if symbol in self.last_prices:
                price_change = analysis['current_price'] - self.last_prices[symbol]
                analysis['price_movement'] = {
                    'change': price_change,
                    'change_percent': (price_change / self.last_prices[symbol]) * 100 if self.last_prices[symbol] > 0 else 0,
                    'direction': 'up' if price_change > 0 else 'down' if price_change < 0 else 'flat'
                }
            
            self.last_prices[symbol] = analysis['current_price']
            analysis['status'] = 'success'
            
        except Exception as e:
            analysis['error'] = str(e)
            analysis['status'] = 'error'
        
        return analysis
    
    def check_breakout_conditions(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Check for breakout conditions"""
        alerts = {
            'symbol': analysis['symbol'],
            'alerts': [],
            'total_alerts': 0
        }
        
        try:
            current_price = analysis.get('current_price', 0)
            indicators = analysis.get('indicators', {})
            volume_ratio = analysis.get('volume_ratio', 0)
            price_movement = analysis.get('price_movement', {})
            
            # Alert conditions
            alert_conditions = []
            
            # 1. Price above both SMAs with high volume
            if (indicators.get('above_sma_10', False) and 
                indicators.get('above_sma_20', False) and 
                volume_ratio > 1.5):
                alert_conditions.append({
                    'type': 'bullish_breakout',
                    'message': f"Price above SMAs with high volume (ratio: {volume_ratio:.2f})",
                    'priority': 'high'
                })
            
            # 2. SMA crossover
            if indicators.get('bullish_cross', False) and indicators.get('above_sma_20', False):
                alert_conditions.append({
                    'type': 'sma_crossover',
                    'message': "Bullish SMA crossover detected",
                    'priority': 'medium'
                })
            
            # 3. Strong price movement
            price_change_pct = price_movement.get('change_percent', 0)
            if abs(price_change_pct) > 2.0:  # More than 2% movement
                direction = "upward" if price_change_pct > 0 else "downward"
                alert_conditions.append({
                    'type': 'strong_movement',
                    'message': f"Strong {direction} movement: {price_change_pct:+.2f}%",
                    'priority': 'medium' if abs(price_change_pct) < 5 else 'high'
                })
            
            # 4. High volume spike
            if volume_ratio > 3.0:
                alert_conditions.append({
                    'type': 'volume_spike',
                    'message': f"Volume spike: {volume_ratio:.2f}x average",
                    'priority': 'medium'
                })
            
            # 5. 24h change alert
            change_24h = analysis.get('price_change_24h', 0)
            if abs(change_24h) > 10:  # More than 10% in 24h
                direction = "gained" if change_24h > 0 else "lost"
                alert_conditions.append({
                    'type': '24h_movement',
                    'message': f"24h: {direction} {abs(change_24h):.1f}%",
                    'priority': 'low'
                })
            
            alerts['alerts'] = alert_conditions
            alerts['total_alerts'] = len(alert_conditions)
            
            # Update alert counter
            symbol = analysis['symbol']
            if symbol not in self.alerts_triggered:
                self.alerts_triggered[symbol] = 0
            
            self.alerts_triggered[symbol] += len(alert_conditions)
            
        except Exception as e:
            alerts['error'] = str(e)
        
        return alerts
    
    def display_analysis(self, analysis: Dict[str, Any], alerts: Dict[str, Any]):
        """Display analysis results"""
        symbol = analysis['symbol']
        timestamp = analysis['timestamp'].strftime("%H:%M:%S")
        
        # Status indicator
        status_icon = "✅" if analysis['status'] == 'success' else "❌"
        
        print(f"\n{status_icon} {symbol} [{timestamp}]")
        
        if analysis['status'] == 'success':
            current_price = analysis.get('current_price', 0)
            change_24h = analysis.get('price_change_24h', 0)
            source = analysis.get('source', 'unknown')
            
            # Price info
            change_icon = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
            print(f"  Price: ${current_price:.4f} ({change_24h:+.2f}%) {change_icon} [{source}]")
            
            # Indicators
            indicators = analysis.get('indicators', {})
            if indicators:
                sma_10 = indicators.get('sma_10', 0)
                sma_20 = indicators.get('sma_20', 0)
                above_10 = "✅" if indicators.get('above_sma_10', False) else "❌"
                above_20 = "✅" if indicators.get('above_sma_20', False) else "❌"
                
                print(f"  SMA10: ${sma_10:.4f} {above_10} | SMA20: ${sma_20:.4f} {above_20}")
            
            # Volume
            volume_ratio = analysis.get('volume_ratio', 0)
            if volume_ratio > 0:
                volume_icon = "🔥" if volume_ratio > 2.0 else "📊"
                print(f"  Volume: {volume_ratio:.2f}x average {volume_icon}")
            
            # Price movement
            price_movement = analysis.get('price_movement', {})
            if price_movement:
                change_pct = price_movement.get('change_percent', 0)
                direction = price_movement.get('direction', 'flat')
                movement_icon = "⬆️" if direction == 'up' else "⬇️" if direction == 'down' else "➡️"
                print(f"  Movement: {change_pct:+.3f}% {movement_icon}")
            
            # Alerts
            if alerts['total_alerts'] > 0:
                print(f"  🚨 ALERTS ({alerts['total_alerts']}):")
                for alert in alerts['alerts']:
                    priority_icon = "🔴" if alert['priority'] == 'high' else "🟡" if alert['priority'] == 'medium' else "🔵"
                    print(f"    {priority_icon} {alert['message']}")
        
        else:
            print(f"  ❌ Error: {analysis.get('error', 'Unknown error')}")
    
    def run_single_update(self):
        """Run a single update cycle"""
        print(f"\n{'='*70}")
        print(f"Market Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*70)
        
        # Get market overview
        overview = self.get_market_overview()
        print(f"📊 Monitoring {overview['total_symbols']} symbols | "
              f"Total alerts: {overview['active_alerts']}")
        
        # Analyze each symbol
        for symbol in self.symbols:
            try:
                analysis = self.analyze_symbol(symbol)
                alerts = self.check_breakout_conditions(analysis)
                self.display_analysis(analysis, alerts)
                
            except Exception as e:
                print(f"❌ Error analyzing {symbol}: {e}")
        
        print(f"\n{'='*70}")
        print(f"Next update in {self.update_interval} seconds...")
    
    def run_continuous(self):
        """Run continuous monitoring"""
        self.running = True
        print(f"\n🚀 Starting continuous monitoring...")
        print(f"Press Ctrl+C to stop")
        
        try:
            while self.running:
                self.run_single_update()
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️ Monitoring stopped by user")
            self.running = False
        
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
            self.running = False
    
    def run_demo(self):
        """Run a demo with limited updates"""
        print(f"\n🎮 Running demo mode (3 updates)...")
        
        for i in range(3):
            print(f"\n--- Demo Update {i+1}/3 ---")
            self.run_single_update()
            
            if i < 2:  # Don't sleep after last update
                time.sleep(30)  # Shorter interval for demo
        
        print(f"\n🎯 Demo completed!")

def main():
    """Main function"""
    print("CoinDCX Live Market Monitor")
    print("="*50)
    
    # Initialize monitor
    monitor = CoinDCXMarketMonitor()
    
    if not monitor.initialize():
        print("❌ Failed to initialize monitor")
        return
    
    # Run based on user choice
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        monitor.run_demo()
    elif len(sys.argv) > 1 and sys.argv[1] == 'single':
        monitor.run_single_update()
    else:
        print("\nOptions:")
        print("  python coindcx_live_monitor.py        - Continuous monitoring")
        print("  python coindcx_live_monitor.py demo   - Demo mode (3 updates)")
        print("  python coindcx_live_monitor.py single - Single update")
        
        choice = input("\nChoose mode (c/d/s): ").lower()
        
        if choice == 'd':
            monitor.run_demo()
        elif choice == 's':
            monitor.run_single_update()
        else:
            monitor.run_continuous()

if __name__ == "__main__":
    main()