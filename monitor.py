#!/usr/bin/env python3
"""
Continuous Trading Signal Monitor
Monitors SOL/USDT for trading signals every 15 minutes
"""

import time
from datetime import datetime
import os
from ema9_api import EMA9API


class TradingMonitor:
    """Continuous monitoring system for trading signals"""
    
    def __init__(self, check_interval_minutes=15):
        self.api = EMA9API()
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self.last_signal = None
        self.signal_count = 0
        
    def print_header(self):
        """Print monitoring header"""
        print("=" * 80)
        print("🔍 SOL/USDT Trading Signal Monitor")
        print("=" * 80)
        print(f"Check Interval: {self.check_interval // 60} minutes")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Monitoring: SOL/USDT on CoinDCX")
        print("=" * 80)
        print()
    
    def check_signal(self):
        """Check for trading signals"""
        try:
            # Get trading signal
            signal = self.api.get_trading_signal()
            
            if 'error' in signal:
                print(f"❌ Error: {signal['error']}")
                return None
            
            # Format timestamp
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Current market data
            direction = signal.get('signal_direction', 'HOLD')
            confidence = signal.get('confidence', 0)
            price = signal.get('current_price', 0)
            rsi7 = signal.get('current_rsi7', 0)
            rsi14 = signal.get('current_rsi14', 0)
            macd = signal.get('current_macd', 0)
            
            # Print current status
            status_emoji = "🔄" if direction == "HOLD" else ("📈" if direction == "LONG" else "📉")
            
            print(f"[{timestamp}] {status_emoji} {direction} | Price: ${price} | RSI7: {rsi7:.1f} | Conf: {confidence}%")
            
            # Check if signal changed
            if direction != "HOLD" and direction != self.last_signal:
                self.print_trading_alert(signal, timestamp)
                self.signal_count += 1
            
            self.last_signal = direction
            return signal
            
        except Exception as e:
            print(f"❌ Error checking signal: {str(e)}")
            return None
    
    def print_trading_alert(self, signal, timestamp):
        """Print detailed trading alert when signal detected"""
        print("\n" + "🚨" * 20)
        print("🚨 TRADING SIGNAL ALERT!")
        print("🚨" * 20)
        
        direction = signal.get('signal_direction')
        emoji = "📈" if direction == "LONG" else "📉"
        
        print(f"\n{emoji} {direction} SIGNAL DETECTED at {timestamp}")
        print(f"├─ Symbol: {signal.get('symbol', 'SOL/USDT')}")
        print(f"├─ Price: ${signal.get('current_price', 0)}")
        print(f"├─ Confidence: {signal.get('confidence', 0)}%")
        print(f"├─ RSI(7): {signal.get('current_rsi7', 0):.1f}")
        print(f"├─ RSI(14): {signal.get('current_rsi14', 0):.1f}")
        print(f"└─ MACD: {signal.get('current_macd', 0):.3f}")
        
        if direction != "HOLD":
            print(f"\n💰 TRADE SETUP:")
            print(f"├─ Entry: ${signal.get('entry_price', 0)}")
            print(f"├─ Stop Loss: ${signal.get('stop_loss', 0)}")
            print(f"├─ Take Profit 1: ${signal.get('take_profit_1', 0)}")
            print(f"├─ Take Profit 2: ${signal.get('take_profit_2', 0)}")
            print(f"└─ Take Profit 3: ${signal.get('take_profit_3', 0)}")
            
            print(f"\n📊 POSITION:")
            print(f"├─ Position Size: {signal.get('position_size_pct', 0)}% of capital")
            print(f"├─ Risk Amount: ${signal.get('risk_amount', 0)}")
            print(f"└─ Validity: {signal.get('validity_hours', 0)} hours")
            
            print(f"\n🎯 SIGNAL FACTORS:")
            for i, factor in enumerate(signal.get('signal_factors', []), 1):
                print(f"├─ {i}. {factor}")
        
        print("\n" + "🚨" * 20)
        print()
    
    def run_continuous(self):
        """Run continuous monitoring"""
        self.print_header()
        
        # Test connection first
        try:
            test = self.api.test_connection()
            if test.get('status') != 'SUCCESS':
                print(f"❌ Connection failed: {test.get('error', 'Unknown error')}")
                return
            
            print(f"✅ Connected to {test.get('exchange_name', 'Exchange')}")
            print()
        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            return
        
        print("🔍 Starting continuous monitoring...")
        print("Press Ctrl+C to stop monitoring")
        print()
        
        try:
            while True:
                self.check_signal()
                
                # Show next check time
                next_check = datetime.now()
                next_check = next_check.replace(
                    minute=(next_check.minute + self.check_interval // 60) % 60,
                    second=0, microsecond=0
                )
                
                print(f"    Next check: {next_check.strftime('%H:%M:%S')}")
                print()
                
                # Wait for next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n" + "=" * 50)
            print("🛑 Monitoring stopped by user")
            print(f"📊 Total signals detected: {self.signal_count}")
            print(f"⏰ Monitoring duration: {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 50)
    
    def run_once(self):
        """Run single check"""
        print("🔍 Single Signal Check")
        print("=" * 40)
        
        signal = self.check_signal()
        if signal and signal.get('signal_direction') != 'HOLD':
            self.print_trading_alert(signal, datetime.now().strftime('%H:%M:%S'))
        
        return signal


def main():
    """Main function with command line options"""
    import sys
    
    monitor = TradingMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'once':
            # Single check
            monitor.run_once()
        elif command == 'fast':
            # Fast monitoring (every 5 minutes)
            monitor.check_interval = 5 * 60
            monitor.run_continuous()
        elif command == 'slow':
            # Slow monitoring (every 30 minutes) 
            monitor.check_interval = 30 * 60
            monitor.run_continuous()
        else:
            print("Usage:")
            print("  python monitor.py          - Monitor every 15 minutes")
            print("  python monitor.py once     - Single check only")
            print("  python monitor.py fast     - Monitor every 5 minutes")
            print("  python monitor.py slow     - Monitor every 30 minutes")
    else:
        # Default: continuous monitoring every 15 minutes
        monitor.run_continuous()


if __name__ == "__main__":
    main()