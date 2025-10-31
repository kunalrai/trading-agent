import requests
import json

try:
    response = requests.get('http://127.0.0.1:5000/api/all-coins-data?limit=10')
    data = response.json()
    
    print(f"Status: {data.get('status')}")
    print(f"Total coins: {data.get('total_coins')}")
    
    if 'coins' in data and len(data['coins']) > 0:
        print("\nFirst coin example:")
        first_coin = data['coins'][0]
        for key, value in first_coin.items():
            print(f"  {key}: {value}")
        
        # Check for major coins
        symbols = [coin['symbol'] for coin in data['coins']]
        major_coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        print(f"\nChecking for major coins in first {len(symbols)} results:")
        for coin in major_coins:
            if coin in symbols:
                print(f"✅ {coin} found")
            else:
                print(f"❌ {coin} not found in this batch")
                
        # Check updated time format
        print(f"\nChecking last_updated field:")
        for coin in data['coins'][:3]:
            print(f"  {coin['symbol']}: {coin.get('last_updated', 'MISSING')}")
                
    else:
        print("No coins data found")
        
except Exception as e:
    print(f"Error: {e}")