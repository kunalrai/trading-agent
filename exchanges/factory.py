"""
Exchange Factory for creating exchange instances
"""
import os
from typing import Optional
from .base_exchange import BaseExchange
from .coindcx_exchange import CoinDCXExchange


class ExchangeFactory:
    """Factory class for creating exchange instances"""
    
    SUPPORTED_EXCHANGES = {
       
        'coindcx': CoinDCXExchange
    }
    
    @classmethod
    def create_exchange(cls, exchange_name: Optional[str] = None) -> BaseExchange:
        """
        Create an exchange instance based on the exchange name
        
        Args:
            exchange_name: Name of the exchange ('binance', 'coindcx')
                          If None, will read from EXCHANGE environment variable
                          
        Returns:
            Exchange instance
            
        Raises:
            ValueError: If exchange is not supported
        """
        if exchange_name is None:
            exchange_name = os.getenv('EXCHANGE', 'binance').lower()
        
        exchange_name = exchange_name.lower().strip()
        
        if exchange_name not in cls.SUPPORTED_EXCHANGES:
            supported = ', '.join(cls.SUPPORTED_EXCHANGES.keys())
            raise ValueError(
                f"Unsupported exchange: '{exchange_name}'. "
                f"Supported exchanges: {supported}"
            )
        
        exchange_class = cls.SUPPORTED_EXCHANGES[exchange_name]
        exchange_instance = exchange_class()
        
        print(f"INFO: Creating {exchange_instance.get_name()} exchange instance")
        
        # Initialize the exchange
        exchange_instance.initialize()
        
        return exchange_instance
    
    @classmethod
    def get_supported_exchanges(cls) -> list:
        """Get list of supported exchange names"""
        return list(cls.SUPPORTED_EXCHANGES.keys())
    
    @classmethod
    def is_supported(cls, exchange_name: str) -> bool:
        """Check if an exchange is supported"""
        return exchange_name.lower() in cls.SUPPORTED_EXCHANGES