#!/usr/bin/env python3
"""
Test CoinDCX Trading Integration
Quick test to verify that the trading system works with CoinDCX data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trade import TradeSignalGenerator
from exchanges.coindcx_exchange import CoinDCXExchange

def test_coindcx_integration():
    """Test CoinDCX integration with trading system"""
    
    print("=" * 60)
    print("TESTING COINDCX TRADING INTEGRATION")
    print("=" * 60)
    
    try:
        # Test 1: Direct CoinDCX exchange
        print("\n1. Testing direct CoinDCX exchange...")
        exchange = CoinDCXExchange()
        
        # Test connection
        if exchange.test_connection():
            print("   ✅ CoinDCX API connection successful")
        else:
            print("   ❌ CoinDCX API connection failed")
            return
        
        # Test symbol validation
        symbol = 'ZEC/USDT'
        if exchange.validate_symbol(symbol):
            print(f"   ✅ Symbol {symbol} is supported")
        else:
            print(f"   ❌ Symbol {symbol} not supported")
        
        # Test ticker data
        try:
            ticker = exchange.get_ticker(symbol)
            print(f"   ✅ Current {symbol} price: ${ticker['last_price']:.2f}")
        except Exception as e:
            print(f"   ⚠️  Ticker error: {e}")
        
        # Test historical data
        try:
            historical = exchange.get_historical_data(symbol, '5m', 10)
            print(f"   ✅ Historical data: {len(historical)} candles retrieved")
            if historical:
                latest_price = historical[-1][4]  # close price
                print(f"   ✅ Latest close price: ${latest_price:.2f}")
        except Exception as e:
            print(f"   ⚠️  Historical data error: {e}")
        
        print("\n2. Testing trading signal generator with CoinDCX...")
        
        # Set environment to use CoinDCX
        os.environ['EXCHANGE'] = 'coindcx'
        os.environ['TRADING_SYMBOL'] = symbol
        
        # Create trading signal generator
        signal_generator = TradeSignalGenerator()
        
        if hasattr(signal_generator, 'coindcx_exchange'):
            print("   ✅ CoinDCX exchange properly initialized in trading system")
        else:
            print("   ❌ CoinDCX exchange not properly initialized")
            return
        
        # Test market data retrieval
        try:
            market_data = signal_generator.get_market_data('5m', 20)
            print(f"   ✅ Market data retrieved: {len(market_data['close'])} data points")
            print(f"   ✅ Current price from trading system: ${market_data['current_price']:.2f}")
        except Exception as e:
            print(f"   ❌ Market data error: {e}")
            return
        
        print("\n3. Testing complete trading analysis...")
        
        # Generate full trading analysis
        try:
            analysis = signal_generator.generate_analysis()
            print("   ✅ Trading analysis generated successfully")
            print("\n" + "=" * 60)
            print("SAMPLE ANALYSIS OUTPUT:")
            print("=" * 60)
            print(analysis)
        except Exception as e:
            print(f"   ❌ Analysis generation error: {e}")
            return
        
        print("\n" + "=" * 60)
        print("✅ COINDCX INTEGRATION TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nThe trading system is now fully compatible with CoinDCX data.")
        print("You can:")
        print("- Run paper trading with live CoinDCX data")
        print("- Use the dashboard with real-time CoinDCX prices")
        print("- Generate trading signals based on CoinDCX market data")
        print("- Access futures and spot data from CoinDCX")
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

def test_available_symbols():
    """Test which symbols are available on CoinDCX"""
    print("\n" + "=" * 60)
    print("AVAILABLE COINDCX SYMBOLS")
    print("=" * 60)
    
    try:
        exchange = CoinDCXExchange()
        
        # Test common symbols
        test_symbols = ['SOL/USDT', 'BTC/USDT', 'ETH/USDT', 'ZEC/USDT', 'ADA/USDT', 'DOT/USDT']
        
        print("Testing symbol availability:")
        for symbol in test_symbols:
            try:
                if exchange.validate_symbol(symbol):
                    ticker = exchange.get_ticker(symbol)
                    print(f"✅ {symbol:<12} - Price: ${ticker['last_price']:.2f}")
                else:
                    print(f"❌ {symbol:<12} - Not available")
            except Exception as e:
                print(f"⚠️  {symbol:<12} - Error: {str(e)[:50]}")
        
        # Search for ZEC specifically
        print(f"\nSearching for ZEC symbols:")
        zec_symbols = exchange.search_symbols('ZEC')
        if zec_symbols:
            for sym in zec_symbols[:5]:  # Show first 5
                print(f"   - {sym}")
        else:
            print("   No ZEC symbols found")
            
    except Exception as e:
        print(f"Error testing symbols: {e}")

if __name__ == "__main__":
    test_coindcx_integration()
    test_available_symbols()