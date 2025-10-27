# CoinDCX API Integration Guide

This guide explains how to use the enhanced CoinDCX API integration in the SolSignals project to fetch comprehensive market data.

## Overview

The CoinDCX exchange implementation provides access to both **spot** and **futures** market data from CoinDCX, including:

- Real-time price data
- Historical candlestick data (OHLCV)
- Market information and trading pairs
- Order book data
- Trade history
- Futures instruments and prices
- Symbol search and validation

## Features

### 🚀 **Core Features**

1. **Market Data Access**
   - Comprehensive market listing
   - Real-time ticker data
   - Price change tracking
   - Volume analysis

2. **Price & Candlestick Data**
   - Latest OHLCV candles
   - Historical data for technical analysis
   - Multiple timeframes (1m, 5m, 15m, 30m, 1h, 4h, 1d)
   - Automatic fallback (Futures → Spot)

3. **Advanced Features**
   - Order book depth
   - Recent trade history
   - Symbol search functionality
   - Market validation

4. **Futures Support**
   - Futures instruments listing
   - Real-time futures prices
   - Cross-margin details
   - Position data (with authentication)

## Quick Start

### Basic Usage

```python
from exchanges.coindcx_exchange import CoinDCXExchange

# Initialize exchange
exchange = CoinDCXExchange()
exchange.initialize()

# Get latest price for SOL/USDT
ohlcv = exchange.get_latest_ohlcv('SOL/USDT', '15m')
current_price = ohlcv[4]  # Close price
print(f"SOL/USDT: ${current_price:.4f}")

# Get historical data for EMA calculation
historical_data = exchange.get_historical_data('SOL/USDT', '15m', limit=50)
closes = [candle[4] for candle in historical_data]
print(f"Retrieved {len(closes)} price points")
```

### With Authentication (Optional)

```python
# For authenticated endpoints (account data, trading)
exchange = CoinDCXExchange(
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# Get account balances
balances = exchange.get_account_balances()
```

## API Reference

### Core Methods

#### `get_latest_ohlcv(symbol, timeframe='15m')`
Get the latest OHLCV candle data.

**Parameters:**
- `symbol` (str): Trading pair (e.g., 'SOL/USDT', 'BTC/USDT')
- `timeframe` (str): Candle timeframe ('1m', '5m', '15m', '30m', '1h', '4h', '1d')

**Returns:** `List[float]` - [timestamp, open, high, low, close, volume]

**Example:**
```python
ohlcv = exchange.get_latest_ohlcv('SOL/USDT', '15m')
print(f"Close: ${ohlcv[4]:.4f}")
```

#### `get_historical_data(symbol, timeframe='15m', limit=50)`
Get historical OHLCV data for technical analysis.

**Parameters:**
- `symbol` (str): Trading pair
- `timeframe` (str): Candle timeframe
- `limit` (int): Number of candles to retrieve

**Returns:** `List[List[float]]` - Array of OHLCV candles

**Example:**
```python
candles = exchange.get_historical_data('SOL/USDT', '15m', limit=100)
for candle in candles[-5:]:  # Last 5 candles
    print(f"Close: ${candle[4]:.4f}")
```

#### `get_ticker(symbol)`
Get current ticker information.

**Parameters:**
- `symbol` (str): Trading pair

**Returns:** `Dict` - Ticker data including price, volume, change%

**Example:**
```python
ticker = exchange.get_ticker('SOL/USDT')
print(f"Price: ${ticker['last_price']:.4f}")
print(f"24h Change: {ticker['price_change_percent']:.2f}%")
print(f"Source: {ticker['source']}")  # 'futures' or 'spot'
```

### Market Information

#### `get_markets()`
Get all available trading markets.

**Returns:** `Dict[str, Any]` - Market information dictionary

**Example:**
```python
markets = exchange.get_markets()
print(f"Total markets: {len(markets)}")

# Check if symbol exists
if 'SOL/USDT' in markets:
    market_info = markets['SOL/USDT']
    print(f"Min quantity: {market_info.get('min_quantity')}")
```

#### `search_symbols(query)`
Search for symbols matching a query.

**Parameters:**
- `query` (str): Search term

**Returns:** `List[str]` - Matching symbols

**Example:**
```python
sol_symbols = exchange.search_symbols('SOL')
print(f"SOL markets: {sol_symbols}")

usdt_pairs = exchange.search_symbols('USDT')
print(f"USDT pairs: {usdt_pairs[:10]}")  # First 10
```

#### `validate_symbol(symbol)`
Check if a symbol is valid and tradeable.

**Parameters:**
- `symbol` (str): Symbol to validate

**Returns:** `bool` - True if valid

**Example:**
```python
is_valid = exchange.validate_symbol('SOL/USDT')
print(f"SOL/USDT valid: {is_valid}")
```

### Advanced Features

#### `get_orderbook(symbol, depth=50)`
Get order book data.

**Parameters:**
- `symbol` (str): Trading pair
- `depth` (int): Order book depth (10, 20, or 50)

**Returns:** `Dict` - Order book with bids and asks

**Example:**
```python
orderbook = exchange.get_orderbook('SOL/USDT')
bids = list(orderbook['bids'].items())[:5]  # Top 5 bids
asks = list(orderbook['asks'].items())[:5]  # Top 5 asks

print("Top Bids:")
for price, quantity in bids:
    print(f"  ${price} - {quantity}")
```

#### `get_trade_history(symbol, limit=50)`
Get recent trade history.

**Parameters:**
- `symbol` (str): Trading pair
- `limit` (int): Number of trades (max 500)

**Returns:** `List[Dict]` - Recent trades

