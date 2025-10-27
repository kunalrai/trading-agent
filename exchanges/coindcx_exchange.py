"""
CoinDCX Exchange implementation using direct HTTP API calls
"""
import requests
import time
import hmac
import hashlib
import json
from typing import List, Optional, Dict, Any
from .base_exchange import BaseExchange


class CoinDCXExchange(BaseExchange):
    """CoinDCX exchange implementation using direct HTTP API calls"""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        super().__init__()
        # CoinDCX API endpoints
        self.base_url = "https://api.coindcx.com"
        self.public_url = "https://public.coindcx.com"
        self.name = "CoinDCX"
        self.exchange = None  # Not using ccxt
        
        # API credentials (optional - needed for authenticated endpoints)
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Cache for markets to reduce API calls
        self._markets_cache = None
        self._markets_cache_time = 0
        self._cache_duration = 300  # 5 minutes
        
        # Map common symbols to CoinDCX futures format  
        self.symbol_map = {
            'SOL/USDT': 'B-SOL_USDT',
            'BTC/USDT': 'B-BTC_USDT',
            'ETH/USDT': 'B-ETH_USDT',
            'BNB/USDT': 'B-BNB_USDT',
            'ADA/USDT': 'B-ADA_USDT',
            'DOT/USDT': 'B-DOT_USDT',
            'MATIC/USDT': 'B-MATIC_USDT',
            'LTC/USDT': 'B-LTC_USDT',
            'AVAX/USDT': 'B-AVAX_USDT',
            'ATOM/USDT': 'B-ATOM_USDT'
        }
        
        # Map timeframes to CoinDCX futures resolution (for candlesticks)
        self.timeframe_map = {
            '1m': '1',
            '5m': '5', 
            '15m': '15',
            '30m': '30',
            '1h': '60',
            '4h': '240',
            '1d': '1D'
        }
    
    def initialize(self) -> None:
        """Initialize CoinDCX connection by testing futures API"""
        try:
            # Test connection with markets endpoint first
            markets = self.get_markets()
            print(f"SUCCESS: Connected to CoinDCX API ({len(markets)} markets available)")
            
        except Exception as e:
            print(f"ERROR: Failed to connect to CoinDCX API: {e}")
            raise Exception("Unable to connect to CoinDCX API")
    
    def get_markets(self) -> Dict[str, Any]:
        """Get all available markets from CoinDCX"""
        try:
            # Check cache first
            current_time = time.time()
            if (self._markets_cache and 
                current_time - self._markets_cache_time < self._cache_duration):
                return self._markets_cache
            
            # Fetch market details from CoinDCX
            url = f"{self.base_url}/exchange/v1/markets_details"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            markets_list = response.json()
            
            # Convert to dictionary for easier lookup
            markets = {}
            for market in markets_list:
                symbol = market.get('coindcx_name', '')
                # Convert to standard format (B-SOL_USDT -> SOL/USDT)
                if symbol.startswith('B-') and '_' in symbol:
                    parts = symbol[2:].split('_')
                    if len(parts) == 2:
                        standard_symbol = f"{parts[0]}/{parts[1]}"
                        markets[standard_symbol] = market
                
                # Also store with original CoinDCX format
                markets[symbol] = market
            
            # Update cache
            self._markets_cache = markets
            self._markets_cache_time = current_time
            
            return markets
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching markets: {e}")
        except Exception as e:
            raise Exception(f"Error fetching markets: {e}")
    
    def get_market_data(self, symbol: str = None) -> Dict[str, Any]:
        """Get comprehensive market data including tickers"""
        try:
            # Get ticker data
            url = f"{self.base_url}/exchange/ticker"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            tickers = response.json()
            
            if symbol:
                # Filter for specific symbol
                dcx_symbol = self._convert_symbol(symbol)
                for ticker in tickers:
                    if ticker.get('market') == dcx_symbol:
                        return ticker
                raise Exception(f"Market data not found for {symbol}")
            
            return tickers
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching market data: {e}")
        except Exception as e:
            raise Exception(f"Error fetching market data: {e}")
    
    def get_orderbook(self, symbol: str, depth: int = 50) -> Dict[str, Any]:
        """Get orderbook for a symbol"""
        try:
            dcx_symbol = self._convert_symbol(symbol)
            
            # Use public orderbook endpoint
            url = f"{self.public_url}/market_data/orderbook"
            params = {'pair': dcx_symbol}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching orderbook: {e}")
        except Exception as e:
            raise Exception(f"Error fetching orderbook: {e}")
    
    def get_trade_history(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trade history for a symbol"""
        try:
            dcx_symbol = self._convert_symbol(symbol)
            
            # Use public trade history endpoint
            url = f"{self.public_url}/market_data/trade_history"
            params = {
                'pair': dcx_symbol,
                'limit': min(limit, 500)  # CoinDCX max is 500
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching trade history: {e}")
        except Exception as e:
            raise Exception(f"Error fetching trade history: {e}")
    
    def _create_signature(self, payload: str) -> str:
        """Create HMAC-SHA256 signature for authenticated requests"""
        if not self.api_secret:
            raise Exception("API secret required for authenticated requests")
        
        secret_bytes = bytes(self.api_secret, encoding='utf-8')
        return hmac.new(secret_bytes, payload.encode(), hashlib.sha256).hexdigest()
    
    def _make_authenticated_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make an authenticated request to CoinDCX API"""
        if not self.api_key or not self.api_secret:
            raise Exception("API key and secret required for authenticated requests")
        
        # Add timestamp
        data['timestamp'] = int(time.time() * 1000)
        
        # Create payload and signature
        json_body = json.dumps(data, separators=(',', ':'))
        signature = self._create_signature(json_body)
        
        # Set headers
        headers = {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': self.api_key,
            'X-AUTH-SIGNATURE': signature
        }
        
        # Make request
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, data=json_body, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    def get_account_balances(self) -> List[Dict[str, Any]]:
        """Get account balances (requires authentication)"""
        try:
            data = {}
            return self._make_authenticated_request('/exchange/v1/users/balances', data)
            
        except Exception as e:
            raise Exception(f"Error fetching account balances: {e}")
    
    def get_futures_instruments(self, margin_currency: str = 'USDT') -> List[Dict[str, Any]]:
        """Get futures active instruments"""
        try:
            url = f"{self.base_url}/exchange/v1/derivatives/futures/data/active_instruments"
            params = {'margin_currency_short_name[]': margin_currency}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching futures instruments: {e}")
        except Exception as e:
            raise Exception(f"Error fetching futures instruments: {e}")
    
    def get_current_prices(self) -> Dict[str, Any]:
        """Get current futures prices (real-time)"""
        try:
            url = f"{self.public_url}/market_data/v3/current_prices/futures/rt"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'prices' in data:
                return data['prices']
            
            return {}
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching futures prices: {e}")
        except Exception as e:
            raise Exception(f"Error fetching futures prices: {e}")
    
    def _convert_symbol_format(self, symbol: str) -> str:
        """Convert standard symbol format to CoinDCX futures format"""
        if symbol in self.symbol_map:
            return self.symbol_map[symbol]
        
        # If not in map, try to convert automatically
        # Example: 'SOL/USDT' -> 'B-SOL_USDT'
        if '/' in symbol:
            base, quote = symbol.split('/')
            return f"B-{base}_{quote}"
        
        return symbol
    
    def get_latest_ohlcv(self, symbol: str, timeframe: str = '15m') -> List[float]:
        """Fetch the latest OHLCV candle data from CoinDCX"""
        try:
            # Convert symbol to CoinDCX futures format
            dcx_symbol = self._convert_symbol_format(symbol)
            
            # Try futures real-time prices first
            try:
                current_prices = self.get_current_prices()
                if dcx_symbol in current_prices:
                    price_info = current_prices[dcx_symbol]
                    current_price = float(price_info.get('ls', 0))  # last price
                    high_24h = float(price_info.get('h', current_price))  # 24h high
                    low_24h = float(price_info.get('l', current_price))   # 24h low
                    volume_24h = float(price_info.get('v', 0))            # 24h volume
                    
                    # Return as OHLCV format [timestamp, open, high, low, close, volume]
                    return [
                        int(time.time() * 1000),  # current timestamp
                        current_price,            # open (use current as approximation)
                        high_24h,                 # high
                        low_24h,                  # low
                        current_price,            # close
                        volume_24h                # volume
                    ]
            except Exception as e:
                print(f"Futures real-time data failed: {e}")
            
            # Fall back to futures candlesticks API
            try:
                return self._get_latest_ohlcv_futures(dcx_symbol, timeframe)
            except Exception as e:
                print(f"Futures candlesticks failed: {e}")
                # Fall back to spot candlesticks
                return self._get_latest_ohlcv_spot(dcx_symbol, timeframe)
                
        except Exception as e:
            raise Exception(f"Error fetching latest OHLCV: {e}")
    
    def _get_latest_ohlcv_futures(self, dcx_symbol: str, timeframe: str) -> List[float]:
        """Get latest OHLCV from futures API"""
        resolution = self._convert_timeframe(timeframe)
        
        # Calculate time range for latest candle
        current_time = int(time.time())
        candle_duration = self._get_candle_duration(timeframe)
        start_time = current_time - (candle_duration * 2)
        end_time = current_time
        
        # CoinDCX futures candlesticks endpoint
        url = f"{self.public_url}/market_data/candlesticks"
        params = {
            'pair': dcx_symbol,
            'from': start_time,
            'to': end_time,
            'resolution': resolution,
            'pcode': 'f'  # 'f' denotes futures
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data or data.get('s') != 'ok' or not data.get('data'):
            raise Exception("No futures candle data received")
        
        # Get the latest candle
        candles = data['data']
        latest_candle = candles[-1]
        
        return [
            latest_candle['time'],           # timestamp
            float(latest_candle['open']),    # open
            float(latest_candle['high']),    # high  
            float(latest_candle['low']),     # low
            float(latest_candle['close']),   # close
            float(latest_candle['volume'])   # volume
        ]
    
    def _get_latest_ohlcv_spot(self, dcx_symbol: str, timeframe: str) -> List[float]:
        """Get latest OHLCV from spot candles API"""
        # For spot, we'll use different interval mapping
        interval_map = {
            '1m': '1m',
            '5m': '5m', 
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        interval = interval_map.get(timeframe, '15m')
        
        # Use public candles endpoint for spot
        url = f"{self.public_url}/market_data/candles"
        params = {
            'pair': dcx_symbol,
            'interval': interval,
            'limit': 1  # Just get the latest candle
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data or not isinstance(data, list) or len(data) == 0:
            raise Exception("No spot candle data received")
        
        # Get the latest candle
        latest_candle = data[-1]
        
        return [
            latest_candle['time'],           # timestamp
            float(latest_candle['open']),    # open
            float(latest_candle['high']),    # high  
            float(latest_candle['low']),     # low
            float(latest_candle['close']),   # close
            float(latest_candle['volume'])   # volume
        ]
    
    def get_historical_data(self, symbol: str, timeframe: str = '15m', limit: int = 50) -> List[List[float]]:
        """Fetch historical OHLCV data for EMA calculation from CoinDCX"""
        try:
            # Convert symbol to CoinDCX format
            dcx_symbol = self._convert_symbol(symbol)
            
            # Try futures first, then fall back to spot
            try:
                return self._get_historical_data_futures(dcx_symbol, timeframe, limit)
            except Exception:
                # Fall back to spot candlesticks
                return self._get_historical_data_spot(dcx_symbol, timeframe, limit)
                
        except Exception as e:
            raise Exception(f"Error fetching historical data: {e}")
    
    def _get_historical_data_futures(self, dcx_symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        """Get historical data from futures API"""
        resolution = self._convert_timeframe(timeframe)
        
        # Calculate time range for historical data
        current_time = int(time.time())
        candle_duration = self._get_candle_duration(timeframe)
        start_time = current_time - (candle_duration * limit * 2)
        end_time = current_time
        
        # CoinDCX futures candlesticks endpoint
        url = f"{self.public_url}/market_data/candlesticks"
        params = {
            'pair': dcx_symbol,
            'from': start_time,
            'to': end_time,
            'resolution': resolution,
            'pcode': 'f'  # 'f' denotes futures
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data or data.get('s') != 'ok' or not data.get('data'):
            raise Exception("No futures historical data received")
        
        candle_data = data['data']
        
        if len(candle_data) < limit:
            print(f"WARNING: Only {len(candle_data)} candles available, requested {limit}")
        
        # Convert to standard format and take the latest 'limit' candles
        candles = []
        for candle in candle_data[-limit:]:
            ohlcv = [
                candle['time'],           # timestamp
                float(candle['open']),    # open
                float(candle['high']),    # high
                float(candle['low']),     # low
                float(candle['close']),   # close
                float(candle['volume'])   # volume
            ]
            candles.append(ohlcv)
        
        # Sort by timestamp (oldest first) for EMA calculation
        candles.sort(key=lambda x: x[0])
        return candles
    
    def _get_historical_data_spot(self, dcx_symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        """Get historical data from spot candles API"""
        # For spot, we'll use different interval mapping
        interval_map = {
            '1m': '1m',
            '5m': '5m', 
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        interval = interval_map.get(timeframe, '15m')
        
        # Use public candles endpoint for spot
        url = f"{self.public_url}/market_data/candles"
        params = {
            'pair': dcx_symbol,
            'interval': interval,
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data or not isinstance(data, list):
            raise Exception("No spot historical data received")
        
        if len(data) < limit:
            print(f"WARNING: Only {len(data)} candles available, requested {limit}")
        
        # Convert to standard format
        candles = []
        for candle in data:
            ohlcv = [
                candle['time'],           # timestamp
                float(candle['open']),    # open
                float(candle['high']),    # high
                float(candle['low']),     # low
                float(candle['close']),   # close
                float(candle['volume'])   # volume
            ]
            candles.append(ohlcv)
        
        # Sort by timestamp (oldest first) for EMA calculation
        candles.sort(key=lambda x: x[0])
        return candles
    
    def test_connection(self) -> bool:
        """Test connection to CoinDCX API"""
        try:
            # Test with markets endpoint first
            url = f"{self.base_url}/exchange/v1/markets"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            markets = response.json()
            print(f"SUCCESS: CoinDCX connection test passed ({len(markets)} markets available)")
            return True
            
        except Exception as e:
            print(f"ERROR: CoinDCX connection test failed: {e}")
            return False
    
    def _convert_symbol(self, symbol: str) -> str:
        """Convert common symbol format to CoinDCX format"""
        if symbol in self.symbol_map:
            return self.symbol_map[symbol]
        
        # If not in map, try to convert automatically
        # Example: 'ETH/USDT' -> 'B-ETH_USDT' for futures or 'ETHUSDT' for spot
        if '/' in symbol:
            base, quote = symbol.split('/')
            # Try futures format first
            return f"B-{base}_{quote}"
        
        return symbol
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert common timeframe to CoinDCX futures resolution"""
        if timeframe in self.timeframe_map:
            return self.timeframe_map[timeframe]
        
        return timeframe
    
    def _get_candle_duration(self, timeframe: str) -> int:
        """Get candle duration in seconds for time range calculations"""
        duration_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        return duration_map.get(timeframe, 900)  # Default to 15min
    
    def format_symbol(self, symbol: str) -> str:
        """Format symbol for CoinDCX (backward compatibility)"""
        return self._convert_symbol(symbol)
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if a trading symbol is supported on CoinDCX"""
        try:
            # Check markets cache or fetch markets
            markets = self.get_markets()
            dcx_symbol = self._convert_symbol(symbol)
            
            # Check if symbol exists in any format
            return (symbol in markets or 
                    dcx_symbol in markets or
                    any(dcx_symbol in str(market) for market in markets.values()))
            
        except Exception:
            return True  # Assume valid if validation fails
    
    def get_ticker(self, symbol: str) -> dict:
        """Get current ticker data"""
        try:
            dcx_symbol = self._convert_symbol(symbol)
            
            # Try futures real-time prices first
            try:
                url = f"{self.public_url}/market_data/v3/current_prices/futures/rt"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if 'prices' in data and dcx_symbol in data['prices']:
                    ticker_data = data['prices'][dcx_symbol]
                    return {
                        'symbol': symbol,
                        'last_price': float(ticker_data.get('ls', 0)),
                        'high': float(ticker_data.get('h', 0)),
                        'low': float(ticker_data.get('l', 0)),
                        'volume': float(ticker_data.get('v', 0)),
                        'price_change_percent': float(ticker_data.get('pc', 0)),
                        'mark_price': float(ticker_data.get('mp', 0)),
                        'timestamp': data.get('ts', int(time.time() * 1000)),
                        'source': 'futures'
                    }
            except Exception:
                pass
            
            # Fall back to spot ticker
            url = f"{self.base_url}/exchange/ticker"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            tickers = response.json()
            
            # Look for matching ticker
            for ticker in tickers:
                if ticker.get('market') == dcx_symbol or ticker.get('market') == symbol:
                    return {
                        'symbol': symbol,
                        'last_price': float(ticker.get('last_price', 0)),
                        'high': float(ticker.get('high', 0)),
                        'low': float(ticker.get('low', 0)),
                        'volume': float(ticker.get('volume', 0)),
                        'price_change_percent': float(ticker.get('change_24_hour', 0)),
                        'bid': float(ticker.get('bid', 0)),
                        'ask': float(ticker.get('ask', 0)),
                        'timestamp': ticker.get('timestamp', int(time.time() * 1000)),
                        'source': 'spot'
                    }
            
            raise Exception(f"Ticker not found for symbol {symbol}")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching ticker: {e}")
        except Exception as e:
            raise Exception(f"Error fetching ticker: {e}")
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get detailed information about a trading symbol"""
        try:
            markets = self.get_markets()
            
            # Check if symbol exists in markets
            if symbol in markets:
                return markets[symbol]
            
            dcx_symbol = self._convert_symbol(symbol)
            if dcx_symbol in markets:
                return markets[dcx_symbol]
            
            # Search for partial matches
            for market_symbol, market_info in markets.items():
                if (symbol.replace('/', '').lower() in market_symbol.lower() or
                    dcx_symbol.lower() in market_symbol.lower()):
                    return market_info
            
            raise Exception(f"Symbol information not found for {symbol}")
            
        except Exception as e:
            raise Exception(f"Error fetching symbol info: {e}")
    
    def search_symbols(self, query: str) -> List[str]:
        """Search for symbols matching a query"""
        try:
            markets = self.get_markets()
            query_lower = query.lower()
            
            matching_symbols = []
            for symbol in markets.keys():
                if query_lower in symbol.lower():
                    # Convert to standard format if it's a CoinDCX format
                    if symbol.startswith('B-') and '_' in symbol:
                        parts = symbol[2:].split('_')
                        if len(parts) == 2:
                            standard_symbol = f"{parts[0]}/{parts[1]}"
                            matching_symbols.append(standard_symbol)
                    else:
                        matching_symbols.append(symbol)
            
            return list(set(matching_symbols))  # Remove duplicates
            
        except Exception as e:
            print(f"Error searching symbols: {e}")
            return []