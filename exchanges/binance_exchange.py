"""
Binance Exchange implementation
"""
import ccxt
import os
from typing import List, Optional
from .base_exchange import BaseExchange


class BinanceExchange(BaseExchange):
    """Binance exchange implementation using ccxt"""
    
    def __init__(self):
        super().__init__()
        self.name = "Binance"
        self.exchange = None
    
    def initialize(self) -> None:
        """Initialize Binance exchange connection"""
        # First try without API credentials (public data only)
        public_config = {
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'defaultType': 'spot',  # spot, margin, future, delivery
            }
        }
        
        try:
            self.exchange = ccxt.binance(public_config)
            # Test connection with public endpoint
            markets = self.exchange.load_markets()
            print("SUCCESS: Connected to Binance (public data mode)")
            return
        except Exception as public_error:
            print(f"WARNING: Public connection failed: {public_error}")
            
            # If public connection fails, try with API credentials
            api_key = os.getenv('BINANCE_API_KEY', '')
            secret_key = os.getenv('BINANCE_SECRET_KEY', '')
            
            if api_key and secret_key:
                print("INFO: Trying with API credentials...")
                auth_config = {
                    'apiKey': api_key,
                    'secret': secret_key,
                    'sandbox': os.getenv('BINANCE_SANDBOX', 'false').lower() == 'true',
                    'enableRateLimit': True,
                    'timeout': 30000,
                    'options': {
                        'defaultType': 'spot',
                    }
                }
                
                try:
                    self.exchange = ccxt.binance(auth_config)
                    self.exchange.load_markets()
                    print(f"SUCCESS: Connected to Binance with API credentials ({'Testnet' if auth_config.get('sandbox') else 'Mainnet'})")
                    return
                except Exception as auth_error:
                    print(f"ERROR: API credentials failed: {auth_error}")
                    print("INFO: Falling back to public-only mode...")
                    
            # Final fallback: minimal public config without market loading
            try:
                self.exchange = ccxt.binance({'enableRateLimit': True})
                print("SUCCESS: Connected to Binance (minimal public mode)")
                return
            except Exception as final_error:
                print(f"ERROR: All connection attempts failed: {final_error}")
                raise Exception("Unable to connect to Binance API")
    
    def get_latest_ohlcv(self, symbol: str, timeframe: str = '15m') -> List[float]:
        """Fetch the latest OHLCV candle data from Binance"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=1)
            if not ohlcv:
                raise Exception("No data received")
            return ohlcv[-1]  # latest candle
        except Exception as e:
            print(f"ERROR: Failed to fetch OHLCV data for {symbol}: {e}")
            raise
    
    def get_historical_data(self, symbol: str, timeframe: str = '15m', limit: int = 50) -> List[List[float]]:
        """Fetch historical OHLCV data from Binance"""
        try:
            candles = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if len(candles) < limit:
                print(f"WARNING: Only {len(candles)} candles available, requested {limit}")
            return candles
        except Exception as e:
            print(f"ERROR: Failed to fetch historical data for {symbol}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test Binance connection"""
        try:
            if self.exchange:
                # Try to fetch server time as a simple connection test
                self.exchange.fetch_time()
                return True
            return False
        except Exception:
            return False
    
    def format_symbol(self, symbol: str) -> str:
        """Format symbol for Binance (usually no change needed)"""
        return symbol.upper()  # Binance typically uses uppercase symbols