#!/usr/bin/env python3
"""
Backend API for CoinDCX EMA9 Data Analysis
Fetches 5-minute timeframe data for EMA9 calculations for the coin specified in .env
"""

import os
import time
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from exchanges.factory import ExchangeFactory

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("INFO: Loaded environment variables from .env file")
except ImportError:
    print("WARNING: python-dotenv not installed, using system environment variables only")
except Exception as e:
    print(f"WARNING: Could not load .env file: {e}")


class EMA9Backend:
    """Backend class for EMA9 analysis using CoinDCX 5-minute data"""
    
    def __init__(self):
        """Initialize the backend with configuration from .env"""
        # Load configuration from environment
        self.symbol = os.getenv('TRADING_SYMBOL', 'UNI/USDT')
        self.timeframe = '1m'   # Changed to 1-minute for intraday analysis
        self.ema_period_short = 20    # Changed to EMA20 as requested
        self.ema_period_long = 50     # For longer-term context
        self.exchange_name = os.getenv('EXCHANGE', 'coindcx')
        
        # Initialize exchange
        self.exchange = None
        self.last_update_time = None
        self.cached_data = None
        self.cache_duration = 60  # 1 minute cache for faster updates
        
        print(f"Enhanced Trading Backend initialized:")
        print(f"  Symbol: {self.symbol}")
        print(f"  Timeframe: {self.timeframe} (intraday)")
        print(f"  EMA Periods: {self.ema_period_short}, {self.ema_period_long}")
        print(f"  Exchange: {self.exchange_name}")
    
    def initialize_exchange(self):
        """Initialize the exchange connection"""
        try:
            if self.exchange is None:
                print("Initializing exchange connection...")
                self.exchange = ExchangeFactory.create_exchange()
                print(f"Successfully connected to {type(self.exchange).__name__}")
            return True
        except Exception as e:
            print(f"Error initializing exchange: {e}")
            return False
    
    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Exponential Moving Average
        
        Args:
            prices: List of closing prices
            period: EMA period (9 for EMA9)
            
        Returns:
            EMA value or None if insufficient data
        """
        if not prices or len(prices) < period:
            return None
        
        # Start with SMA for the first EMA value
        sma = sum(prices[:period]) / period
        ema = sma
        
        # Calculate multiplier: 2 / (period + 1)
        multiplier = 2 / (period + 1)
        
        # Calculate EMA for remaining prices
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_macd(self, prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Optional[Tuple[float, float, float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            prices: List of closing prices
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
            
        Returns:
            Tuple of (MACD line, Signal line, Histogram) or None if insufficient data
        """
        if not prices or len(prices) < slow_period + signal_period:
            return None
        
        # Calculate fast and slow EMAs
        fast_ema = self.calculate_ema(prices, fast_period)
        slow_ema = self.calculate_ema(prices, slow_period)
        
        if fast_ema is None or slow_ema is None:
            return None
        
        # MACD line = Fast EMA - Slow EMA
        macd_line = fast_ema - slow_ema
        
        # Calculate MACD values for signal line calculation
        macd_values = []
        for i in range(slow_period - 1, len(prices)):
            subset_prices = prices[:i+1]
            fast = self.calculate_ema(subset_prices, fast_period)
            slow = self.calculate_ema(subset_prices, slow_period)
            if fast is not None and slow is not None:
                macd_values.append(fast - slow)
        
        if len(macd_values) < signal_period:
            return macd_line, 0, macd_line  # Return with zero signal line if insufficient data
        
        # Signal line = EMA of MACD line
        signal_line = self.calculate_ema(macd_values, signal_period)
        if signal_line is None:
            signal_line = 0
        
        # Histogram = MACD line - Signal line
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_rsi(self, prices: List[float], period: int = 7) -> Optional[float]:
        """
        Calculate RSI (Relative Strength Index)
        
        Args:
            prices: List of closing prices
            period: RSI period (default 7)
            
        Returns:
            RSI value (0-100) or None if insufficient data
        """
        if not prices or len(prices) < period + 1:
            return None
        
        # Calculate price changes
        price_changes = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            price_changes.append(change)
        
        if len(price_changes) < period:
            return None
        
        # Separate gains and losses
        gains = [change if change > 0 else 0 for change in price_changes]
        losses = [-change if change < 0 else 0 for change in price_changes]
        
        # Calculate average gain and loss for the period
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        # Avoid division by zero
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_atr(self, ohlcv_data: List[List[float]], period: int = 14) -> Optional[float]:
        """
        Calculate Average True Range (ATR)
        
        Args:
            ohlcv_data: OHLCV data [timestamp, open, high, low, close, volume]
            period: ATR period
            
        Returns:
            ATR value or None if insufficient data
        """
        if not ohlcv_data or len(ohlcv_data) < period + 1:
            return None
        
        true_ranges = []
        
        for i in range(1, len(ohlcv_data)):
            high = ohlcv_data[i][2]
            low = ohlcv_data[i][3]
            prev_close = ohlcv_data[i-1][4]
            
            # True Range is the maximum of:
            # 1. Current High - Current Low
            # 2. Absolute value of Current High - Previous Close
            # 3. Absolute value of Current Low - Previous Close
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        if len(true_ranges) < period:
            return None
        
        # Calculate ATR as simple moving average of true ranges
        atr = sum(true_ranges[-period:]) / period
        return atr
    
    def calculate_series_indicators(self, prices: List[float], ohlcv_data: List[List[float]], periods: int = 10) -> Dict:
        """
        Calculate indicator series for the last N periods
        
        Args:
            prices: Historical closing prices
            ohlcv_data: OHLCV data for ATR calculation
            periods: Number of periods to calculate
            
        Returns:
            Dictionary with indicator series
        """
        if len(prices) < periods + 26:  # Need enough data for MACD
            return {}
        
        # Calculate series for each indicator
        price_series = prices[-periods:]
        ema20_series = []
        macd_series = []
        rsi7_series = []
        rsi14_series = []
        
        # Calculate EMA20, MACD, RSI for each period
        for i in range(periods):
            end_idx = len(prices) - periods + i + 1
            subset_prices = prices[:end_idx]
            
            # EMA20
            ema20 = self.calculate_ema(subset_prices, 20)
            ema20_series.append(round(ema20, 3) if ema20 else 0)
            
            # MACD
            macd_result = self.calculate_macd(subset_prices)
            macd_line = macd_result[0] if macd_result else 0
            macd_series.append(round(macd_line, 3))
            
            # RSI 7-period
            rsi7 = self.calculate_rsi(subset_prices, 7)
            rsi7_series.append(round(rsi7, 3) if rsi7 else 50)
            
            # RSI 14-period
            rsi14 = self.calculate_rsi(subset_prices, 14)
            rsi14_series.append(round(rsi14, 3) if rsi14 else 50)
        
        return {
            'prices': [round(p, 1) for p in price_series],
            'ema20_series': ema20_series,
            'macd_series': macd_series,
            'rsi7_series': rsi7_series,
            'rsi14_series': rsi14_series
        }
    
    def get_historical_ohlcv(self, timeframe: str, limit: int = 100) -> List[List[float]]:
        """
        Get historical OHLCV data for comprehensive analysis
        
        Args:
            timeframe: Timeframe ('1m', '5m', '4h', etc.)
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV candles [timestamp, open, high, low, close, volume]
        """
        if not self.initialize_exchange():
            return []
        
        try:
            historical_data = self.exchange.get_historical_data(
                symbol=self.symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            if not historical_data:
                print(f"No data received for {self.symbol} on {timeframe}")
                return []
            
            print(f"Retrieved {len(historical_data)} {timeframe} candles for {self.symbol}")
            return historical_data
            
        except Exception as e:
            print(f"Error fetching {timeframe} OHLCV data: {e}")
            return []
    
    def get_historical_prices(self, timeframe: str = '1m', limit: int = 100) -> List[float]:
        """
        Get historical closing prices for calculations
        
        Args:
            timeframe: Timeframe for data
            limit: Number of candles to fetch
            
        Returns:
            List of closing prices
        """
        ohlcv_data = self.get_historical_ohlcv(timeframe, limit)
        if not ohlcv_data:
            return []
        
        # Extract closing prices (index 4 in OHLCV)
        closing_prices = [float(candle[4]) for candle in ohlcv_data]
        return closing_prices
    
    def get_current_price(self) -> Optional[float]:
        """
        Get current price for the trading symbol
        
        Returns:
            Current price or None if error
        """
        if not self.initialize_exchange():
            return None
        
        try:
            # Get latest OHLCV candle
            latest_ohlcv = self.exchange.get_latest_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe
            )
            
            if not latest_ohlcv:
                return None
            
            # Return closing price (index 4)
            return float(latest_ohlcv[4])
            
        except Exception as e:
            print(f"Error fetching current price: {e}")
            return None
    
    def calculate_comprehensive_data(self) -> Dict:
        """
        Calculate comprehensive trading analysis with intraday series and longer-term context
        
        Returns:
            Dictionary containing comprehensive analysis in the requested format
        """
        try:
            # Check cache first
            if self._is_cache_valid():
                print("Using cached comprehensive data")
                return self.cached_data
            
            print(f"Calculating comprehensive analysis for {self.symbol}...")
            
            # Get 1-minute data for intraday analysis
            intraday_ohlcv = self.get_historical_ohlcv('1m', 150)  # Get enough for calculations
            intraday_prices = [float(candle[4]) for candle in intraday_ohlcv] if intraday_ohlcv else []
            
            # Get 4-hour data for longer-term context
            hourly_ohlcv = self.get_historical_ohlcv('4h', 100)
            hourly_prices = [float(candle[4]) for candle in hourly_ohlcv] if hourly_ohlcv else []
            
            if not intraday_prices or len(intraday_prices) < 60:
                return {
                    'error': f'Insufficient intraday data: got {len(intraday_prices) if intraday_prices else 0} prices, need at least 60',
                    'symbol': self.symbol,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Current values (latest)
            current_price = intraday_prices[-1]
            current_ema20 = self.calculate_ema(intraday_prices, 20)
            current_macd_result = self.calculate_macd(intraday_prices)
            current_macd = current_macd_result[0] if current_macd_result else 0
            current_rsi7 = self.calculate_rsi(intraday_prices, 7)
            
            # Calculate intraday series (last 10 periods)
            series_data = self.calculate_series_indicators(intraday_prices, intraday_ohlcv, 10)
            
            # Longer-term context (4-hour timeframe)
            longer_context = {}
            if hourly_prices and len(hourly_prices) >= 50:
                # 4-hour EMAs
                ema20_4h = self.calculate_ema(hourly_prices, 20)
                ema50_4h = self.calculate_ema(hourly_prices, 50)
                
                # 4-hour ATR
                atr3_4h = self.calculate_atr(hourly_ohlcv, 3)
                atr14_4h = self.calculate_atr(hourly_ohlcv, 14)
                
                # 4-hour volume analysis
                current_volume = hourly_ohlcv[-1][5] if hourly_ohlcv else 0
                volumes_4h = [candle[5] for candle in hourly_ohlcv[-20:]] if hourly_ohlcv else []
                avg_volume = sum(volumes_4h) / len(volumes_4h) if volumes_4h else 0
                
                # 4-hour MACD and RSI series
                macd_4h_series = []
                rsi14_4h_series = []
                
                for i in range(10):
                    end_idx = len(hourly_prices) - 10 + i + 1
                    subset_prices_4h = hourly_prices[:end_idx]
                    
                    # MACD 4h
                    macd_result_4h = self.calculate_macd(subset_prices_4h)
                    macd_4h = macd_result_4h[0] if macd_result_4h else 0
                    macd_4h_series.append(round(macd_4h, 3))
                    
                    # RSI 14 4h
                    rsi14_4h = self.calculate_rsi(subset_prices_4h, 14)
                    rsi14_4h_series.append(round(rsi14_4h, 3) if rsi14_4h else 50)
                
                longer_context = {
                    'ema20_4h': round(ema20_4h, 3) if ema20_4h else 0,
                    'ema50_4h': round(ema50_4h, 3) if ema50_4h else 0,
                    'atr3_4h': round(atr3_4h, 3) if atr3_4h else 0,
                    'atr14_4h': round(atr14_4h, 3) if atr14_4h else 0,
                    'current_volume': round(current_volume, 3),
                    'average_volume': round(avg_volume, 3),
                    'macd_4h_series': macd_4h_series,
                    'rsi14_4h_series': rsi14_4h_series
                }
            
            # Prepare comprehensive result in requested format
            result = {
                'success': True,
                'symbol': self.symbol,
                'timestamp': datetime.now().isoformat(),
                
                # Current values
                'current_price': round(current_price, 1),
                'current_ema20': round(current_ema20, 3) if current_ema20 else 0,
                'current_macd': round(current_macd, 3),
                'current_rsi7': round(current_rsi7, 3) if current_rsi7 else 50,
                
                # Intraday series (by minute, oldest → latest)
                'intraday_series': series_data,
                
                # Longer-term context (4-hour timeframe)
                'longer_term_context': longer_context,
                
                # Metadata
                'timeframe': '1m',
                'data_points_used': len(intraday_prices),
                'exchange': type(self.exchange).__name__.replace('Exchange', '') if self.exchange else 'Unknown'
            }
            
            # Cache the result
            self.cached_data = result
            self.last_update_time = time.time()
            
            print(f"Comprehensive analysis completed:")
            print(f"  Price: ${current_price:.1f}")
            print(f"  EMA20: ${current_ema20:.3f}" if current_ema20 else "  EMA20: N/A")
            print(f"  MACD: {current_macd:.3f}")
            print(f"  RSI(7): {current_rsi7:.3f}" if current_rsi7 else "  RSI(7): N/A")
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'error': f'Calculation failed: {str(e)}',
                'symbol': self.symbol,
                'timestamp': datetime.now().isoformat()
            }
    
    def calculate_ema9_data(self) -> Dict:
        """
        Backward compatibility method - calls comprehensive analysis
        """
        return self.calculate_comprehensive_data()
    
    def _generate_combined_signal(self, current_price: float, current_ema9: float, previous_ema9: Optional[float], 
                                 current_macd: float, current_rsi: float, prices: List[float]) -> Dict:
        """
        Generate trading signal based on EMA9, MACD, and RSI analysis
        
        Args:
            current_price: Current asset price
            current_ema9: Current EMA9 value
            previous_ema9: Previous EMA9 value
            current_macd: Current MACD value
            current_rsi: Current RSI value
            prices: Historical prices for additional analysis
            
        Returns:
            Dictionary with signal information
        """
        signal_type = "HOLD"
        signal_strength = 0
        signal_reasons = []
        
        # Price position relative to EMA9
        gap_percentage = ((current_price - current_ema9) / current_ema9) * 100
        
        # 1. EMA9 Cross Analysis
        if len(prices) >= 2 and previous_ema9:
            previous_price = prices[-2]
            
            # Bullish cross: price crosses above EMA9
            if previous_price <= previous_ema9 and current_price > current_ema9:
                signal_type = "BUY"
                signal_strength += 40
                signal_reasons.append("Price crossed above EMA9 (bullish)")
            
            # Bearish cross: price crosses below EMA9
            elif previous_price >= previous_ema9 and current_price < current_ema9:
                signal_type = "SELL"
                signal_strength += 40
                signal_reasons.append("Price crossed below EMA9 (bearish)")
        
        # 2. EMA9 Trend Analysis
        if previous_ema9:
            ema_change = ((current_ema9 - previous_ema9) / previous_ema9) * 100
            
            if ema_change > 0.5:  # EMA9 rising strongly
                if current_price > current_ema9:
                    signal_strength += 20
                    signal_reasons.append(f"EMA9 rising strongly (+{ema_change:.2f}%)")
                
            elif ema_change < -0.5:  # EMA9 falling strongly
                if current_price < current_ema9:
                    signal_strength += 20
                    signal_reasons.append(f"EMA9 falling strongly ({ema_change:.2f}%)")
        
        # 3. Distance from EMA9 Analysis
        if abs(gap_percentage) < 1.0:  # Price very close to EMA9 (within 1%)
            signal_strength += 15
            signal_reasons.append(f"Price close to EMA9 ({gap_percentage:+.2f}%)")
        elif abs(gap_percentage) > 5.0:  # Price far from EMA9 (potential reversal)
            if gap_percentage > 0:
                signal_type = "SELL" if signal_type != "BUY" else signal_type
                signal_reasons.append(f"Price significantly above EMA9 (+{gap_percentage:.1f}%)")
            else:
                signal_type = "BUY" if signal_type != "SELL" else signal_type
                signal_reasons.append(f"Price significantly below EMA9 ({gap_percentage:.1f}%)")
        
        # 4. MACD Analysis
        if current_macd > 0:
            signal_strength += 25
            signal_reasons.append(f"MACD bullish ({current_macd:.3f})")
            if signal_type == "HOLD":
                signal_type = "BUY"
        elif current_macd < 0:
            signal_strength += 15
            signal_reasons.append(f"MACD bearish ({current_macd:.3f})")
            if signal_type == "HOLD":
                signal_type = "SELL"
        
        # 5. RSI Analysis
        if current_rsi > 70:
            if signal_type == "BUY":
                signal_strength -= 10  # Reduce bullish strength in overbought
            signal_reasons.append(f"RSI overbought ({current_rsi:.1f})")
        elif current_rsi < 30:
            if signal_type == "SELL":
                signal_strength -= 10  # Reduce bearish strength in oversold
            signal_reasons.append(f"RSI oversold ({current_rsi:.1f})")
        elif 45 <= current_rsi <= 55:
            signal_strength += 10
            signal_reasons.append(f"RSI neutral ({current_rsi:.1f})")
        
        # 6. Recent Price Momentum
        if len(prices) >= 5:
            recent_prices = prices[-5:]
            price_momentum = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100
            
            if price_momentum > 2.0:  # Strong upward momentum
                if current_price > current_ema9:
                    signal_strength += 15
                    signal_reasons.append(f"Strong upward momentum (+{price_momentum:.1f}%)")
            elif price_momentum < -2.0:  # Strong downward momentum
                if current_price < current_ema9:
                    signal_strength += 15
                    signal_reasons.append(f"Strong downward momentum ({price_momentum:.1f}%)")
        
        # Determine final signal type based on strength and indicators
        if signal_strength >= 50:
            if signal_type == "BUY" or (current_macd > 0 and current_price > current_ema9 and current_rsi < 70):
                signal_type = "STRONG_BUY"
            elif signal_type == "SELL" or (current_macd < 0 and current_price < current_ema9 and current_rsi > 30):
                signal_type = "STRONG_SELL"
        elif signal_strength >= 35:
            if current_rsi < 25 or (current_macd > 0 and current_price > current_ema9):
                signal_type = "BUY"
            elif current_rsi > 75 or (current_macd < 0 and current_price < current_ema9):
                signal_type = "SELL"
        elif signal_strength < 20:
            signal_type = "HOLD"
        
        # Compile signal
        return {
            'type': signal_type,
            'strength': min(signal_strength, 100),
            'confidence': min(signal_strength / 100, 1.0),
            'reasons': signal_reasons,
            'gap_percentage': gap_percentage,
            'recommendation': self._get_signal_recommendation(signal_type, signal_strength)
        }
    
    def _get_signal_recommendation(self, signal_type: str, strength: int) -> str:
        """Get human-readable recommendation based on signal"""
        recommendations = {
            'STRONG_BUY': f"Strong Buy Signal (Confidence: {strength}%) - Consider entering long position",
            'BUY': f"Buy Signal (Confidence: {strength}%) - Favorable for long entry",
            'STRONG_SELL': f"Strong Sell Signal (Confidence: {strength}%) - Consider exiting or short position",
            'SELL': f"Sell Signal (Confidence: {strength}%) - Consider taking profits or exit",
            'HOLD': f"Hold/Neutral (Confidence: {strength}%) - Wait for clearer signals"
        }
        return recommendations.get(signal_type, f"Unknown Signal ({strength}%)")
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        if not self.cached_data or not self.last_update_time:
            return False
        
        return (time.time() - self.last_update_time) < self.cache_duration
    
    def get_formatted_output(self) -> str:
        """
        Get data in the exact requested format
        
        Returns:
            Formatted string output matching the requested format
        """
        data = self.calculate_comprehensive_data()
        
        if 'error' in data:
            return f"Error: {data['error']}"
        
        # Build formatted output
        output_lines = []
        
        # Current values line
        output_lines.append(f"current_price = {data['current_price']}, current_ema20 = {data['current_ema20']}, current_macd = {data['current_macd']}, current_rsi (7 period) = {data['current_rsi7']}")
        output_lines.append("")
        
        # Intraday series
        if 'intraday_series' in data and data['intraday_series']:
            series = data['intraday_series']
            output_lines.append("Intraday series (by minute, oldest → latest):")
            
            if 'prices' in series:
                prices_str = ', '.join([str(p) for p in series['prices']])
                output_lines.append(f"Mid prices: [{prices_str}]")
            
            if 'ema20_series' in series:
                ema20_str = ', '.join([str(e) for e in series['ema20_series']])
                output_lines.append(f"EMA indicators (20‑period): [{ema20_str}]")
            
            if 'macd_series' in series:
                macd_str = ', '.join([str(m) for m in series['macd_series']])
                output_lines.append(f"MACD indicators: [{macd_str}]")
            
            if 'rsi7_series' in series:
                rsi7_str = ', '.join([str(r) for r in series['rsi7_series']])
                output_lines.append(f"RSI indicators (7‑Period): [{rsi7_str}]")
            
            if 'rsi14_series' in series:
                rsi14_str = ', '.join([str(r) for r in series['rsi14_series']])
                output_lines.append(f"RSI indicators (14‑Period): [{rsi14_str}]")
        
        # Longer-term context
        if 'longer_term_context' in data and data['longer_term_context']:
            context = data['longer_term_context']
            output_lines.append("")
            output_lines.append("Longer‑term context (4‑hour timeframe):")
            
            if 'ema20_4h' in context and 'ema50_4h' in context:
                output_lines.append(f"20‑Period EMA: {context['ema20_4h']} vs. 50‑Period EMA: {context['ema50_4h']}")
            
            if 'atr3_4h' in context and 'atr14_4h' in context:
                output_lines.append(f"3‑Period ATR: {context['atr3_4h']} vs. 14‑Period ATR: {context['atr14_4h']}")
            
            if 'current_volume' in context and 'average_volume' in context:
                output_lines.append(f"Current Volume: {context['current_volume']} vs. Average Volume: {context['average_volume']}")
            
            if 'macd_4h_series' in context:
                macd_4h_str = ', '.join([str(m) for m in context['macd_4h_series']])
                output_lines.append(f"MACD indicators: [{macd_4h_str}]")
            
            if 'rsi14_4h_series' in context:
                rsi14_4h_str = ', '.join([str(r) for r in context['rsi14_4h_series']])
                output_lines.append(f"RSI indicators (14‑Period): [{rsi14_4h_str}]")
        
        return '\n'.join(output_lines)
    
    def generate_trading_signal(self) -> Dict:
        """
        Generate automated trading signal with entry, stop loss, and take profit levels
        
        Returns:
            Dictionary containing trading recommendation with levels
        """
        data = self.calculate_comprehensive_data()
        
        if 'error' in data:
            return {'error': data['error']}
        
        # Extract current values
        current_price = data['current_price']
        current_ema20 = data['current_ema20']
        current_macd = data['current_macd']
        current_rsi7 = data['current_rsi7']
        
        # Get series data for trend analysis
        series = data.get('intraday_series', {})
        longer_context = data.get('longer_term_context', {})
        
        # Calculate additional metrics
        price_vs_ema = ((current_price - current_ema20) / current_ema20) * 100
        
        # Get RSI 14 from series if available
        rsi14_series = series.get('rsi14_series', [])
        current_rsi14 = rsi14_series[-1] if rsi14_series else 50
        
        # Get 4H context
        ema20_4h = longer_context.get('ema20_4h', current_ema20)
        ema50_4h = longer_context.get('ema50_4h', current_ema20)
        
        # Initialize signal components
        signal_strength = 0
        signal_factors = []
        trade_direction = "HOLD"
        confidence = 50
        
        # RSI Analysis (Primary factor for oversold/overbought)
        if current_rsi7 < 20:  # Extremely oversold on RSI7
            signal_strength += 50
            signal_factors.append(f"Extremely oversold RSI(7): {current_rsi7:.1f}")
            trade_direction = "LONG"
        elif current_rsi7 < 30:  # Oversold on RSI7
            signal_strength += 35
            signal_factors.append(f"Oversold RSI(7): {current_rsi7:.1f}")
            trade_direction = "LONG"
        elif current_rsi7 > 80:  # Extremely overbought on RSI7
            signal_strength += 50
            signal_factors.append(f"Extremely overbought RSI(7): {current_rsi7:.1f}")
            trade_direction = "SHORT"
        elif current_rsi7 > 70:  # Overbought on RSI7
            signal_strength += 35
            signal_factors.append(f"Overbought RSI(7): {current_rsi7:.1f}")
            trade_direction = "SHORT"
        
        # RSI(14) confirmation
        if current_rsi14 < 35 and trade_direction == "LONG":
            signal_strength += 15
            signal_factors.append(f"RSI(14) oversold confirmation: {current_rsi14:.1f}")
        elif current_rsi14 > 65 and trade_direction == "SHORT":
            signal_strength += 15
            signal_factors.append(f"RSI(14) overbought confirmation: {current_rsi14:.1f}")
        elif current_rsi14 < 40 and trade_direction == "LONG":
            signal_strength += 10
            signal_factors.append(f"RSI(14) supportive: {current_rsi14:.1f}")
        elif current_rsi14 > 60 and trade_direction == "SHORT":
            signal_strength += 10
            signal_factors.append(f"RSI(14) supportive: {current_rsi14:.1f}")
        
        # MACD Analysis
        if current_macd > 0 and trade_direction == "LONG":
            signal_strength += 20
            signal_factors.append(f"MACD bullish confirmation: {current_macd:.3f}")
        elif current_macd < 0 and trade_direction == "SHORT":
            signal_strength += 20
            signal_factors.append(f"MACD bearish confirmation: {current_macd:.3f}")
        elif current_macd < 0 and trade_direction == "LONG":
            signal_strength -= 10
            signal_factors.append(f"MACD bearish divergence: {current_macd:.3f}")
        elif current_macd > 0 and trade_direction == "SHORT":
            signal_strength -= 10
            signal_factors.append(f"MACD bullish divergence: {current_macd:.3f}")
        
        # Price vs EMA Analysis
        if abs(price_vs_ema) < 0.5:
            signal_strength += 15
            signal_factors.append(f"Price near EMA20: {price_vs_ema:+.2f}%")
        
        # Longer-term context
        if current_price < ema20_4h and current_price < ema50_4h and trade_direction == "LONG":
            signal_factors.append(f"Counter-trend long (below 4H EMAs)")
        elif current_price > ema20_4h and current_price > ema50_4h and trade_direction == "SHORT":
            signal_factors.append(f"Counter-trend short (above 4H EMAs)")
        
        # Calculate confidence
        confidence = min(signal_strength, 95)
        
        # Generate TP/SL levels based on ATR and volatility
        atr_3 = longer_context.get('atr3_4h', 0.05)  # Default ATR if not available
        atr_14 = longer_context.get('atr14_4h', 0.1)
        
        # Use shorter ATR for tighter stops, longer for targets
        volatility_factor = (atr_3 + atr_14) / 2
        
        if trade_direction == "LONG":
            # Long position levels
            entry_price = current_price
            stop_loss = round(current_price - (volatility_factor * 0.5), 4)
            take_profit_1 = round(current_price + (volatility_factor * 0.6), 4)
            take_profit_2 = round(current_price + (volatility_factor * 1.2), 4)
            take_profit_3 = round(current_price + (volatility_factor * 2.0), 4)
            
            # Risk/Reward calculations
            risk_amount = entry_price - stop_loss
            reward_1 = take_profit_1 - entry_price
            reward_2 = take_profit_2 - entry_price
            reward_3 = take_profit_3 - entry_price
            
        elif trade_direction == "SHORT":
            # Short position levels
            entry_price = current_price
            stop_loss = round(current_price + (volatility_factor * 0.5), 4)
            take_profit_1 = round(current_price - (volatility_factor * 0.6), 4)
            take_profit_2 = round(current_price - (volatility_factor * 1.2), 4)
            take_profit_3 = round(current_price - (volatility_factor * 2.0), 4)
            
            # Risk/Reward calculations
            risk_amount = stop_loss - entry_price
            reward_1 = entry_price - take_profit_1
            reward_2 = entry_price - take_profit_2
            reward_3 = entry_price - take_profit_3
        else:
            # HOLD - no trade
            entry_price = current_price
            stop_loss = None
            take_profit_1 = None
            take_profit_2 = None
            take_profit_3 = None
            risk_amount = 0
            reward_1 = reward_2 = reward_3 = 0
        
        # Position sizing recommendation (based on confidence and volatility)
        if confidence >= 80:
            position_size_pct = 2.0  # 2% of capital for high confidence
        elif confidence >= 60:
            position_size_pct = 1.5  # 1.5% for medium confidence
        elif confidence >= 40:
            position_size_pct = 1.0  # 1% for lower confidence
        else:
            position_size_pct = 0.5  # 0.5% for very low confidence
        
        # Trade validity time (based on timeframe)
        validity_hours = 4 if trade_direction != "HOLD" else 0
        
        # Compile trading signal
        trading_signal = {
            'symbol': data['symbol'],
            'timestamp': data['timestamp'],
            'signal_direction': trade_direction,
            'confidence': confidence,
            'signal_strength': signal_strength,
            'signal_factors': signal_factors,
            
            # Current market data
            'current_price': current_price,
            'current_ema20': current_ema20,
            'current_macd': current_macd,
            'current_rsi7': current_rsi7,
            'current_rsi14': current_rsi14,
            
            # Trade levels
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'take_profit_3': take_profit_3,
            
            # Risk management
            'risk_amount': round(risk_amount, 4) if risk_amount else 0,
            'reward_1': round(reward_1, 4) if reward_1 else 0,
            'reward_2': round(reward_2, 4) if reward_2 else 0,
            'reward_3': round(reward_3, 4) if reward_3 else 0,
            'risk_reward_1': round(reward_1 / risk_amount, 2) if risk_amount > 0 else 0,
            'risk_reward_2': round(reward_2 / risk_amount, 2) if risk_amount > 0 else 0,
            'risk_reward_3': round(reward_3 / risk_amount, 2) if risk_amount > 0 else 0,
            
            # Position management
            'position_size_pct': position_size_pct,
            'validity_hours': validity_hours,
            'volatility_factor': round(volatility_factor, 4),
            
            # Market context
            'price_vs_ema20_pct': round(price_vs_ema, 3),
            'ema20_4h': ema20_4h,
            'ema50_4h': ema50_4h,
            'atr_3': round(atr_3, 4),
            'atr_14': round(atr_14, 4)
        }
        
        return trading_signal
    
    def get_formatted_trading_signal(self) -> str:
        """
        Get trading signal in formatted text output
        
        Returns:
            Formatted trading signal with entry, SL, TP levels
        """
        signal = self.generate_trading_signal()
        
        if 'error' in signal:
            return f"Error generating signal: {signal['error']}"
        
        if signal['signal_direction'] == "HOLD":
            return f"""
🔄 TRADING SIGNAL: HOLD/WAIT
Symbol: {signal['symbol']}
Current Price: ${signal['current_price']}
Confidence: {signal['confidence']}%

No clear trading opportunity at current levels.
Wait for better setup or clearer technical signals.

Market Analysis:
- RSI(7): {signal['current_rsi7']:.1f}
- RSI(14): {signal['current_rsi14']:.1f}  
- MACD: {signal['current_macd']:.3f}
- Price vs EMA20: {signal['price_vs_ema20_pct']:+.2f}%
"""
        
        direction_emoji = "📈" if signal['signal_direction'] == "LONG" else "📉"
        
        output = f"""
{direction_emoji} TRADING SIGNAL: {signal['signal_direction']} POSITION
Symbol: {signal['symbol']}
Confidence: {signal['confidence']}% | Strength: {signal['signal_strength']}/100

💰 TRADE SETUP:
Entry Price: ${signal['entry_price']}
Stop Loss: ${signal['stop_loss']} (-{((signal['entry_price'] - signal['stop_loss']) / signal['entry_price'] * 100):.2f}%)
Take Profit 1: ${signal['take_profit_1']} (+{((signal['take_profit_1'] - signal['entry_price']) / signal['entry_price'] * 100):.2f}%)
Take Profit 2: ${signal['take_profit_2']} (+{((signal['take_profit_2'] - signal['entry_price']) / signal['entry_price'] * 100):.2f}%)
Take Profit 3: ${signal['take_profit_3']} (+{((signal['take_profit_3'] - signal['entry_price']) / signal['entry_price'] * 100):.2f}%)

📊 RISK/REWARD:
Risk Amount: ${signal['risk_amount']}
TP1 R/R: 1:{signal['risk_reward_1']}
TP2 R/R: 1:{signal['risk_reward_2']}
TP3 R/R: 1:{signal['risk_reward_3']}

💼 POSITION MANAGEMENT:
Position Size: {signal['position_size_pct']}% of capital
Validity: {signal['validity_hours']} hours
Volatility (ATR): {signal['volatility_factor']}

📈 TECHNICAL ANALYSIS:
Current Price: ${signal['current_price']}
EMA20 (1m): ${signal['current_ema20']} ({signal['price_vs_ema20_pct']:+.2f}%)
MACD: {signal['current_macd']:.3f}
RSI(7): {signal['current_rsi7']:.1f}
RSI(14): {signal['current_rsi14']:.1f}

🎯 SIGNAL REASONS:"""
        
        for i, factor in enumerate(signal['signal_factors'], 1):
            output += f"\n{i}. {factor}"
        
        output += f"""

⚠️ LONGER-TERM CONTEXT:
4H EMA20: ${signal['ema20_4h']:.3f}
4H EMA50: ${signal['ema50_4h']:.3f}
ATR(3): {signal['atr_3']} | ATR(14): {signal['atr_14']}
"""
        
        return output
    
    def get_ema9_summary(self) -> Dict:
        """
        Get a concise summary of all indicators analysis
        
        Returns:
            Simplified data for quick reference
        """
        full_data = self.calculate_ema9_data()
        
        if 'error' in full_data:
            return full_data
        
        return {
            'symbol': full_data['symbol'],
            'current_price': full_data['current_price'],
            'current_ema9': full_data['current_ema9'],
            'current_macd': full_data['current_macd'],
            'current_rsi': full_data['current_rsi'],
            'gap_percent': full_data['price_to_ema_percentage'],
            'position': full_data['position'],
            'signal': full_data['signal']['type'],
            'confidence': full_data['signal']['confidence'],
            'timestamp': full_data['timestamp']
        }
    
    def get_ema9_history(self, periods: int = 20) -> List[Dict]:
        """
        Get historical EMA20 values for trend analysis
        
        Args:
            periods: Number of periods to calculate EMA20 for
            
        Returns:
            List of historical EMA20 data points
        """
        if not self.initialize_exchange():
            return []
        
        try:
            # Get more historical data for calculating multiple EMA20 points
            limit = periods + self.ema_period_short + 10  # Buffer for accurate calculations
            prices = self.get_historical_prices('1m', limit=limit)
            
            if len(prices) < self.ema_period_short + periods:
                return []
            
            history = []
            
            # Calculate EMA20 for each period
            for i in range(self.ema_period_short, len(prices)):
                subset_prices = prices[:i+1]
                ema20_value = self.calculate_ema(subset_prices, self.ema_period_short)
                current_price = prices[i]
                
                if ema20_value:
                    gap_percent = ((current_price - ema20_value) / ema20_value) * 100
                    
                    history.append({
                        'period': i - self.ema_period_short + 1,
                        'price': round(current_price, 8),
                        'ema20': round(ema20_value, 8),
                        'gap_percent': round(gap_percent, 3),
                        'position': 'above' if current_price > ema20_value else 'below'
                    })
            
            # Return the last 'periods' number of data points
            return history[-periods:] if len(history) > periods else history
            
        except Exception as e:
            print(f"Error getting EMA9 history: {e}")
            return []
    
    def test_connection(self) -> Dict:
        """
        Test the backend connection and configuration
        
        Returns:
            Dictionary with connection test results
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'ema_period': self.ema_period_short,
            'exchange_config': self.exchange_name
        }
        
        try:
            # Test exchange initialization
            if not self.initialize_exchange():
                result['status'] = 'FAILED'
                result['error'] = 'Exchange initialization failed'
                return result
            
            result['exchange_name'] = type(self.exchange).__name__.replace('Exchange', '')
            
            # Test data fetching
            current_price = self.get_current_price()
            if current_price is None:
                result['status'] = 'FAILED'
                result['error'] = 'Failed to fetch current price'
                return result
            
            result['current_price'] = current_price
            
            # Test historical data (need enough for EMA20)
            prices = self.get_historical_prices('1m', limit=50)
            if not prices or len(prices) < 25:
                result['status'] = 'FAILED'
                result['error'] = f'Insufficient historical data: got {len(prices) if prices else 0} prices, need at least 25'
                return result
            
            result['historical_data_points'] = len(prices)
            
            # Test EMA20 calculation
            ema20 = self.calculate_ema(prices, self.ema_period_short)
            if ema20 is None:
                result['status'] = 'FAILED'
                result['error'] = 'Failed to calculate EMA20'
                return result
            
            result['ema20_test'] = ema20
            result['status'] = 'SUCCESS'
            result['message'] = f'All tests passed. Ready to provide comprehensive data for {self.symbol}'
            
        except Exception as e:
            result['status'] = 'FAILED'
            result['error'] = f'Test failed: {str(e)}'
        
        return result


def main():
    """Main function for standalone execution"""
    print("=" * 60)
    print("CoinDCX EMA9 Backend - Standalone Mode")
    print("=" * 60)
    
    # Initialize backend
    backend = EMA9Backend()
    
    # Test connection
    print("\n1. Testing Connection...")
    test_result = backend.test_connection()
    print(f"Status: {test_result['status']}")
    
    if test_result['status'] == 'SUCCESS':
        print(f"Exchange: {test_result['exchange_name']}")
        print(f"Current Price: ${test_result['current_price']:.6f}")
        print(f"Historical Data Points: {test_result['historical_data_points']}")
        print(f"EMA9 Test Value: ${test_result['ema9_test']:.6f}")
    else:
        print(f"Error: {test_result.get('error', 'Unknown error')}")
        return
    
    # Get EMA9 analysis
    print(f"\n2. EMA9 Analysis for {backend.symbol}...")
    ema9_data = backend.calculate_ema9_data()
    
    if 'error' in ema9_data:
        print(f"Error: {ema9_data['error']}")
        return
    
    print(f"Current Price: ${ema9_data['current_price']:.6f}")
    print(f"EMA9: ${ema9_data['ema9']:.6f}")
    print(f"Gap: {ema9_data['price_to_ema_percentage']:+.3f}%")
    print(f"Position: {ema9_data['position']} EMA9")
    print(f"EMA9 Trend: {ema9_data['ema_trend']} ({ema9_data['ema_trend_percentage']:+.3f}%)")
    
    # Signal Analysis
    signal = ema9_data['signal']
    print(f"\n3. Trading Signal:")
    print(f"Signal: {signal['type']}")
    print(f"Strength: {signal['strength']}/100")
    print(f"Confidence: {signal['confidence']:.1%}")
    print(f"Recommendation: {signal['recommendation']}")
    
    if signal['reasons']:
        print("Reasons:")
        for i, reason in enumerate(signal['reasons'], 1):
            print(f"  {i}. {reason}")
    
    # Get summary
    print(f"\n4. Quick Summary:")
    summary = backend.get_ema9_summary()
    print(json.dumps(summary, indent=2))
    
    # Get recent history
    print(f"\n5. Recent EMA9 History (last 10 periods):")
    history = backend.get_ema9_history(periods=10)
    if history:
        print("Period | Price     | EMA9      | Gap%   | Position")
        print("-" * 50)
        for point in history[-10:]:  # Show last 10
            print(f"{point['period']:6d} | ${point['price']:8.4f} | ${point['ema9']:8.4f} | {point['gap_percent']:+6.2f}% | {point['position']:>5s}")
    else:
        print("No history available")
    
    print(f"\n6. Cache Status:")
    print(f"Last Update: {backend.last_update_time}")
    print(f"Cache Valid: {backend._is_cache_valid()}")
    print(f"Cache Duration: {backend.cache_duration}s")


if __name__ == "__main__":
    main()