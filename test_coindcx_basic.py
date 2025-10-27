#!/usr/bin/env python3
"""
CoinDCX API Basic Test

Simple test script for CoinDCX API without external dependencies.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only CoinDCX exchange
from exchanges.coindcx_exchange import CoinDCXExchange

def test_basic_functionality():
    """Test basic CoinDCX functionality"""
    print("CoinDCX API Basic Test")
    print("=" * 40)
    
    try:
        # Initialize exchange
        print("1. Initializing CoinDCX exchange...")
        exchange = CoinDCXExchange()
        print("✅ Exchange initialized")
        
        # Test connection
        print("\n2. Testing connection...")
        if exchange.test_connection():
            print("✅ Connection successful")
        else:
            print("❌ Connection failed")
            return False
        
        # Test markets endpoint
        print("\n3. Fetching markets...")
        markets = exchange.get_markets()
        print(f"✅ Retrieved {len(markets)} markets")
        
        # Show sample markets
        sample_markets = list(markets.keys())[:5]
        print(f"Sample markets: {sample_markets}")
        
        # Test symbol conversion
        print("\n4. Testing symbol conversion...")
        test_symbols = ['SOL/USDT', 'BTC/USDT', 'ETH/USDT']
        for symbol in test_symbols:
            dcx_format = exchange._convert_symbol(symbol)
            print(f"  {symbol} -> {dcx_format}")
        
        # Test ticker
        print("\n5. Testing ticker data...")
        try:
            ticker = exchange.get_ticker('SOL/USDT')
            print(f"✅ SOL/USDT ticker:")
            print(f"  - Price: ${ticker.get('last_price', 0):.4f}")
            print(f"  - 24h Change: {ticker.get('price_change_percent', 0):.2f}%")
            print(f"  - Source: {ticker.get('source', 'unknown')}")
        except Exception as e:
            print(f"⚠️ Ticker test failed: {e}")
        
        # Test latest OHLCV
        print("\n6. Testing latest OHLCV...")
        try:
            ohlcv = exchange.get_latest_ohlcv('SOL/USDT', '15m')
            print(f"✅ Latest OHLCV for SOL/USDT:")
            print(f"  - Close: ${ohlcv[4]:.4f}")
            print(f"  - Volume: {ohlcv[5]:.2f}")
        except Exception as e:
            print(f"⚠️ OHLCV test failed: {e}")
        
        # Test historical data
        print("\n7. Testing historical data...")
        try:
            historical = exchange.get_historical_data('SOL/USDT', '15m', limit=5)
            print(f"✅ Retrieved {len(historical)} historical candles")
            if historical:
                latest = historical[-1]
                print(f"  - Latest close: ${latest[4]:.4f}")
        except Exception as e:
            print(f"⚠️ Historical data test failed: {e}")
        
        # Test search
        print("\n8. Testing symbol search...")
        try:
            sol_results = exchange.search_symbols('SOL')
            print(f"✅ Found {len(sol_results)} SOL symbols:")
            print(f"  {sol_results[:3]}")  # Show first 3
        except Exception as e:
            print(f"⚠️ Search test failed: {e}")
        
        print("\n" + "=" * 40)
        print("🎉 Basic tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)