#!/usr/bin/env python3
"""
Simple API wrapper for the EMA9 Backend
Provides easy-to-use functions for getting EMA9 data from CoinDCX
"""

from backend import EMA9Backend
import json
from typing import Dict, List, Optional


class EMA9API:
    """Simple API wrapper for EMA9Backend"""
    
    def __init__(self):
        """Initialize the API"""
        self.backend = EMA9Backend()
        self._initialized = False
    
    def _ensure_initialized(self) -> bool:
        """Ensure backend is initialized"""
        if not self._initialized:
            self._initialized = self.backend.initialize_exchange()
        return self._initialized
    
    def get_ema9_data(self) -> Dict:
        """
        Get complete EMA9 analysis data
        
        Returns:
            Dictionary with EMA9 analysis or error information
        """
        if not self._ensure_initialized():
            return {'error': 'Failed to initialize exchange connection'}
        
        return self.backend.calculate_ema9_data()
    
    def get_current_signal(self) -> Dict:
        """
        Get current trading signal based on EMA9
        
        Returns:
            Dictionary with signal information
        """
        data = self.get_ema9_data()
        if 'error' in data:
            return data
        
        return {
            'symbol': data['symbol'],
            'signal_type': data['signal']['type'],
            'signal_strength': data['signal']['strength'],
            'confidence': data['signal']['confidence'],
            'recommendation': data['signal']['recommendation'],
            'reasons': data['signal']['reasons'],
            'timestamp': data['timestamp']
        }
    
    def get_price_vs_ema9(self) -> Dict:
        """
        Get current price vs EMA9 comparison with all indicators
        
        Returns:
            Dictionary with price comparison and indicator data
        """
        data = self.get_ema9_data()
        if 'error' in data:
            return data
        
        return {
            'symbol': data['symbol'],
            'current_price': data['current_price'],
            'current_ema9': data['current_ema9'],
            'current_macd': data['current_macd'],
            'current_rsi': data['current_rsi'],
            'gap_amount': data['price_to_ema_gap'],
            'gap_percentage': data['price_to_ema_percentage'],
            'position': data['position'],
            'ema_trend': data['ema_trend'],
            'timestamp': data['timestamp']
        }
    
    def get_quick_summary(self) -> Dict:
        """
        Get a quick summary with all indicators
        
        Returns:
            Simplified summary data with EMA9, MACD, RSI
        """
        if not self._ensure_initialized():
            return {'error': 'Failed to initialize exchange connection'}
        
        return self.backend.get_ema9_summary()
    
    def get_history(self, periods: int = 10) -> List[Dict]:
        """
        Get historical EMA9 data
        
        Args:
            periods: Number of historical periods to return
            
        Returns:
            List of historical EMA9 data points
        """
        if not self._ensure_initialized():
            return []
        
        return self.backend.get_ema9_history(periods=periods)
    
    def test_connection(self) -> Dict:
        """
        Test the API connection and configuration
        
        Returns:
            Test results
        """
        return self.backend.test_connection()
    
    def is_bullish(self) -> bool:
        """
        Check if current signal is bullish
        
        Returns:
            True if signal is bullish (BUY/STRONG_BUY)
        """
        signal = self.get_current_signal()
        if 'error' in signal:
            return False
        
        return signal['signal_type'] in ['BUY', 'STRONG_BUY']
    
    def is_bearish(self) -> bool:
        """
        Check if current signal is bearish
        
        Returns:
            True if signal is bearish (SELL/STRONG_SELL)
        """
        signal = self.get_current_signal()
        if 'error' in signal:
            return False
        
        return signal['signal_type'] in ['SELL', 'STRONG_SELL']
    
    def is_price_above_ema9(self) -> Optional[bool]:
        """
        Check if price is above EMA9
        
        Returns:
            True if above, False if below, None if error
        """
        data = self.get_price_vs_ema9()
        if 'error' in data:
            return None
        
        return data['position'] == 'above'
    
    def get_gap_percentage(self) -> Optional[float]:
        """
        Get the percentage gap between price and EMA20
        
        Returns:
            Gap percentage (positive if above EMA20, negative if below)
        """
        data = self.get_price_vs_ema9()
        if 'error' in data:
            return None
        
        return data['gap_percentage']
    
    def get_formatted_output(self) -> str:
        """
        Get comprehensive data in the exact requested format
        
        Returns:
            Formatted string output
        """
        if not self._ensure_initialized():
            return 'Error: Failed to initialize exchange connection'
        
        return self.backend.get_formatted_output()
    
    def get_trading_signal(self) -> Dict:
        """
        Get automated trading signal with entry, SL, TP levels
        
        Returns:
            Dictionary with complete trading signal
        """
        if not self._ensure_initialized():
            return {'error': 'Failed to initialize exchange connection'}
        
        return self.backend.generate_trading_signal()
    
    def get_formatted_trading_signal(self) -> str:
        """
        Get trading signal in formatted text
        
        Returns:
            Formatted trading signal with all levels and analysis
        """
        if not self._ensure_initialized():
            return 'Error: Failed to initialize exchange connection'
        
        return self.backend.get_formatted_trading_signal()
    
    def get_intraday_series_data(self) -> Dict:
        """
        Get intraday series data for comprehensive analysis
        
        Returns:
            Dictionary with price, EMA, MACD, RSI series data for last 10 minutes
        """
        if not self._ensure_initialized():
            return {'error': 'Failed to initialize exchange connection'}
        
        try:
            # Get the last 10 minutes of 1-minute candles for series analysis
            ohlcv_data = self.backend.exchange.fetch_ohlcv(
                symbol=self.backend.symbol,
                timeframe='1m',
                limit=10
            )
            
            if len(ohlcv_data) < 10:
                return {'error': 'Insufficient data for series analysis'}
            
            # Extract price series (close prices)
            price_series = [candle[4] for candle in ohlcv_data]  # Close prices
            
            # Calculate EMA20 for each candle (simplified - using expanding window)
            ema20_series = []
            ema20 = price_series[0]  # Start with first price
            alpha = 2 / (20 + 1)
            
            for price in price_series:
                ema20 = (price * alpha) + (ema20 * (1 - alpha))
                ema20_series.append(ema20)
            
            # Calculate simplified MACD series (12-26 EMA difference)
            macd_series = []
            ema12 = price_series[0]
            ema26 = price_series[0]
            alpha12 = 2 / (12 + 1)
            alpha26 = 2 / (26 + 1)
            
            for price in price_series:
                ema12 = (price * alpha12) + (ema12 * (1 - alpha12))
                ema26 = (price * alpha26) + (ema26 * (1 - alpha26))
                macd_series.append(ema12 - ema26)
            
            # Calculate RSI series (simplified 7 and 14 period)
            def calculate_rsi_series(prices, period):
                rsi_values = []
                gains = []
                losses = []
                
                for i in range(1, len(prices)):
                    change = prices[i] - prices[i-1]
                    if change > 0:
                        gains.append(change)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(change))
                
                # Simple RSI calculation for series
                for i in range(len(gains)):
                    if i < period - 1:
                        rsi_values.append(50)  # Neutral for insufficient data
                    else:
                        start_idx = max(0, i - period + 1)
                        avg_gain = sum(gains[start_idx:i+1]) / period
                        avg_loss = sum(losses[start_idx:i+1]) / period
                        
                        if avg_loss == 0:
                            rsi_values.append(100)
                        else:
                            rs = avg_gain / avg_loss
                            rsi = 100 - (100 / (1 + rs))
                            rsi_values.append(rsi)
                
                return rsi_values
            
            rsi7_series = calculate_rsi_series(price_series, 7)
            rsi14_series = calculate_rsi_series(price_series, 14)
            
            return {
                'price_series': price_series,
                'ema20_series': ema20_series,
                'macd_series': macd_series,
                'rsi7_series': rsi7_series,
                'rsi14_series': rsi14_series,
                'timestamp_series': [candle[0] for candle in ohlcv_data],  # Timestamps
                'data_length': len(price_series)
            }
            
        except Exception as e:
            return {'error': f'Failed to get intraday series: {str(e)}'}
    
    def get_longer_term_context(self) -> Dict:
        """
        Get longer-term context data (4H timeframe indicators)
        
        Returns:
            Dictionary with 4H timeframe analysis
        """
        if not self._ensure_initialized():
            return {'error': 'Failed to initialize exchange connection'}
        
        try:
            # Get 4H candles for longer-term context
            ohlcv_4h = self.backend.exchange.fetch_ohlcv(
                symbol=self.backend.symbol,
                timeframe='4h',
                limit=50  # Need enough data for EMAs and ATR
            )
            
            if len(ohlcv_4h) < 50:
                return {'error': 'Insufficient 4H data for context analysis'}
            
            # Extract close prices
            close_prices = [candle[4] for candle in ohlcv_4h]
            high_prices = [candle[2] for candle in ohlcv_4h]
            low_prices = [candle[3] for candle in ohlcv_4h]
            volumes = [candle[5] for candle in ohlcv_4h]
            
            # Calculate 4H EMA20 and EMA50
            def calculate_ema(prices, period):
                ema = prices[0]
                alpha = 2 / (period + 1)
                for price in prices[1:]:
                    ema = (price * alpha) + (ema * (1 - alpha))
                return ema
            
            ema20_4h = calculate_ema(close_prices, 20)
            ema50_4h = calculate_ema(close_prices, 50)
            
            # Calculate ATR (Average True Range)
            def calculate_atr(highs, lows, closes, period):
                true_ranges = []
                for i in range(1, len(closes)):
                    tr1 = highs[i] - lows[i]
                    tr2 = abs(highs[i] - closes[i-1])
                    tr3 = abs(lows[i] - closes[i-1])
                    true_ranges.append(max(tr1, tr2, tr3))
                
                # Calculate ATR for different periods
                if len(true_ranges) >= period:
                    return sum(true_ranges[-period:]) / period
                else:
                    return sum(true_ranges) / len(true_ranges)
            
            atr3_4h = calculate_atr(high_prices, low_prices, close_prices, 3)
            atr14_4h = calculate_atr(high_prices, low_prices, close_prices, 14)
            
            # Calculate 4H MACD
            ema12_4h = calculate_ema(close_prices, 12)
            ema26_4h = calculate_ema(close_prices, 26)
            macd_4h = ema12_4h - ema26_4h
            
            # Calculate 4H RSI(14)
            def calculate_rsi(prices, period):
                gains = []
                losses = []
                
                for i in range(1, len(prices)):
                    change = prices[i] - prices[i-1]
                    if change > 0:
                        gains.append(change)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(change))
                
                if len(gains) >= period:
                    avg_gain = sum(gains[-period:]) / period
                    avg_loss = sum(losses[-period:]) / period
                    
                    if avg_loss == 0:
                        return 100
                    else:
                        rs = avg_gain / avg_loss
                        return 100 - (100 / (1 + rs))
                else:
                    return 50  # Neutral if insufficient data
            
            rsi14_4h = calculate_rsi(close_prices, 14)
            
            # Calculate average volume
            avg_volume = sum(volumes[-20:]) / min(20, len(volumes))
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            return {
                'ema20_4h': ema20_4h,
                'ema50_4h': ema50_4h,
                'atr3_4h': atr3_4h,
                'atr14_4h': atr14_4h,
                'macd_4h': macd_4h,
                'rsi14_4h': rsi14_4h,
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'volume_ratio': volume_ratio,
                'candle_count': len(close_prices)
            }
            
        except Exception as e:
            return {'error': f'Failed to get longer-term context: {str(e)}'}


