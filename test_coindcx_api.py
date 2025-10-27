#!/usr/bin/env python3
"""
CoinDCX API Test Script

This script demonstrates how to use the enhanced CoinDCX API integration
to fetch various types of market data.
"""

import os
import sys
import json
from datetime import datetime
from exchanges.coindcx_exchange import CoinDCXExchange

def print_separator(title: str):
    """Print a formatted separator with title"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_json(data, title: str = None):
    """Pretty print JSON data"""
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2))

def test_basic_connection():
    """Test basic CoinDCX connection"""
    print_separator("BASIC CONNECTION TEST")
    
    # Initialize exchange
    exchange = CoinDCXExchange()
    
    # Test connection
    print("Testing connection...")
    if exchange.test_connection():
        print("✅ Connection successful!")
        exchange.initialize()
    else:
        print("❌ Connection failed!")
        return False
    
    return True

def test_market_data():
    """Test market data endpoints"""
    print_separator("MARKET DATA")
    
    exchange = CoinDCXExchange()
    
    try:
        # Get all markets
        print("Fetching all markets...")
        markets = exchange.get_markets()
        print(f"✅ Found {len(markets)} markets")
        
        # Show a few sample markets
        sample_markets = list(markets.keys())[:5]
        print(f"\nSample markets: {sample_markets}")
        
        # Get market ticker data
        print("\nFetching market ticker data...")
        tickers = exchange.get_market_data()
        print(f"✅ Found {len(tickers)} tickers")
        
        # Show sample ticker
        if tickers:
            print(f"\nSample ticker:")
            print_json(tickers[0])
        
    except Exception as e:
        print(f"❌ Error fetching market data: {e}")

def test_symbol_operations():
    """Test symbol-related operations"""
    print_separator("SYMBOL OPERATIONS")
    
    exchange = CoinDCXExchange()
    test_symbols = ['SOL/USDT', 'BTC/USDT', 'ETH/USDT']
    
    for symbol in test_symbols:
        print(f"\n--- Testing {symbol} ---")
        
        try:
            # Test symbol validation
            is_valid = exchange.validate_symbol(symbol)
            print(f"Symbol validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
            
            # Test symbol conversion
            dcx_format = exchange._convert_symbol(symbol)
            print(f"CoinDCX format: {dcx_format}")
            
            # Get symbol info
            try:
                symbol_info = exchange.get_symbol_info(symbol)
                print(f"Symbol info available: ✅")
                print(f"  - Min quantity: {symbol_info.get('min_quantity', 'N/A')}")
                print(f"  - Status: {symbol_info.get('status', 'N/A')}")
            except Exception as e:
                print(f"Symbol info: ❌ ({e})")
            
            # Get ticker
            try:
                ticker = exchange.get_ticker(symbol)
                print(f"Ticker data: ✅")
                print(f"  - Last price: ${ticker.get('last_price', 0):.4f}")
                print(f"  - 24h change: {ticker.get('price_change_percent', 0):.2f}%")
                print(f"  - Source: {ticker.get('source', 'unknown')}")
            except Exception as e:
                print(f"Ticker data: ❌ ({e})")
                
        except Exception as e:
            print(f"❌ Error testing {symbol}: {e}")

def test_price_data():
    """Test price and candle data"""
    print_separator("PRICE DATA")
    
    exchange = CoinDCXExchange()
    symbol = 'SOL/USDT'
    timeframe = '15m'
    
    print(f"Testing price data for {symbol} on {timeframe} timeframe...")
    
    try:
        # Get latest OHLCV
        print("\nFetching latest OHLCV...")
        latest_ohlcv = exchange.get_latest_ohlcv(symbol, timeframe)
        print("✅ Latest OHLCV:")
        print(f"  - Timestamp: {datetime.fromtimestamp(latest_ohlcv[0]/1000)}")
        print(f"  - Open: ${latest_ohlcv[1]:.4f}")
        print(f"  - High: ${latest_ohlcv[2]:.4f}")
        print(f"  - Low: ${latest_ohlcv[3]:.4f}")
        print(f"  - Close: ${latest_ohlcv[4]:.4f}")
        print(f"  - Volume: {latest_ohlcv[5]:.2f}")
        
        # Get historical data
        print(f"\nFetching historical data (last 10 candles)...")
        historical_data = exchange.get_historical_data(symbol, timeframe, limit=10)
        print(f"✅ Retrieved {len(historical_data)} candles")
        
        # Show last few candles
        print("\nLast 3 candles:")
        for i, candle in enumerate(historical_data[-3:], 1):
            print(f"  {i}. Close: ${candle[4]:.4f} | Volume: {candle[5]:.2f}")
        
    except Exception as e:
        print(f"❌ Error fetching price data: {e}")

def test_advanced_features():
    """Test advanced features like orderbook and trade history"""
    print_separator("ADVANCED FEATURES")
    
    exchange = CoinDCXExchange()
    symbol = 'SOL/USDT'
    
    try:
        # Test orderbook
        print(f"Fetching orderbook for {symbol}...")
        try:
            orderbook = exchange.get_orderbook(symbol)
            print("✅ Orderbook data retrieved")
            
            # Show top 3 bids and asks
            if 'bids' in orderbook and 'asks' in orderbook:
                print("\nTop 3 bids:")
                bids = list(orderbook['bids'].items())[:3]
                for price, quantity in bids:
                    print(f"  ${price} - {quantity}")
                
                print("\nTop 3 asks:")
                asks = list(orderbook['asks'].items())[:3]
                for price, quantity in asks:
                    print(f"  ${price} - {quantity}")
            
        except Exception as e:
            print(f"❌ Orderbook error: {e}")
        
        # Test trade history
        print(f"\nFetching trade history for {symbol}...")
        try:
            trades = exchange.get_trade_history(symbol, limit=5)
            print(f"✅ Retrieved {len(trades)} recent trades")
            
            # Show recent trades
            if trades:
                print("\nRecent trades:")
                for i, trade in enumerate(trades[:3], 1):
                    price = trade.get('p', 0)
                    quantity = trade.get('q', 0)
                    timestamp = trade.get('T', 0)
                    if timestamp:
                        trade_time = datetime.fromtimestamp(int(timestamp)/1000)
                        print(f"  {i}. Price: ${price} | Qty: {quantity} | Time: {trade_time}")
            
        except Exception as e:
            print(f"❌ Trade history error: {e}")
        
    except Exception as e:
        print(f"❌ Error in advanced features: {e}")

def test_futures_data():
    """Test futures-specific data"""
    print_separator("FUTURES DATA")
    
    exchange = CoinDCXExchange()
    
    try:
        # Test futures instruments
        print("Fetching futures instruments...")
        instruments = exchange.get_futures_instruments()
        print(f"✅ Found {len(instruments)} futures instruments")
        
        # Show sample instruments
        if instruments:
            print("\nSample futures instruments:")
            for i, instrument in enumerate(instruments[:5], 1):
                pair = instrument.get('pair', 'Unknown')
                status = instrument.get('status', 'Unknown')
                print(f"  {i}. {pair} - {status}")
        
        # Test futures prices
        print("\nFetching futures real-time prices...")
        futures_prices = exchange.get_futures_prices()
        if 'prices' in futures_prices:
            prices_count = len(futures_prices['prices'])
            print(f"✅ Retrieved {prices_count} futures prices")
            
            # Show sample prices
            sample_symbols = list(futures_prices['prices'].keys())[:3]
            print("\nSample futures prices:")
            for symbol in sample_symbols:
                price_data = futures_prices['prices'][symbol]
                last_price = price_data.get('ls', 0)
                change_pct = price_data.get('pc', 0)
                print(f"  {symbol}: ${last_price} ({change_pct:+.2f}%)")
        
    except Exception as e:
        print(f"❌ Error fetching futures data: {e}")

def test_search_functionality():
    """Test symbol search functionality"""
    print_separator("SEARCH FUNCTIONALITY")
    
    exchange = CoinDCXExchange()
    
    search_queries = ['SOL', 'BTC', 'ETH', 'USDT']
    
    for query in search_queries:
        print(f"\nSearching for '{query}':")
        try:
            results = exchange.search_symbols(query)
            if results:
                print(f"✅ Found {len(results)} matches:")
                for result in results[:5]:  # Show first 5 results
                    print(f"  - {result}")
            else:
                print("❌ No matches found")
        except Exception as e:
            print(f"❌ Search error: {e}")

def main():
    """Main test function"""
    print("CoinDCX API Integration Test")
    print(f"Timestamp: {datetime.now()}")
    
    # Run all tests
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Market Data", test_market_data),
        ("Symbol Operations", test_symbol_operations),
        ("Price Data", test_price_data),
        ("Advanced Features", test_advanced_features),
        ("Futures Data", test_futures_data),
        ("Search Functionality", test_search_functionality),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            print(f"Running: {test_name}")
            print('='*60)
            
            test_func()
            passed += 1
            print(f"\n✅ {test_name} completed successfully")
            
        except Exception as e:
            print(f"\n❌ {test_name} failed: {e}")
        
        except KeyboardInterrupt:
            print(f"\n⚠️ Test interrupted by user")
            break
    
    # Summary
    print_separator("TEST SUMMARY")
    print(f"Tests completed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️ {total-passed} test(s) failed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")