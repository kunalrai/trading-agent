"""
CoinDCX Futures Trading Agent
Fetches real-time data for top 5 coins, calculates technical indicators,
and provides trading signals with confidence levels.
"""

import time
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

# Technical indicator calculations
def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return []
    
    ema_values = []
    multiplier = 2 / (period + 1)
    
    # Start with simple moving average for first EMA value
    sma = sum(prices[:period]) / period
    ema_values.append(sma)
    
    # Calculate EMA for remaining periods
    for i in range(period, len(prices)):
        ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
        ema_values.append(ema)
    
    return ema_values

def calculate_macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, List[float]]:
    """Calculate MACD (Moving Average Convergence Divergence)"""
    if len(prices) < slow_period:
        return {'macd': [], 'signal': [], 'histogram': []}
    
    # Calculate EMAs
    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)
    
    # Calculate MACD line
    macd_line = []
    start_idx = slow_period - fast_period
    for i in range(len(ema_slow)):
        fast_val = ema_fast[start_idx + i] if start_idx + i < len(ema_fast) else ema_fast[-1]
        macd_line.append(fast_val - ema_slow[i])
    
    # Calculate signal line (EMA of MACD)
    signal_line = calculate_ema(macd_line, signal_period)
    
    # Calculate histogram
    histogram = []
    signal_start = len(macd_line) - len(signal_line)
    for i in range(len(signal_line)):
        histogram.append(macd_line[signal_start + i] - signal_line[i])
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }

def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return []
    
    gains = []
    losses = []
    
    # Calculate price changes
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return []
    
    rsi_values = []
    
    # Calculate first RSI with simple moving average
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        rsi_values.append(100)
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_values.append(rsi)
    
    # Calculate remaining RSI values with exponential smoothing
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)
    
    return rsi_values

def calculate_atr(high_prices: List[float], low_prices: List[float], close_prices: List[float], period: int = 14) -> List[float]:
    """Calculate Average True Range"""
    if len(high_prices) < period or len(low_prices) < period or len(close_prices) < period:
        return []
    
    true_ranges = []
    
    # Calculate True Range for each period
    for i in range(1, len(close_prices)):
        high_low = high_prices[i] - low_prices[i]
        high_close_prev = abs(high_prices[i] - close_prices[i-1])
        low_close_prev = abs(low_prices[i] - close_prices[i-1])
        
        true_range = max(high_low, high_close_prev, low_close_prev)
        true_ranges.append(true_range)
    
    if len(true_ranges) < period:
        return []
    
    atr_values = []
    
    # First ATR is simple moving average
    first_atr = sum(true_ranges[:period]) / period
    atr_values.append(first_atr)
    
    # Subsequent ATRs use exponential smoothing
    for i in range(period, len(true_ranges)):
        atr = (atr_values[-1] * (period - 1) + true_ranges[i]) / period
        atr_values.append(atr)
    
    return atr_values