**Example:**
```python
trades = exchange.get_trade_history('SOL/USDT', limit=10)
for trade in trades:
    price = trade.get('p', 0)
    quantity = trade.get('q', 0)
    print(f"Trade: ${price} x {quantity}")
```

### Futures Data

#### `get_futures_instruments(margin_currency='USDT')`
Get available futures instruments.

**Parameters:**
- `margin_currency` (str): 'USDT' or 'INR'

**Returns:** `List[Dict]` - Futures instruments

**Example:**
```python
instruments = exchange.get_futures_instruments()
for instrument in instruments[:5]:
    print(f"Futures: {instrument.get('pair')} - {instrument.get('status')}")
```

#### `get_futures_prices()`
Get real-time futures prices.

**Returns:** `Dict` - Futures price data

**Example:**
```python
futures_data = exchange.get_futures_prices()
if 'prices' in futures_data:
    sol_futures = futures_data['prices'].get('B-SOL_USDT', {})
    if sol_futures:
        price = sol_futures.get('ls', 0)  # Last price
        change = sol_futures.get('pc', 0)  # Price change %
        print(f"SOL Futures: ${price} ({change:+.2f}%)")
```

## Symbol Format Conversion

The exchange automatically converts between standard and CoinDCX formats:

| Standard Format | CoinDCX Format | Type |
|----------------|----------------|------|
| SOL/USDT       | B-SOL_USDT     | Futures |
| SOL/USDT       | SOLUSDT        | Spot |
| BTC/USDT       | B-BTC_USDT     | Futures |
| ETH/USDT       | B-ETH_USDT     | Futures |

## Timeframe Support

| Timeframe | CoinDCX Futures | CoinDCX Spot |
|-----------|----------------|--------------|
| 1m        | ✅ '1'         | ✅ '1m'      |
| 5m        | ✅ '5'         | ✅ '5m'      |
| 15m       | ✅ '15'        | ✅ '15m'     |
| 30m       | ✅ '30'        | ✅ '30m'     |
| 1h        | ✅ '60'        | ✅ '1h'      |
| 4h        | ✅ '240'       | ✅ '4h'      |
| 1d        | ✅ '1D'        | ✅ '1d'      |

## Error Handling

The exchange includes comprehensive error handling:

```python
try:
    ohlcv = exchange.get_latest_ohlcv('SOL/USDT', '15m')
    print(f"Success: ${ohlcv[4]:.4f}")
except Exception as e:
    print(f"Error: {e}")
    # Handle error appropriately
```

Common error scenarios:
- Network connectivity issues
- Invalid symbols
- API rate limits
- Missing data
- Invalid timeframes

## Testing Scripts

### Basic API Test

```bash
# Test all CoinDCX API functionality
python test_coindcx_api.py
```

### Live Market Monitor

```bash
# Continuous monitoring
python coindcx_live_monitor.py

# Demo mode (3 updates)
python coindcx_live_monitor.py demo

# Single update
python coindcx_live_monitor.py single
```

## Environment Configuration

Add to your `.env` file:

```env
# Optional: CoinDCX API credentials (for authenticated endpoints)
COINDCX_API_KEY=your_api_key_here
COINDCX_API_SECRET=your_api_secret_here

# Exchange selection
EXCHANGE=coindcx
```

## Integration with Main App

The main SolSignals app automatically uses CoinDCX when configured:

```bash
# Set exchange in environment
export EXCHANGE=coindcx

# Run the main monitoring script
python app.py
```

## API Rate Limits

CoinDCX has rate limits on their API:
- **Public endpoints**: Generally more permissive
- **Authenticated endpoints**: More restrictive
- **Recommended**: Add delays between requests for production use

## Troubleshooting

### Common Issues

1. **Connection Errors**
   ```python
   # Test basic connectivity
   if not exchange.test_connection():
       print("Check internet connection and CoinDCX API status")
   ```

2. **Symbol Not Found**
   ```python
   # Validate symbol first
   if not exchange.validate_symbol('SYMBOL/USDT'):
       print("Symbol not available on CoinDCX")
       
   # Search for similar symbols
   results = exchange.search_symbols('SYMBOL')
   print(f"Similar symbols: {results}")
   ```

3. **No Data Returned**
   ```python
   # Try different timeframes
   timeframes = ['15m', '1h', '1d']
   for tf in timeframes:
       try:
           data = exchange.get_latest_ohlcv('SOL/USDT', tf)
           print(f"Success with {tf}: ${data[4]:.4f}")
           break
       except Exception as e:
           print(f"Failed with {tf}: {e}")
   ```

4. **Futures vs Spot Data**
   ```python
   # The exchange automatically tries futures first, then spot
   # Check the ticker source to see which was used
   ticker = exchange.get_ticker('SOL/USDT')
   print(f"Data source: {ticker.get('source', 'unknown')}")
   ```

### Debug Mode

Enable verbose logging in the main app:

```env
VERBOSE_LOGGING=true
```

## Best Practices

1. **Cache Market Data**: Markets don't change frequently
2. **Handle Rate Limits**: Add appropriate delays
3. **Validate Symbols**: Check symbol validity before use
4. **Error Recovery**: Implement retry logic for network issues
5. **Fallback Strategy**: Use both futures and spot data sources
6. **Monitor API Health**: Regular connection testing

## Examples

See the included example scripts:
- `test_coindcx_api.py` - Comprehensive API testing
- `coindcx_live_monitor.py` - Live market monitoring
- `app.py` - Main trading signal detection

These demonstrate real-world usage patterns and best practices for the CoinDCX API integration.