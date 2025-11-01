#!/usr/bin/env python3
"""
Trading Signal Generator for CoinDCX
Generates automated trading signals with entry, stop loss, and take profit levels
Based on comprehensive technical analysis including EMA, MACD, RSI, and ATR
"""

from ema9_api import EMA9API, get_trading_signal, get_trade_recommendation
import json
from datetime import datetime


def main():
    """Main function to generate and display trading signals"""
    print("=" * 70)
    print("🚀 AUTOMATED TRADING SIGNAL GENERATOR")
    print("=" * 70)
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Initialize API
        api = EMA9API()
        
        # Test connection first
        print("Testing connection...")
        test_result = api.test_connection()
        if test_result['status'] != 'SUCCESS':
            print(f"❌ Connection failed: {test_result.get('error', 'Unknown error')}")
            return
        
        print(f"✅ Connected to {test_result['exchange_name']}")
        print()
        
        # Get formatted trading signal
        print("🎯 GENERATING TRADING SIGNAL...")
        print("=" * 50)
        
        signal_text = api.get_formatted_trading_signal()
        print(signal_text)
        
        # Also get JSON data for programmatic use
        print("\n" + "=" * 70)
        print("📊 JSON TRADING DATA (for algorithms)")
        print("=" * 70)
        
        signal_data = api.get_trading_signal()
        
        # Print key trading levels
        if signal_data.get('signal_direction') != 'HOLD':
            print(f"Direction: {signal_data['signal_direction']}")
            print(f"Entry: ${signal_data['entry_price']}")
            print(f"Stop Loss: ${signal_data['stop_loss']}")
            print(f"Take Profit 1: ${signal_data['take_profit_1']} (R/R: 1:{signal_data['risk_reward_1']})")
            print(f"Take Profit 2: ${signal_data['take_profit_2']} (R/R: 1:{signal_data['risk_reward_2']})")
            print(f"Take Profit 3: ${signal_data['take_profit_3']} (R/R: 1:{signal_data['risk_reward_3']})")
            print(f"Position Size: {signal_data['position_size_pct']}% of capital")
            print(f"Confidence: {signal_data['confidence']}%")
        else:
            print("No trading signal - HOLD/WAIT for better setup")
        
        # Show current market summary
        print(f"\nCurrent Market Summary:")
        print(f"  Symbol: {signal_data['symbol']}")
        print(f"  Price: ${signal_data['current_price']}")
        print(f"  EMA20: ${signal_data['current_ema20']}")
        print(f"  MACD: {signal_data['current_macd']}")
        print(f"  RSI(7): {signal_data['current_rsi7']}")
        print(f"  RSI(14): {signal_data['current_rsi14']}")
        
        print("\n" + "=" * 70)
        print("💡 USAGE EXAMPLES")
        print("=" * 70)
        print("""
# Get trading signal in Python:
from ema9_api import get_trading_signal, get_trade_recommendation

# Get structured data
signal = get_trading_signal()
if signal['signal_direction'] == 'LONG':
    print(f"Go LONG at ${signal['entry_price']}")
    print(f"Stop Loss: ${signal['stop_loss']}")
    print(f"Take Profit: ${signal['take_profit_1']}")

# Get formatted recommendation  
recommendation = get_trade_recommendation()
print(recommendation)

# Command line usage:
python trading_signals.py            # This script
python ema9_api.py trade            # JSON output
python ema9_api.py trade-formatted  # Formatted output
""")
        
    except Exception as e:
        print(f"❌ Error generating signal: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()