class CoinDCXFuturesTrader:
    """CoinDCX Futures Trading System with Virtual Position Management"""
    
    def __init__(self, virtual_trading_enabled=True, virtual_balance=10000.0, 
                 risk_per_trade=0.02, max_positions=3, confidence_threshold=80):
        self.base_url = "https://api.coindcx.com"
        self.public_url = "https://public.coindcx.com"
        
        # Coin selection mode
        self.scan_all_instruments = False  # Set to True to scan all active instruments
        self.top_coins = ['ZEC/USDT']  # Used when scan_all_instruments is False
        self.min_volume_filter = 100000  # Minimum 24h volume filter for scanning all instruments
        
        # Trading parameters
        self.confidence_threshold = confidence_threshold  # Minimum confidence for trade signals
        self.risk_reward_ratio = 2.0    # Risk:Reward ratio for TP/SL calculation
        
        # Virtual trading parameters
        self.virtual_trading_enabled = virtual_trading_enabled  # Enable/disable virtual position management
        self.virtual_balance = virtual_balance  # Starting virtual balance in USDT
        self.risk_per_trade = risk_per_trade  # Risk percentage of balance per trade
        self.max_positions = max_positions  # Maximum concurrent positions
        
        # Virtual portfolio tracking
        self.virtual_positions = {}  # Active virtual positions
        self.virtual_trade_history = []  # Completed trades history
        self.virtual_current_balance = self.virtual_balance
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def get_futures_instruments(self, margin_currency: str = 'USDT') -> List[Dict]:
        """Fetch active futures instruments from CoinDCX"""
        try:
            url = f"{self.base_url}/exchange/v1/derivatives/futures/data/active_instruments"
            params = {'margin_currency_short_name[]': margin_currency}
            
            self.logger.info(f"🌐 Fetching futures instruments from CoinDCX API...")
            self.logger.info(f"📡 URL: {url}")
            self.logger.info(f"🔧 Parameters: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Log raw response for debugging
            self.logger.info(f"🔍 Response status: {response.status_code}")
            self.logger.info(f"🔍 Response headers: {dict(response.headers)}")
            
            raw_data = response.text
            self.logger.info(f"📄 Raw response (first 200 chars): {raw_data[:200]}...")
            
            instruments = response.json()
            
            # Check if response is a dict with data key or direct list
            if isinstance(instruments, dict):
                if 'data' in instruments:
                    instruments = instruments['data']
                elif 'result' in instruments:
                    instruments = instruments['result']
                else:
                    # If it's a dict but not the expected structure, convert to list
                    self.logger.warning(f"⚠️ Unexpected response structure: {list(instruments.keys())}")
                    instruments = []
            
            self.logger.info(f"✅ Successfully fetched {len(instruments)} futures instruments for {margin_currency}")
            
            # Log first few instruments as examples
            if instruments and len(instruments) > 0:
                self.logger.info(f"📋 Sample instruments:")
                for i, instrument in enumerate(instruments[:5], 1):
                    if isinstance(instrument, dict):
                        symbol = instrument.get('symbol', 'N/A')
                        status = instrument.get('status', 'N/A')
                        self.logger.info(f"   {i}. {symbol} (Status: {status})")
                    else:
                        self.logger.info(f"   {i}. {instrument}")
                if len(instruments) > 5:
                    self.logger.info(f"   ... and {len(instruments) - 5} more instruments")
            
            return instruments if isinstance(instruments, list) else []
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching futures instruments: {e}")
            self.logger.error(f"🔗 URL attempted: {url if 'url' in locals() else 'URL not set'}")
            return []
    
    def get_all_tradable_symbols(self, max_symbols=None) -> List[str]:
        """Get all tradable USDT futures symbols with volume filtering
        
        Args:
            max_symbols (int, optional): Maximum number of symbols to return. 
                                       None means no limit (for full scans)
        """
        try:
            self.logger.info("🔍 Starting comprehensive market scan for tradable symbols...")
            
            # Get futures instruments
            self.logger.info("📡 Fetching active futures instruments...")
            instruments = self.get_futures_instruments('USDT')
            if not instruments:
                self.logger.warning("⚠️ No instruments found, falling back to default coins")
                return self.top_coins
            
            self.logger.info(f"📊 Processing {len(instruments)} instruments for tradability...")
            
            # Get current prices to filter by volume
            self.logger.info("💹 Fetching current market prices for volume filtering...")
            prices = self.get_futures_prices()
            self.logger.info(f"📈 Retrieved price data for {len(prices)} symbols")
            
            tradable_symbols = []
            processed_count = 0
            skipped_count = 0
            
            for instrument in instruments:
                processed_count += 1
                try:
                    # Handle both string format (from API) and dict format
                    if isinstance(instrument, str):
                        # API returns strings like "B-MANTA_USDT"
                        # Convert to symbol format like "MANTA/USDT"
                        if instrument.startswith('B-') and instrument.endswith('_USDT'):
                            base_symbol = instrument[2:-5]  # Remove "B-" prefix and "_USDT" suffix
                            symbol = f"{base_symbol}/USDT"
                        else:
                            # Skip if format doesn't match expected pattern
                            skipped_count += 1
                            continue
                    elif isinstance(instrument, dict):
                        # Handle dict format if API changes
                        symbol = instrument.get('symbol', '').replace('USDT-', '') + '/USDT'
                    else:
                        # Skip unknown formats
                        skipped_count += 1
                        continue
                    
                    # Get price data for volume filtering
                    price_key = instrument  # Use the original instrument name as the price key
                    self.logger.debug(f"🔑 Looking for price_key: '{price_key}' in {len(prices)} price entries")
                    
                    if price_key in prices:
                        price_data = prices[price_key]
                        self.logger.debug(f"✅ Found price data for {symbol}: {price_data}")
                        price_data = prices[price_key]
                        # Try different volume field names
                        volume_24h = (price_data.get('volume') or 
                                    price_data.get('v') or 
                                    price_data.get('24h_volume') or 
                                    0)
                        
                        # Convert to float if it's a string
                        try:
                            volume_24h = float(volume_24h)
                            self.logger.debug(f"🔢 Volume for {symbol}: {volume_24h} (type: {type(volume_24h)})")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"❌ Failed to convert volume for {symbol}: {volume_24h} (error: {e})")
                            volume_24h = 0
                        
                        # Filter by minimum volume
                        if volume_24h >= self.min_volume_filter:
                            tradable_symbols.append(symbol)
                            self.logger.info(f"✅ Added {symbol} (24h volume: ${volume_24h:,.0f})")
                        else:
                            skipped_count += 1
                            self.logger.debug(f"⏭️ Skipped {symbol} (low volume: ${volume_24h:,.0f} < ${self.min_volume_filter:,.0f})")
                    else:
                        # If no price data, skip for safety
                        skipped_count += 1
                        self.logger.debug(f"⚠️ No price data for {symbol}")
                        
                except Exception as e:
                    self.logger.debug(f"Error processing instrument {instrument}: {e}")
                    continue
            
            # Apply symbol limit if specified
            if max_symbols is not None and len(tradable_symbols) > max_symbols:
                self.logger.info(f"📊 Found {len(tradable_symbols)} tradable symbols, limiting to {max_symbols} for scan performance")
                # Sort by volume would be ideal, but for now take first N symbols
                tradable_symbols = tradable_symbols[:max_symbols]
            elif max_symbols is None:
                self.logger.info(f"📊 Found {len(tradable_symbols)} tradable symbols, no limit applied (full scan)")
            else:
                self.logger.info(f"📊 Found {len(tradable_symbols)} tradable symbols, under limit of {max_symbols}")
            
            # Final summary
            self.logger.info(f"📊 INSTRUMENT SCAN SUMMARY:")
            self.logger.info(f"   📡 Total instruments fetched: {len(instruments)}")
            self.logger.info(f"   🔍 Instruments processed: {processed_count}")
            self.logger.info(f"   ✅ Tradable symbols found: {len(tradable_symbols)}")
            self.logger.info(f"   ⏭️ Symbols skipped (low volume/no data): {skipped_count}")
            self.logger.info(f"   💰 Minimum volume filter: ${self.min_volume_filter:,.0f}")
            
            if tradable_symbols:
                self.logger.info(f"🎯 SELECTED SYMBOLS FOR ANALYSIS:")
                for i, symbol in enumerate(tradable_symbols[:10], 1):  # Show first 10
                    self.logger.info(f"   {i}. {symbol}")
                if len(tradable_symbols) > 10:
                    self.logger.info(f"   ... and {len(tradable_symbols) - 10} more symbols")
            
            return tradable_symbols if tradable_symbols else self.top_coins
            
        except Exception as e:
            self.logger.error(f"❌ Error getting tradable symbols: {e}")
            self.logger.info(f"🔄 Falling back to default coins: {self.top_coins}")
            return self.top_coins
    
    def get_futures_prices(self) -> Dict[str, Dict]:
        """Get real-time futures prices for all instruments"""
        try:
            url = f"{self.public_url}/market_data/v3/current_prices/futures/rt"
            
            self.logger.info(f"💹 Fetching real-time futures prices...")
            self.logger.info(f"📡 URL: {url}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Log raw response info
            self.logger.info(f"🔍 Response status: {response.status_code}")
            raw_data = response.text
            self.logger.info(f"📄 Raw response (first 200 chars): {raw_data[:200]}...")
            
            data = response.json()
            
            # Handle different response structures
            prices = {}
            if isinstance(data, dict):
                if 'prices' in data:
                    prices = data['prices']
                elif 'data' in data:
                    prices = data['data']
                else:
                    # Assume the entire response is the prices dict
                    prices = data
            elif isinstance(data, list):
                # Convert list to dict if needed
                self.logger.warning(f"⚠️ API returned list, converting to dict")
                prices = {str(i): item for i, item in enumerate(data)}
            
            self.logger.info(f"✅ Successfully fetched prices for {len(prices)} futures symbols")
            
            # Log some sample price data
            sample_count = min(3, len(prices))
            if sample_count > 0:
                self.logger.info(f"📊 Sample price data:")
                for i, (symbol, price_data) in enumerate(list(prices.items())[:sample_count], 1):
                    if isinstance(price_data, dict):
                        last_price = (price_data.get('last_price') or 
                                    price_data.get('ls') or 
                                    price_data.get('price') or 
                                    'N/A')
                        volume = (price_data.get('volume') or 
                                price_data.get('v') or 
                                price_data.get('24h_volume') or 
                                'N/A')
                        self.logger.info(f"   {i}. {symbol}: ${last_price} (24h vol: ${volume})")
                    else:
                        self.logger.info(f"   {i}. {symbol}: {price_data}")
            
            return prices
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching futures prices: {e}")
            return {}
    
    def get_candlestick_data(self, symbol: str, timeframe: str = '5m', limit: int = 100) -> List[Dict]:
        """Fetch candlestick data for technical analysis"""
        try:
            # Convert symbol to CoinDCX futures format
            if '/' in symbol:
                base, quote = symbol.split('/')
                dcx_symbol = f"B-{base}_{quote}"
            else:
                dcx_symbol = symbol
            
            # Timeframe mapping
            timeframe_map = {
                '1m': '1',
                '5m': '5',
                '15m': '15',
                '30m': '30',
                '1h': '60',
                '4h': '240',
                '1d': '1D'
            }
            
            resolution = timeframe_map.get(timeframe, '5')
            
            # Calculate time range
            current_time = int(time.time())
            candle_duration = {
                '1': 60, '5': 300, '15': 900, '30': 1800,
                '60': 3600, '240': 14400, '1D': 86400
            }.get(resolution, 300)
            
            start_time = current_time - (candle_duration * limit * 2)
            end_time = current_time
            
            url = f"{self.public_url}/market_data/candlesticks"
            params = {
                'pair': dcx_symbol,
                'from': start_time,
                'to': end_time,
                'resolution': resolution,
                'pcode': 'f'  # 'f' for futures
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or data.get('s') != 'ok' or not data.get('data'):
                self.logger.warning(f"No candlestick data for {symbol}")
                return []
            
            candles = []
            for candle in data['data'][-limit:]:  # Get latest candles
                candles.append({
                    'timestamp': candle['time'],
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': float(candle['volume'])
                })
            
            return sorted(candles, key=lambda x: x['timestamp'])
            
        except Exception as e:
            self.logger.error(f"Error fetching candlestick data for {symbol}: {e}")
            return []
    
    def calculate_technical_indicators(self, candles: List[Dict]) -> Dict:
        """Calculate technical indicators for the given candle data"""
        if not candles or len(candles) < 50:
            return {}
        
        # Extract price arrays
        close_prices = [c['close'] for c in candles]
        high_prices = [c['high'] for c in candles]
        low_prices = [c['low'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        # Calculate indicators
        ema_20 = calculate_ema(close_prices, 20)
        ema_50 = calculate_ema(close_prices, 50)
        macd_data = calculate_macd(close_prices)
        rsi_7 = calculate_rsi(close_prices, 7)
        rsi_14 = calculate_rsi(close_prices, 14)
        atr_3 = calculate_atr(high_prices, low_prices, close_prices, 3)
        atr_14 = calculate_atr(high_prices, low_prices, close_prices, 14)
        
        # Get current values (latest values from each indicator)
        current_price = close_prices[-1]
        current_ema20 = ema_20[-1] if ema_20 else None
        current_ema50 = ema_50[-1] if ema_50 else None
        current_macd = macd_data['macd'][-1] if macd_data['macd'] else None
        current_rsi7 = rsi_7[-1] if rsi_7 else None
        current_rsi14 = rsi_14[-1] if rsi_14 else None
        current_atr3 = atr_3[-1] if atr_3 else None
        current_atr14 = atr_14[-1] if atr_14 else None
        current_volume = volumes[-1]
        avg_volume = sum(volumes[-20:]) / min(20, len(volumes))  # 20-period average volume
        
        return {
            'current_price': current_price,
            'current_ema20': current_ema20,
            'current_ema50': current_ema50,
            'current_macd': current_macd,
            'current_rsi7': current_rsi7,
            'current_rsi14': current_rsi14,
            'current_atr3': current_atr3,
            'current_atr14': current_atr14,
            'current_volume': current_volume,
            'average_volume': avg_volume,
            'price_series': close_prices[-10:],  # Last 10 prices for trend analysis
            'ema20_series': ema_20[-10:] if len(ema_20) >= 10 else ema_20,
            'macd_series': macd_data['macd'][-10:] if len(macd_data['macd']) >= 10 else macd_data['macd'],
            'rsi7_series': rsi_7[-10:] if len(rsi_7) >= 10 else rsi_7,
            'rsi14_series': rsi_14[-10:] if len(rsi_14) >= 10 else rsi_14
        }
    
    def analyze_market_signals_short_term(self, indicators: Dict) -> Dict:
        """Analyze 5-minute timeframe indicators for short-term signals"""
        if not indicators:
            return {'signal': 'FLAT', 'confidence': 0, 'reasons': []}
        
        signals = []
        reasons = []
        confidence_factors = []
        
        current_price = indicators['current_price']
        ema20 = indicators.get('current_ema20')
        ema50 = indicators.get('current_ema50')
        macd = indicators.get('current_macd')
        rsi7 = indicators.get('current_rsi7')
        rsi14 = indicators.get('current_rsi14')
        volume_ratio = indicators['current_volume'] / indicators['average_volume'] if indicators['average_volume'] > 0 else 1
        
        # Price vs EMA analysis
        if ema20 and ema50:
            if current_price > ema20 > ema50:
                signals.append('LONG')
                confidence_factors.append(25)
                reasons.append(f"Price ({current_price:.4f}) > EMA20 ({ema20:.4f}) > EMA50 ({ema50:.4f})")
            elif current_price < ema20 < ema50:
                signals.append('SHORT')
                confidence_factors.append(25)
                reasons.append(f"Price ({current_price:.4f}) < EMA20 ({ema20:.4f}) < EMA50 ({ema50:.4f})")
        
        # MACD analysis
        if macd:
            if macd > 0:
                signals.append('LONG')
                confidence_factors.append(15)
                reasons.append(f"MACD positive ({macd:.4f})")
            else:
                signals.append('SHORT')
                confidence_factors.append(15)
                reasons.append(f"MACD negative ({macd:.4f})")
        
        # RSI analysis
        if rsi7:
            if rsi7 < 30:  # Oversold
                signals.append('LONG')
                confidence_factors.append(20)
                reasons.append(f"RSI7 oversold ({rsi7:.4f})")
            elif rsi7 > 70:  # Overbought
                signals.append('SHORT')
                confidence_factors.append(20)
                reasons.append(f"RSI7 overbought ({rsi7:.4f})")
            elif 40 <= rsi7 <= 60:  # Neutral zone
                confidence_factors.append(10)
                reasons.append(f"RSI7 neutral ({rsi7:.4f})")
        
        if rsi14:
            if rsi14 < 35:  # Oversold
                signals.append('LONG')
                confidence_factors.append(15)
                reasons.append(f"RSI14 oversold ({rsi14:.4f})")
            elif rsi14 > 65:  # Overbought
                signals.append('SHORT')
                confidence_factors.append(15)
                reasons.append(f"RSI14 overbought ({rsi14:.4f})")
        
        # Volume confirmation
        if volume_ratio > 1.5:
            confidence_factors.append(10)
            reasons.append(f"High volume confirmation (x{volume_ratio:.4f})")
        elif volume_ratio < 0.5:
            confidence_factors.append(-5)
            reasons.append(f"Low volume warning (x{volume_ratio:.4f})")
        
        # Trend analysis using price series
        price_series = indicators.get('price_series', [])
        if len(price_series) >= 5:
            recent_trend = (price_series[-1] - price_series[-5]) / price_series[-5] * 100
            if recent_trend > 1:  # Strong uptrend
                signals.append('LONG')
                confidence_factors.append(10)
                reasons.append(f"Strong uptrend (+{recent_trend:.4f}%)")
            elif recent_trend < -1:  # Strong downtrend
                signals.append('SHORT')
                confidence_factors.append(10)
                reasons.append(f"Strong downtrend ({recent_trend:.4f}%)")
        
        # Determine final signal
        long_signals = signals.count('LONG')
        short_signals = signals.count('SHORT')
        
        if long_signals > short_signals:
            final_signal = 'LONG'
        elif short_signals > long_signals:
            final_signal = 'SHORT'
        else:
            final_signal = 'FLAT'
        
        # Calculate confidence
        total_confidence = sum(confidence_factors)
        confidence_percentage = min(max(total_confidence, 0), 100)
        
        return {
            'signal': final_signal,
            'confidence': confidence_percentage,
            'reasons': reasons,
            'long_signals': long_signals,
            'short_signals': short_signals,
            'volume_ratio': volume_ratio,
            'timeframe': '5m'
        }
    
    def analyze_market_signals_long_term(self, indicators: Dict) -> Dict:
        """Analyze 4-hour timeframe indicators for long-term signals"""
        if not indicators:
            return {'signal': 'FLAT', 'confidence': 0, 'reasons': []}
        
        signals = []
        reasons = []
        confidence_factors = []
        
        current_price = indicators['current_price']
        ema20 = indicators.get('current_ema20')
        ema50 = indicators.get('current_ema50')
        macd = indicators.get('current_macd')
        rsi14 = indicators.get('current_rsi14')
        atr14 = indicators.get('current_atr14')
        volume_ratio = indicators['current_volume'] / indicators['average_volume'] if indicators['average_volume'] > 0 else 1
        
        # Long-term price vs EMA analysis (higher weight for trend confirmation)
        if ema20 and ema50:
            if current_price > ema20 > ema50:
                signals.append('LONG')
                confidence_factors.append(35)  # Higher weight for long-term trend
                reasons.append(f"4H Strong bullish trend: Price ({current_price:.4f}) > EMA20 ({ema20:.4f}) > EMA50 ({ema50:.4f})")
            elif current_price < ema20 < ema50:
                signals.append('SHORT')
                confidence_factors.append(35)
                reasons.append(f"4H Strong bearish trend: Price ({current_price:.4f}) < EMA20 ({ema20:.4f}) < EMA50 ({ema50:.4f})")
            elif current_price > ema20 and ema20 < ema50:
                # Mixed signals - price above short EMA but trend is bearish
                confidence_factors.append(-10)
                reasons.append(f"4H Mixed signals: Price above EMA20 but EMA20 < EMA50")
            elif current_price < ema20 and ema20 > ema50:
                # Mixed signals - price below short EMA but trend is bullish
                confidence_factors.append(-10)
                reasons.append(f"4H Mixed signals: Price below EMA20 but EMA20 > EMA50")
        
        # Long-term MACD analysis (trend momentum)
        if macd is not None:
            if macd > 50:  # Strong bullish momentum on 4H
                signals.append('LONG')
                confidence_factors.append(25)
                reasons.append(f"4H Very strong bullish momentum: MACD = {macd:.4f}")
            elif macd > 0:
                signals.append('LONG')
                confidence_factors.append(15)
                reasons.append(f"4H Bullish momentum: MACD = {macd:.4f}")
            elif macd < -50:  # Strong bearish momentum on 4H
                signals.append('SHORT')
                confidence_factors.append(25)
                reasons.append(f"4H Very strong bearish momentum: MACD = {macd:.4f}")
            elif macd < 0:
                signals.append('SHORT')
                confidence_factors.append(15)
                reasons.append(f"4H Bearish momentum: MACD = {macd:.4f}")
        
        # Long-term RSI analysis (for major reversals)
        if rsi14 is not None:
            if rsi14 < 25:  # Severely oversold on 4H
                signals.append('LONG')
                confidence_factors.append(30)
                reasons.append(f"4H Severely oversold: RSI14 = {rsi14:.4f}")
            elif rsi14 < 35:
                signals.append('LONG')
                confidence_factors.append(20)
                reasons.append(f"4H Oversold: RSI14 = {rsi14:.4f}")
            elif rsi14 > 75:  # Severely overbought on 4H
                signals.append('SHORT')
                confidence_factors.append(30)
                reasons.append(f"4H Severely overbought: RSI14 = {rsi14:.4f}")
            elif rsi14 > 65:
                signals.append('SHORT')
                confidence_factors.append(20)
                reasons.append(f"4H Overbought: RSI14 = {rsi14:.4f}")
            elif 40 <= rsi14 <= 60:  # Neutral zone
                confidence_factors.append(10)
                reasons.append(f"4H RSI14 in neutral zone: {rsi14:.4f}")
        
        # Volume analysis for 4H timeframe
        if volume_ratio > 2.0:  # Very high volume on 4H
            confidence_factors.append(20)
            reasons.append(f"4H Very high volume confirmation: x{volume_ratio:.4f}")
        elif volume_ratio > 1.2:
            confidence_factors.append(15)
            reasons.append(f"4H High volume confirmation: x{volume_ratio:.4f}")
        elif volume_ratio < 0.3:  # Very low volume warning
            confidence_factors.append(-15)
            reasons.append(f"4H Very low volume warning: x{volume_ratio:.4f}")
        elif volume_ratio < 0.7:
            confidence_factors.append(-5)
            reasons.append(f"4H Low volume warning: x{volume_ratio:.4f}")
        
        # ATR-based volatility analysis
        if atr14 is not None:
            # High ATR suggests strong trending market
            price_atr_ratio = (atr14 / current_price) * 100
            if price_atr_ratio > 3:  # High volatility (>3%)
                confidence_factors.append(10)
                reasons.append(f"4H High volatility environment: ATR/Price = {price_atr_ratio:.4f}%")
            elif price_atr_ratio < 1:  # Low volatility (<1%)
                confidence_factors.append(-10)
                reasons.append(f"4H Low volatility (consolidation): ATR/Price = {price_atr_ratio:.4f}%")
        
        # Long-term trend analysis using price series
        price_series = indicators.get('price_series', [])
        if len(price_series) >= 5:
            long_term_trend = (price_series[-1] - price_series[0]) / price_series[0] * 100
            if long_term_trend > 3:  # Strong uptrend over 4H period
                signals.append('LONG')
                confidence_factors.append(20)
                reasons.append(f"4H Strong uptrend: +{long_term_trend:.4f}%")
            elif long_term_trend < -3:  # Strong downtrend over 4H period
                signals.append('SHORT')
                confidence_factors.append(20)
                reasons.append(f"4H Strong downtrend: {long_term_trend:.4f}%")
        
        # Determine final signal
        long_signals = signals.count('LONG')
        short_signals = signals.count('SHORT')
        
        if long_signals > short_signals:
            final_signal = 'LONG'
        elif short_signals > long_signals:
            final_signal = 'SHORT'
        else:
            final_signal = 'FLAT'
        
        # Calculate confidence
        total_confidence = sum(confidence_factors)
        confidence_percentage = min(max(total_confidence, 0), 100)
        
        return {
            'signal': final_signal,
            'confidence': confidence_percentage,
            'reasons': reasons,
            'long_signals': long_signals,
            'short_signals': short_signals,
            'volume_ratio': volume_ratio,
            'timeframe': '4h'
        }
    
    def combine_timeframe_signals(self, short_term_analysis: Dict, long_term_analysis: Dict) -> Dict:
        """Combine short-term and long-term analysis for overall signal"""
        short_confidence = short_term_analysis.get('confidence', 0)
        long_confidence = long_term_analysis.get('confidence', 0)
        
        short_signal = short_term_analysis.get('signal', 'FLAT')
        long_signal = long_term_analysis.get('signal', 'FLAT')
        
        # Calculate combined confidence based on alignment
        if short_signal == long_signal and short_signal != 'FLAT':
            # Both timeframes agree - boost confidence
            combined_confidence = min(((short_confidence * 0.6) + (long_confidence * 0.4)) * 1.2, 100)
            alignment_bonus = 15
            final_signal = short_signal
            reasons = [f"Strong alignment: Both 5m and 4h suggest {short_signal}"]
        elif short_signal == 'FLAT' or long_signal == 'FLAT':
            # One timeframe is neutral
            if short_signal != 'FLAT':
                combined_confidence = short_confidence * 0.8
                final_signal = short_signal
                alignment_bonus = 0
                reasons = [f"Mixed signals: 5m suggests {short_signal}, 4h neutral"]
            elif long_signal != 'FLAT':
                combined_confidence = long_confidence * 0.7
                final_signal = long_signal
                alignment_bonus = 0
                reasons = [f"Mixed signals: 4h suggests {long_signal}, 5m neutral"]
            else:
                combined_confidence = (short_confidence + long_confidence) / 2
                final_signal = 'FLAT'
                alignment_bonus = 0
                reasons = ["Both timeframes neutral"]
        else:
            # Conflicting signals - reduce confidence significantly
            combined_confidence = max((short_confidence + long_confidence) / 2 - 30, 0)
            final_signal = 'FLAT'  # Default to flat when conflicting
            alignment_bonus = -20
            reasons = [f"Conflicting signals: 5m suggests {short_signal}, 4h suggests {long_signal}"]
        
        return {
            'signal': final_signal,
            'combined_confidence': round(combined_confidence),
            'short_term_confidence': short_confidence,
            'long_term_confidence': long_confidence,
            'alignment_bonus': alignment_bonus,
            'reasons': reasons,
            'short_term_analysis': short_term_analysis,
            'long_term_analysis': long_term_analysis
        }
    
    def calculate_entry_tp_sl(self, signal_data: Dict, indicators: Dict) -> Dict:
        """Calculate entry, take profit, and stop loss levels (legacy method)"""
        if signal_data['confidence'] < self.confidence_threshold:
            return {}
        
        current_price = indicators['current_price']
        atr = indicators.get('current_atr14', current_price * 0.02)  # Use 2% if ATR not available
        
        signal = signal_data['signal']
        
        if signal == 'LONG':
            entry_price = current_price
            stop_loss = entry_price - (atr * 1.5)  # 1.5x ATR below entry
            take_profit = entry_price + (atr * 3.0)  # 2:1 risk-reward ratio
            
        elif signal == 'SHORT':
            entry_price = current_price
            stop_loss = entry_price + (atr * 1.5)  # 1.5x ATR above entry
            take_profit = entry_price - (atr * 3.0)  # 2:1 risk-reward ratio
            
        else:
            return {}
        
        risk_amount = abs(entry_price - stop_loss)
        reward_amount = abs(take_profit - entry_price)
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
        
        return {
            'entry_price': round(entry_price, 4),
            'take_profit': round(take_profit, 4),
            'stop_loss': round(stop_loss, 4),
            'risk_amount': round(risk_amount, 4),
            'reward_amount': round(reward_amount, 4),
            'risk_reward_ratio': round(risk_reward_ratio, 4)
        }
    
    def calculate_entry_tp_sl_multi_timeframe(self, combined_analysis: Dict, indicators: Dict) -> Dict:
        """Calculate entry, take profit, and stop loss levels using multi-timeframe analysis"""
        combined_confidence = combined_analysis.get('combined_confidence', 0)
        
        if combined_confidence < self.confidence_threshold:
            return {}
        
        current_price = indicators['current_price']
        atr = indicators.get('current_atr14', current_price * 0.02)  # Use 2% if ATR not available
        
        signal = combined_analysis['signal']
        short_confidence = combined_analysis.get('short_term_confidence', 0)
        long_confidence = combined_analysis.get('long_term_confidence', 0)
        
        # Adjust risk/reward based on timeframe confidence alignment
        if short_confidence >= 70 and long_confidence >= 70:
            # High confidence on both timeframes - tighter stops, bigger targets
            atr_multiplier_sl = 1.2  # Tighter stop loss
            atr_multiplier_tp = 3.5  # Bigger target
        elif short_confidence >= 60 or long_confidence >= 60:
            # Medium confidence - standard risk/reward
            atr_multiplier_sl = 1.5
            atr_multiplier_tp = 3.0
        else:
            # Lower confidence - wider stops, closer targets
            atr_multiplier_sl = 2.0
            atr_multiplier_tp = 2.5
        
        if signal == 'LONG':
            entry_price = current_price
            stop_loss = entry_price - (atr * atr_multiplier_sl)
            take_profit = entry_price + (atr * atr_multiplier_tp)
            
        elif signal == 'SHORT':
            entry_price = current_price
            stop_loss = entry_price + (atr * atr_multiplier_sl)
            take_profit = entry_price - (atr * atr_multiplier_tp)
            
        else:
            return {}
        
        risk_amount = abs(entry_price - stop_loss)
        reward_amount = abs(take_profit - entry_price)
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
        
        return {
            'entry_price': round(entry_price, 4),
            'take_profit': round(take_profit, 4),
            'stop_loss': round(stop_loss, 4),
            'risk_amount': round(risk_amount, 4),
            'reward_amount': round(reward_amount, 4),
            'risk_reward_ratio': round(risk_reward_ratio, 4),
            'atr_multiplier_sl': atr_multiplier_sl,
            'atr_multiplier_tp': atr_multiplier_tp
        }
    
    def analyze_single_coin(self, symbol: str) -> Dict:
        """Analyze a single coin and generate trading signal"""
        self.logger.info(f"Analyzing {symbol}...")
        
        # Get 5-minute candlestick data
        candles_5m = self.get_candlestick_data(symbol, '5m', 100)
        
        if not candles_5m:
            self.logger.warning(f"No 5m data available for {symbol}")
            return {'symbol': symbol, 'error': 'No 5m data available'}
        
        # Get 4-hour candlestick data for longer-term context
        candles_4h = self.get_candlestick_data(symbol, '4h', 50)
        
        # Calculate indicators for 5m timeframe
        indicators_5m = self.calculate_technical_indicators(candles_5m)
        
        if not indicators_5m:
            return {'symbol': symbol, 'error': 'Could not calculate indicators'}
        
        # Calculate indicators for 4h timeframe
        indicators_4h = self.calculate_technical_indicators(candles_4h) if candles_4h else {}
        
        # Generate trading signals for both timeframes
        short_term_analysis = self.analyze_market_signals_short_term(indicators_5m)
        long_term_analysis = self.analyze_market_signals_long_term(indicators_4h) if indicators_4h else {
            'signal': 'FLAT', 'confidence': 0, 'reasons': ['No 4h data available'], 
            'long_signals': 0, 'short_signals': 0, 'volume_ratio': 1, 'timeframe': '4h'
        }
        
        # Combine timeframe analyses
        combined_analysis = self.combine_timeframe_signals(short_term_analysis, long_term_analysis)
        
        # Use combined confidence for trade levels calculation
        trade_levels = self.calculate_entry_tp_sl_multi_timeframe(combined_analysis, indicators_5m)
        
        # Compile results
        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timeframe': '5m',
            
            # Current market data
            'current_price': indicators_5m['current_price'],
            'current_ema20': indicators_5m.get('current_ema20'),
            'current_macd': indicators_5m.get('current_macd'),
            'current_rsi7': indicators_5m.get('current_rsi7'),
            'current_rsi14': indicators_5m.get('current_rsi14'),
            'current_volume': indicators_5m['current_volume'],
            'volume_ratio': short_term_analysis.get('volume_ratio', 1),
            
            # 5-minute context
            'price_series_5m': indicators_5m.get('price_series', []),
            'ema20_series_5m': indicators_5m.get('ema20_series', []),
            'macd_series_5m': indicators_5m.get('macd_series', []),
            'rsi7_series_5m': indicators_5m.get('rsi7_series', []),
            'rsi14_series_5m': indicators_5m.get('rsi14_series', []),
            
            # 4-hour context
            '4h_ema20': indicators_4h.get('current_ema20'),
            '4h_ema50': indicators_4h.get('current_ema50'),
            '4h_atr3': indicators_4h.get('current_atr3'),
            '4h_atr14': indicators_4h.get('current_atr14'),
            '4h_rsi14': indicators_4h.get('current_rsi14'),
            '4h_volume_ratio': long_term_analysis.get('volume_ratio', 1),
            
            # Multi-timeframe signal analysis
            'signal': combined_analysis['signal'],
            'combined_confidence': combined_analysis['combined_confidence'],
            'short_term_confidence': combined_analysis['short_term_confidence'],
            'long_term_confidence': combined_analysis['long_term_confidence'],
            'alignment_bonus': combined_analysis['alignment_bonus'],
            'combined_reasons': combined_analysis['reasons'],
            
            # Individual timeframe analysis
            'short_term_analysis': short_term_analysis,
            'long_term_analysis': long_term_analysis,
            
            # Trade levels (if combined confidence > threshold)
            'trade_levels': trade_levels
        }
        
        return analysis
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk management"""
        risk_amount = self.virtual_current_balance * self.risk_per_trade
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk > 0:
            position_size = risk_amount / price_risk
            return round(position_size, 6)
        return 0.0
    
    def open_virtual_position(self, analysis: Dict) -> Dict:
        """Open a virtual position based on analysis"""
        if not self.virtual_trading_enabled:
            return {'status': 'disabled', 'message': 'Virtual trading disabled'}
        
        # Check if we already have a position for this symbol
        symbol = analysis['symbol']
        if symbol in self.virtual_positions:
            return {'status': 'exists', 'message': f'Position already exists for {symbol}'}
        
        # Check maximum positions limit
        if len(self.virtual_positions) >= self.max_positions:
            return {'status': 'limit', 'message': f'Maximum positions limit reached ({self.max_positions})'}
        
        # Check if we have trade levels (high confidence required)
        if not analysis.get('trade_levels'):
            return {'status': 'no_signal', 'message': 'No high confidence trade signal'}
        
        trade_levels = analysis['trade_levels']
        entry_price = trade_levels['entry_price']
        stop_loss = trade_levels['stop_loss']
        take_profit = trade_levels['take_profit']
        
        # Calculate position size
        position_size = self.calculate_position_size(entry_price, stop_loss)
        
        if position_size <= 0:
            return {'status': 'error', 'message': 'Invalid position size calculated'}
        
        # Check if we have enough balance
        required_margin = position_size * entry_price * 0.1  # Assuming 10x leverage
        if required_margin > self.virtual_current_balance:
            return {'status': 'insufficient_funds', 'message': 'Insufficient virtual balance'}
        
        # Create virtual position
        position = {
            'symbol': symbol,
            'signal': analysis['signal'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'margin_used': required_margin,
            'entry_time': datetime.now(),
            'combined_confidence': analysis.get('combined_confidence', 0),
            'short_confidence': analysis.get('short_term_confidence', 0),
            'long_confidence': analysis.get('long_term_confidence', 0),
            'status': 'open',
            'current_price': entry_price,
            'unrealized_pnl': 0.0
        }
        
        # Update virtual balance and positions
        self.virtual_current_balance -= required_margin
        self.virtual_positions[symbol] = position
        
        self.logger.info(f"📈 Opened virtual {analysis['signal']} position for {symbol}")
        
        return {
            'status': 'opened',
            'message': f"Virtual {analysis['signal']} position opened for {symbol}",
            'position': position
        }
    
    def update_virtual_positions(self, current_prices: Dict[str, float]) -> List[Dict]:
        """Update virtual positions with current prices and check for TP/SL"""
        closed_positions = []
        
        for symbol, position in list(self.virtual_positions.items()):
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            position['current_price'] = current_price
            
            # Calculate unrealized PnL
            if position['signal'] == 'LONG':
                pnl = (current_price - position['entry_price']) * position['position_size']
            else:  # SHORT
                pnl = (position['entry_price'] - current_price) * position['position_size']
            
            position['unrealized_pnl'] = round(pnl, 4)
            
            # Check for TP/SL hits
            should_close = False
            close_reason = ""
            close_price = current_price
            
            if position['signal'] == 'LONG':
                if current_price >= position['take_profit']:
                    should_close = True
                    close_reason = "Take Profit Hit"
                    close_price = position['take_profit']
                elif current_price <= position['stop_loss']:
                    should_close = True
                    close_reason = "Stop Loss Hit"
                    close_price = position['stop_loss']
            else:  # SHORT
                if current_price <= position['take_profit']:
                    should_close = True
                    close_reason = "Take Profit Hit"
                    close_price = position['take_profit']
                elif current_price >= position['stop_loss']:
                    should_close = True
                    close_reason = "Stop Loss Hit"
                    close_price = position['stop_loss']
            
            if should_close:
                closed_position = self.close_virtual_position(symbol, close_price, close_reason)
                if closed_position:
                    closed_positions.append(closed_position)
        
        return closed_positions
    
    def close_virtual_position(self, symbol: str, close_price: float, reason: str = "Manual") -> Dict:
        """Close a virtual position"""
        if symbol not in self.virtual_positions:
            return {'status': 'not_found', 'message': f'No position found for {symbol}'}
        
        position = self.virtual_positions[symbol]
        
        # Calculate final PnL
        if position['signal'] == 'LONG':
            pnl = (close_price - position['entry_price']) * position['position_size']
        else:  # SHORT
            pnl = (position['entry_price'] - close_price) * position['position_size']
        
        # Calculate return percentage
        return_pct = (pnl / position['margin_used']) * 100 if position['margin_used'] > 0 else 0
        
        # Create trade record
        trade_record = {
            'symbol': symbol,
            'signal': position['signal'],
            'entry_price': position['entry_price'],
            'close_price': close_price,
            'stop_loss': position['stop_loss'],
            'take_profit': position['take_profit'],
            'position_size': position['position_size'],
            'margin_used': position['margin_used'],
            'entry_time': position['entry_time'],
            'close_time': datetime.now(),
            'pnl': round(pnl, 4),
            'return_pct': round(return_pct, 2),
            'close_reason': reason,
            'duration': datetime.now() - position['entry_time'],
            'combined_confidence': position.get('combined_confidence', 0),
            'short_confidence': position.get('short_confidence', 0),
            'long_confidence': position.get('long_confidence', 0)
        }
        
        # Update virtual balance
        self.virtual_current_balance += position['margin_used'] + pnl
        
        # Add to trade history and remove from active positions
        self.virtual_trade_history.append(trade_record)
        del self.virtual_positions[symbol]
        
        self.logger.info(f"💰 Closed virtual position for {symbol}: PnL = ${pnl:.4f} ({return_pct:.2f}%) - {reason}")
        
        return {
            'status': 'closed',
            'message': f"Position closed for {symbol}",
            'trade': trade_record
        }
    
    def get_virtual_portfolio_summary(self) -> Dict:
        """Get summary of virtual portfolio performance"""
        total_pnl = sum([trade['pnl'] for trade in self.virtual_trade_history])
        winning_trades = [trade for trade in self.virtual_trade_history if trade['pnl'] > 0]
        losing_trades = [trade for trade in self.virtual_trade_history if trade['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(self.virtual_trade_history) * 100 if self.virtual_trade_history else 0
        avg_win = sum([trade['pnl'] for trade in winning_trades]) / len(winning_trades) if winning_trades else 0
        avg_loss = sum([trade['pnl'] for trade in losing_trades]) / len(losing_trades) if losing_trades else 0
        
        # Calculate unrealized PnL from active positions
        unrealized_pnl = sum([pos['unrealized_pnl'] for pos in self.virtual_positions.values()])
        
        # Total portfolio value
        total_portfolio_value = self.virtual_current_balance + sum([pos['margin_used'] for pos in self.virtual_positions.values()]) + unrealized_pnl
        total_return = ((total_portfolio_value - self.virtual_balance) / self.virtual_balance) * 100
        
        return {
            'starting_balance': self.virtual_balance,
            'current_balance': round(self.virtual_current_balance, 4),
            'total_portfolio_value': round(total_portfolio_value, 4),
            'total_return_pct': round(total_return, 2),
            'realized_pnl': round(total_pnl, 4),
            'unrealized_pnl': round(unrealized_pnl, 4),
            'total_trades': len(self.virtual_trade_history),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 4),
            'avg_loss': round(avg_loss, 4),
            'active_positions': len(self.virtual_positions),
            'margin_used': sum([pos['margin_used'] for pos in self.virtual_positions.values()])
        }
    
    def analyze_top_coins(self) -> List[Dict]:
        """Analyze coins and return results with virtual position management"""
        results = []
        current_prices = {}
        
        # Get symbols to analyze
        if self.scan_all_instruments:
            symbols_to_analyze = self.get_all_tradable_symbols()
            self.logger.info(f"🔍 Starting analysis of {len(symbols_to_analyze)} active instruments...")
        else:
            symbols_to_analyze = self.top_coins
            self.logger.info(f"📊 Starting analysis of {len(symbols_to_analyze)} selected coins...")
        
        # Track high confidence signals for summary
        high_confidence_signals = []
        
        for i, symbol in enumerate(symbols_to_analyze, 1):
            try:
                if self.scan_all_instruments:
                    self.logger.info(f"📊 Analyzing {symbol} ({i}/{len(symbols_to_analyze)})...")
                
                analysis = self.analyze_single_coin(symbol)
                results.append(analysis)
                current_prices[symbol] = analysis.get('current_price', 0)
                
                # Track high confidence signals
                confidence = analysis.get('combined_confidence', 0)
                if confidence >= self.confidence_threshold and analysis.get('signal') in ['LONG', 'SHORT']:
                    high_confidence_signals.append({
                        'symbol': symbol,
                        'confidence': confidence,
                        'signal': analysis.get('signal'),
                        'analysis': analysis
                    })
                    self.logger.info(f"🔥 HIGH CONFIDENCE: {symbol} - {analysis.get('signal')} ({confidence}%)")
                
                # Auto-open virtual position if high confidence and virtual trading enabled
                if (self.virtual_trading_enabled and 
                    analysis.get('combined_confidence', 0) >= self.confidence_threshold and 
                    analysis.get('signal') in ['LONG', 'SHORT'] and 
                    symbol not in self.virtual_positions and
                    analysis.get('trade_levels')):
                    
                    position_result = self.open_virtual_position(analysis)
                    if position_result['status'] == 'opened':
                        self.logger.info(f"🎯 Auto-opened virtual position: {position_result['message']}")
                    else:
                        self.logger.info(f"⚠️  Could not open position: {position_result['message']}")
                
                # Brief pause to avoid rate limiting (shorter for single coins)
                if self.scan_all_instruments:
                    time.sleep(0.3)  # Faster scanning for many instruments
                else:
                    time.sleep(0.5)  # Original timing for few coins
                
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")
                results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # Log summary of high confidence signals found
        if high_confidence_signals:
            self.logger.info(f"🎯 SCAN COMPLETE: Found {len(high_confidence_signals)} high confidence signals!")
            for signal in sorted(high_confidence_signals, key=lambda x: x['confidence'], reverse=True)[:5]:
                self.logger.info(f"   🔥 {signal['symbol']}: {signal['signal']} ({signal['confidence']}%)")
        else:
            self.logger.info(f"📊 SCAN COMPLETE: No high confidence signals found (threshold: {self.confidence_threshold}%)")
        
        # Update existing virtual positions with current prices
        if self.virtual_trading_enabled and current_prices:
            closed_positions = self.update_virtual_positions(current_prices)
            for closed_pos in closed_positions:
                if closed_pos['status'] == 'closed':
                    trade = closed_pos['trade']
                    self.logger.info(f"🔔 Position auto-closed: {trade['symbol']} - PnL: ${trade['pnl']:.4f} - {trade['close_reason']}")
        
        return results
    
    def enable_full_market_scan(self, min_volume=100000):
        """Enable scanning of all active instruments"""
        self.scan_all_instruments = True
        self.min_volume_filter = min_volume
        self.logger.info(f"🔍 Enabled full market scan (min volume: ${min_volume:,})")
    
    def disable_full_market_scan(self):
        """Disable full market scan, return to selected coins"""
        self.scan_all_instruments = False
        self.logger.info(f"📊 Disabled full market scan, using selected coins: {self.top_coins}")
    
    def scan_for_high_confidence_signals(self, min_confidence=80, max_results=10) -> List[Dict]:
        """Scan all instruments and return only high confidence signals"""
        original_threshold = self.confidence_threshold
        original_scan_mode = self.scan_all_instruments
        
        try:
            # Temporarily configure for scanning
            self.confidence_threshold = min_confidence
            self.scan_all_instruments = True
            
            self.logger.info(f"🔍 Scanning all instruments for signals ≥{min_confidence}% confidence...")
            
            # Run analysis
            results = self.analyze_top_coins()
            
            # Filter and sort high confidence results
            high_conf_results = []
            for result in results:
                if (not result.get('error') and 
                    result.get('combined_confidence', 0) >= min_confidence and
                    result.get('signal') in ['LONG', 'SHORT']):
                    high_conf_results.append(result)
            
            # Sort by confidence (highest first)
            high_conf_results.sort(key=lambda x: x.get('combined_confidence', 0), reverse=True)
            
            # Limit results
            if max_results and len(high_conf_results) > max_results:
                high_conf_results = high_conf_results[:max_results]
            
            return high_conf_results
            
        finally:
            # Restore original settings
            self.confidence_threshold = original_threshold
            self.scan_all_instruments = original_scan_mode
        
        return results
    
    def print_analysis_summary(self, results: List[Dict]):
        """Print formatted analysis summary"""
        print("\n" + "="*80)
        print("🚀 COINDCX FUTURES TRADING ANALYSIS")
        print("="*80)
        print(f"📊 Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💹 Confidence Threshold: {self.confidence_threshold}%")
        print("="*80)
        
        high_confidence_trades = []
        
        for result in results:
            if 'error' in result:
                print(f"\n❌ {result['symbol']}: {result['error']}")
                continue
            
            symbol = result['symbol']
            price = result['current_price']
            signal = result['signal']
            combined_confidence = result.get('combined_confidence', 0)
            short_confidence = result.get('short_term_confidence', 0)
            long_confidence = result.get('long_term_confidence', 0)
            
            # Status indicators
            signal_emoji = "📈" if signal == "LONG" else "📉" if signal == "SHORT" else "⏸️"
            confidence_emoji = "🔥" if combined_confidence >= 80 else "⚡" if combined_confidence >= 60 else "💫"
            
            print(f"\n{signal_emoji} {symbol}")
            print(f"   💰 Price: ${price:.4f}")
            print(f"   📊 EMA20 (5m): ${result.get('current_ema20', 0):.4f}")
            print(f"   � EMA20 (4h): ${result.get('4h_ema20', 0):.4f}")
            print(f"   �📈 MACD (5m): {result.get('current_macd', 0):.4f}")
            print(f"   🎯 RSI(7): {result.get('current_rsi7', 0):.4f}")
            print(f"   🎯 RSI(14) 5m: {result.get('current_rsi14', 0):.4f}")
            print(f"   🎯 RSI(14) 4h: {result.get('4h_rsi14', 0):.4f}")
            print(f"   🔊 Volume 5m: x{result.get('volume_ratio', 1):.4f}")
            print(f"   🔊 Volume 4h: x{result.get('4h_volume_ratio', 1):.4f}")
            
            print(f"\n   {confidence_emoji} SIGNAL: {signal}")
            print(f"   📊 Combined Confidence: {combined_confidence}%")
            print(f"   ⏱️ Short-term (5m): {short_confidence}%")
            print(f"   ⏰ Long-term (4h): {long_confidence}%")
            
            # Show alignment analysis
            alignment_bonus = result.get('alignment_bonus', 0)
            if alignment_bonus > 0:
                print(f"   ✅ Timeframe Alignment: +{alignment_bonus}% bonus")
            elif alignment_bonus < 0:
                print(f"   ⚠️ Timeframe Conflict: {alignment_bonus}% penalty")
            else:
                print(f"   ➡️ Mixed Timeframe Signals")
            
            # Show trade levels if high confidence
            if combined_confidence >= self.confidence_threshold and result.get('trade_levels'):
                levels = result['trade_levels']
                print(f"\n   � TRADE SETUP:")
                print(f"   �📍 ENTRY: ${levels['entry_price']:.4f}")
                print(f"   🎯 TP: ${levels['take_profit']:.4f}")
                print(f"   🛡️ SL: ${levels['stop_loss']:.4f}")
                print(f"   ⚖️ R:R = 1:{levels['risk_reward_ratio']:.4f}")
                if 'atr_multiplier_sl' in levels:
                    print(f"   📏 ATR Multipliers: SL={levels['atr_multiplier_sl']:.1f}x, TP={levels['atr_multiplier_tp']:.1f}x")
                
                high_confidence_trades.append({
                    'symbol': symbol,
                    'signal': signal,
                    'confidence': combined_confidence,
                    'short_confidence': short_confidence,
                    'long_confidence': long_confidence,
                    'levels': levels
                })
            
            # Show timeframe-specific reasons
            print(f"\n   📝 Analysis Summary:")
            if result.get('combined_reasons'):
                for i, reason in enumerate(result['combined_reasons'], 1):
                    print(f"      {i}. {reason}")
            
            # Show individual timeframe analysis
            short_analysis = result.get('short_term_analysis', {})
            long_analysis = result.get('long_term_analysis', {})
            
            if short_analysis.get('reasons'):
                print(f"   � Short-term (5m) Key Factors:")
                for i, reason in enumerate(short_analysis['reasons'][:2], 1):
                    print(f"      • {reason}")
            
            if long_analysis.get('reasons'):
                print(f"   🔍 Long-term (4h) Key Factors:")
                for i, reason in enumerate(long_analysis['reasons'][:2], 1):
                    print(f"      • {reason}")
        
        # High confidence trades summary
        if high_confidence_trades:
            print(f"\n{'='*80}")
            print(f"🔥 HIGH CONFIDENCE TRADES (≥{self.confidence_threshold}%)")
            print("="*80)
            
            for i, trade in enumerate(high_confidence_trades, 1):
                signal_direction = "📈 LONG" if trade['signal'] == "LONG" else "📉 SHORT"
                print(f"\n{i}. {signal_direction} {trade['symbol']}")
                print(f"   🎯 Combined Confidence: {trade['confidence']}%")
                print(f"   ⏱️ Short-term: {trade['short_confidence']}% | ⏰ Long-term: {trade['long_confidence']}%")
                print(f"   📍 Entry: ${trade['levels']['entry_price']:.4f}")
                print(f"   🎯 TP: ${trade['levels']['take_profit']:.4f}")
                print(f"   🛡️ SL: ${trade['levels']['stop_loss']:.4f}")
                print(f"   💰 Risk: ${trade['levels']['risk_amount']:.4f} | Reward: ${trade['levels']['reward_amount']:.4f}")
        else:
            print(f"\n⚠️ No high confidence trades found (threshold: {self.confidence_threshold}%)")
        
        # Virtual Portfolio Summary
        if self.virtual_trading_enabled:
            portfolio_summary = self.get_virtual_portfolio_summary()
            
            print(f"\n{'='*80}")
            print("💼 VIRTUAL PORTFOLIO SUMMARY")
            print("="*80)
            print(f"💰 Starting Balance: ${portfolio_summary['starting_balance']:,.2f}")
            print(f"💵 Current Balance: ${portfolio_summary['current_balance']:,.2f}")
            print(f"📊 Total Portfolio Value: ${portfolio_summary['total_portfolio_value']:,.2f}")
            print(f"📈 Total Return: {portfolio_summary['total_return_pct']:+.2f}%")
            
            if portfolio_summary['total_trades'] > 0:
                print(f"\n📋 TRADING STATISTICS:")
                print(f"   🎯 Total Trades: {portfolio_summary['total_trades']}")
                print(f"   ✅ Winning Trades: {portfolio_summary['winning_trades']}")
                print(f"   ❌ Losing Trades: {portfolio_summary['losing_trades']}")
                print(f"   📊 Win Rate: {portfolio_summary['win_rate']:.1f}%")
                print(f"   💚 Average Win: ${portfolio_summary['avg_win']:+.4f}")
                print(f"   🔴 Average Loss: ${portfolio_summary['avg_loss']:+.4f}")
                print(f"   💰 Realized P&L: ${portfolio_summary['realized_pnl']:+.4f}")
                print(f"   📊 Unrealized P&L: ${portfolio_summary['unrealized_pnl']:+.4f}")
            
            # Active Positions
            if self.virtual_positions:
                print(f"\n🔥 ACTIVE POSITIONS ({len(self.virtual_positions)}):")
                for symbol, pos in self.virtual_positions.items():
                    duration = datetime.now() - pos['entry_time']
                    hours = int(duration.total_seconds() // 3600)
                    minutes = int((duration.total_seconds() % 3600) // 60)
                    
                    pnl_emoji = "💚" if pos['unrealized_pnl'] > 0 else "🔴" if pos['unrealized_pnl'] < 0 else "🟡"
                    signal_emoji = "📈" if pos['signal'] == "LONG" else "📉"
                    
                    print(f"   {signal_emoji} {symbol} ({pos['signal']})")
                    print(f"      📍 Entry: ${pos['entry_price']:.4f} | Current: ${pos['current_price']:.4f}")
                    print(f"      {pnl_emoji} P&L: ${pos['unrealized_pnl']:+.4f} ({(pos['unrealized_pnl']/pos['margin_used']*100):+.2f}%)")
                    print(f"      ⏰ Duration: {hours}h {minutes}m")
                    print(f"      🎯 TP: ${pos['take_profit']:.4f} | SL: ${pos['stop_loss']:.4f}")
            else:
                print(f"\n📭 No active positions")
            
            print(f"   💼 Available Balance: ${portfolio_summary['current_balance']:,.2f}")
            print(f"   🔒 Margin Used: ${portfolio_summary['margin_used']:,.2f}")
        
        print(f"\n{'='*80}")
    
    def run_continuous_monitoring(self, interval_minutes: int = 5):
        """Run continuous monitoring every 5 minutes"""
        self.logger.info(f"Starting continuous monitoring (every {interval_minutes} minutes)...")
        
        while True:
            try:
                # Analyze all coins
                results = self.analyze_top_coins()
                
                # Print summary
                self.print_analysis_summary(results)
                
                # Wait for next interval
                print(f"\n⏱️ Next analysis in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                print(f"❌ Error: {e}")
                print(f"⏱️ Retrying in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)

def main():
    """Main function to run the trading analysis"""
    print("🚀 Initializing CoinDCX Futures Trading Agent...")
    
    # Create trader instance
    trader = CoinDCXFuturesTrader()
    
    # Check if we should run continuously or just once
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--monitor':
        trader.run_continuous_monitoring()
    else:
        # Run single analysis
        results = trader.analyze_top_coins()
        trader.print_analysis_summary(results)

if __name__ == "__main__":
    main()
