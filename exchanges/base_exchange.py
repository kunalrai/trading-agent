"""
Base Exchange class defining the common interface for all exchanges
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseExchange(ABC):
    """Abstract base class for cryptocurrency exchanges"""
    
    def __init__(self):
        self.exchange = None
        self.name = ""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the exchange connection"""
        pass
    
    @abstractmethod
    def get_latest_ohlcv(self, symbol: str, timeframe: str = '15m') -> List[float]:
        """
        Fetch the latest OHLCV candle data
        
        Args:
            symbol: Trading pair symbol (e.g., 'SOL/USDT')
            timeframe: Timeframe for candles (e.g., '15m', '1h')
            
        Returns:
            List containing [timestamp, open, high, low, close, volume]
        """
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str = '15m', limit: int = 50) -> List[List[float]]:
        """
        Fetch historical OHLCV data
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for candles
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV candles
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the exchange connection is working
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    def get_name(self) -> str:
        """Get the exchange name"""
        return self.name
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a trading symbol is supported
        
        Args:
            symbol: Trading pair symbol to validate
            
        Returns:
            True if symbol is valid, False otherwise
        """
        try:
            if self.exchange and hasattr(self.exchange, 'load_markets'):
                markets = self.exchange.load_markets()
                return symbol in markets
            return True  # Assume valid if we can't check
        except Exception:
            return True  # Assume valid if validation fails
    
    def format_symbol(self, symbol: str) -> str:
        """
        Format symbol according to exchange requirements
        Override in subclasses if needed
        
        Args:
            symbol: Raw symbol like 'SOL/USDT'
            
        Returns:
            Formatted symbol for the exchange
        """
        return symbol