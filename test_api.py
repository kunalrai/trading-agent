import requests
import json

try:
    response = requests.get('http://127.0.0.1:5000/api/all-coins-data?limit=200')
    data = response.json()
    
    print(f"Status: {data.get('status')}")
    print(f"Total coins: {data.get('total_coins')}")
    
    if 'coins' in data:
        symbols = [coin['symbol'] for coin in data['coins']]
        print(f"Actual coins in database: {len(symbols)}")
        print("Sample symbols:", sorted(symbols)[:10])
        
        # Check for major coins
        major_coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        for coin in major_coins:
            if coin in symbols:
                print(f"✅ {coin} found")
            else:
                print(f"❌ {coin} not found yet")
                
        # Check if we have the B- prefix format
        print("\nChecking B- prefix format:")
        b_format_coins = ['B-BTC_USDT', 'B-ETH_USDT', 'B-SOL_USDT']
        for coin in b_format_coins:
            matching = [s for s in symbols if coin.replace('_', '/').replace('B-', '') in s]
            if matching:
                print(f"✅ Found similar: {matching}")
            else:
                print(f"❌ {coin} format not found")
    else:
        print("No coins data found")
        
except Exception as e:
    print(f"Error: {e}")