# Convenience functions for direct use
def get_ema9_data() -> Dict:
    """Get EMA9 data for the symbol in .env file"""
    api = EMA9API()
    return api.get_ema9_data()


def get_current_signal() -> Dict:
    """Get current trading signal"""
    api = EMA9API()
    return api.get_current_signal()


def get_price_vs_ema9() -> Dict:
    """Get price vs EMA9 comparison"""
    api = EMA9API()
    return api.get_price_vs_ema9()


def is_bullish() -> bool:
    """Check if current signal is bullish"""
    api = EMA9API()
    return api.is_bullish()


def is_bearish() -> bool:
    """Check if current signal is bearish"""
    api = EMA9API()
    return api.is_bearish()


def test_api() -> Dict:
    """Test the API connection"""
    api = EMA9API()
    return api.test_connection()


def get_trading_signal() -> Dict:
    """Get automated trading signal with TP/SL levels"""
    api = EMA9API()
    return api.get_trading_signal()


def get_trade_recommendation() -> str:
    """Get formatted trading recommendation"""
    api = EMA9API()
    return api.get_formatted_trading_signal()


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    print("EMA9 API - Quick Test")
    print("=" * 40)
    
    # Initialize API
    api = EMA9API()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            result = api.test_connection()
            print(json.dumps(result, indent=2))
        
        elif command == 'data':
            result = api.get_ema9_data()
            print(json.dumps(result, indent=2))
        
        elif command == 'signal':
            result = api.get_current_signal()
            print(json.dumps(result, indent=2))
        
        elif command == 'price':
            result = api.get_price_vs_ema9()
            print(json.dumps(result, indent=2))
        
        elif command == 'summary':
            result = api.get_quick_summary()
            print(json.dumps(result, indent=2))
        
        elif command == 'history':
            periods = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            result = api.get_history(periods)
            print(json.dumps(result, indent=2))
        
        elif command == 'bullish':
            result = api.is_bullish()
            print(f"Is Bullish: {result}")
        
        elif command == 'bearish':
            result = api.is_bearish()
            print(f"Is Bearish: {result}")
        
        elif command == 'above':
            result = api.is_price_above_ema9()
            print(f"Price above EMA9: {result}")
        
        elif command == 'gap':
            result = api.get_gap_percentage()
            print(f"Gap percentage: {result}%")
        
        elif command == 'formatted':
            result = api.get_formatted_output()
            print(result)
        
        elif command == 'trade':
            result = api.get_trading_signal()
            print(json.dumps(result, indent=2))
        
        elif command == 'trade-formatted':
            result = api.get_formatted_trading_signal()
            print(result)
        
        else:
            print(f"Unknown command: {command}")
            print("Available commands: test, data, signal, price, summary, history, bullish, bearish, above, gap, formatted, trade, trade-formatted")
    
    else:
        # Run quick summary by default
        print("Quick EMA9 Summary:")
        summary = api.get_quick_summary()
        print(json.dumps(summary, indent=2))
        
        print(f"\nUsage: python {sys.argv[0]} <command>")
        print("Commands: test, data, signal, price, summary, history, bullish, bearish, above, gap, formatted, trade, trade-formatted")