#!/usr/bin/env python3
"""
Flask Web Dashboard for SolSignals Trading Monitor
Displays real-time trading signals in a web interface
"""

import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from threading import Thread, Lock
from exchanges.factory import ExchangeFactory
from database import get_database
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("INFO: Loaded environment variables from .env file")
except ImportError:
    print("WARNING: python-dotenv not installed, using system environment variables only")
except Exception as e:
    print(f"WARNING: Could not load .env file: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = get_database()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global variables for storing latest data
latest_data = {
    'price': 0.0,
    'ema': 0.0,
    'gap': 0.0,
    'volume': 0.0,
    'within_threshold': False,
    'timestamp': '',
    'exchange': '',
    'symbol': '',
    'threshold': 0.0,
    'ema_period': 50,
    'timeframe': '15m',
    'status': 'Initializing...',
    'historical_data': []
}
data_lock = Lock()

# Global exchange instance for API routes
global_exchange = None

# Configuration
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL_MINUTES', 1)) * 60  # Convert to seconds
SYMBOL = os.getenv('TRADING_SYMBOL', 'SOL/USDT')
EMA_PERIOD = int(os.getenv('EMA_PERIOD', 50))
THRESHOLD = float(os.getenv('PRICE_THRESHOLD', 0.1))
TIMEFRAME = os.getenv('TIMEFRAME', '15m')

# Database cleanup configuration
MAX_DB_SIZE_MB = float(os.getenv('MAX_DB_SIZE_MB', 10.0))  # Maximum DB size in MB
CLEANUP_RETENTION_DAYS = int(os.getenv('CLEANUP_RETENTION_DAYS', 7))  # Keep last N days


def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return None
    
    # Start with SMA for the first EMA value
    sma = sum(prices[:period]) / period
    ema = sma
    
    # Calculate multiplier
    multiplier = 2 / (period + 1)
    
    # Calculate EMA for remaining prices
    for i in range(period, len(prices)):
        ema = (prices[i] * multiplier) + (ema * (1 - multiplier))
    
    return ema


def detect_support_resistance(ohlcv_data, lookback_period=10, min_touches=2):
    """
    Detect support and resistance levels from OHLCV data
    
    Args:
        ohlcv_data: List of OHLCV candles [timestamp, open, high, low, close, volume]
        lookback_period: Number of periods to look back for pivot detection (optimized for 4h timeframe)
        min_touches: Minimum number of times a level must be touched to be considered valid
    
    Returns:
        dict: {
            'support_levels': [list of support prices],
            'resistance_levels': [list of resistance prices],
            'current_support': float or None,
            'current_resistance': float or None
        }
    """
    if len(ohlcv_data) < lookback_period * 3:  # Need more data for 4h analysis
        return {
            'support_levels': [],
            'resistance_levels': [],
            'current_support': None,
            'current_resistance': None
        }
    
    # Extract highs and lows
    highs = [candle[2] for candle in ohlcv_data]  # High prices
    lows = [candle[3] for candle in ohlcv_data]   # Low prices
    closes = [candle[4] for candle in ohlcv_data] # Close prices
    
    # Find pivot highs and lows
    pivot_highs = []
    pivot_lows = []
    
    # Look for pivot points (local maxima and minima)
    for i in range(lookback_period, len(ohlcv_data) - lookback_period):
        # Check for pivot high
        is_pivot_high = True
        for j in range(i - lookback_period, i + lookback_period + 1):
            if j != i and highs[j] >= highs[i]:
                is_pivot_high = False
                break
        
        if is_pivot_high:
            pivot_highs.append(highs[i])
        
        # Check for pivot low
        is_pivot_low = True
        for j in range(i - lookback_period, i + lookback_period + 1):
            if j != i and lows[j] <= lows[i]:
                is_pivot_low = False
                break
        
        if is_pivot_low:
            pivot_lows.append(lows[i])
    
    # Group similar levels together (wider tolerance for 4h timeframe)
    def group_levels(levels, tolerance_pct=1.0):  # Increased tolerance for 4h timeframe
        if not levels:
            return []
        
        levels = sorted(levels)
        grouped = []
        current_group = [levels[0]]
        
        for level in levels[1:]:
            # Check if this level is within tolerance of the current group average
            group_avg = sum(current_group) / len(current_group)
            if abs(level - group_avg) / group_avg <= tolerance_pct / 100:
                current_group.append(level)
            else:
                # Start new group if current group has enough touches
                if len(current_group) >= min_touches:
                    grouped.append(sum(current_group) / len(current_group))
                current_group = [level]
        
        # Don't forget the last group
        if len(current_group) >= min_touches:
            grouped.append(sum(current_group) / len(current_group))
        
        return grouped
    
    # Group and filter levels
    support_levels = group_levels(pivot_lows, tolerance_pct=1.0)
    resistance_levels = group_levels(pivot_highs, tolerance_pct=1.0)
    
    # Find current support and resistance relative to current price
    current_price = closes[-1]
    
    # Current support: highest support level below current price
    current_support = None
    for level in sorted(support_levels, reverse=True):
        if level < current_price:
            current_support = level
            break
    
    # Current resistance: lowest resistance level above current price
    current_resistance = None
    for level in sorted(resistance_levels):
        if level > current_price:
            current_resistance = level
            break
    
    return {
        'support_levels': sorted(support_levels),
        'resistance_levels': sorted(resistance_levels),
        'current_support': current_support,
        'current_resistance': current_resistance
    }


def generate_trading_signal(current_price, previous_price, current_ema, previous_ema, current_volume, avg_volume, threshold):
    """
    Generate buy/sell signals based on multiple criteria
    
    Returns:
        tuple: (signal_type, signal_strength, reason)
        signal_type: 'BUY', 'SELL', 'HOLD', 'STRONG_BUY', 'STRONG_SELL'
        signal_strength: 0.0 to 1.0 (confidence level)
        reason: explanation of the signal
    """
    signals = []
    total_weight = 0
    signal_type = "HOLD"
    reason = "No clear signal"
    
    # 1. EMA Crossover Signal (High importance - weight: 3)
    if previous_price is not None and previous_ema is not None:
        if previous_price <= previous_ema and current_price > current_ema:
            signals.append(("BUY", 3, "Price crossed above EMA (bullish)"))
        elif previous_price >= previous_ema and current_price < current_ema:
            signals.append(("SELL", 3, "Price crossed below EMA (bearish)"))
    
    # 2. Price-EMA Distance Signal (Medium importance - weight: 2)
    gap = current_price - current_ema
    gap_percentage = (gap / current_ema) * 100
    
    if abs(gap_percentage) <= threshold:
        if gap > 0:
            signals.append(("BUY", 2, f"Price close above EMA (+{gap_percentage:.2f}%)"))
        else:
            signals.append(("SELL", 2, f"Price close below EMA ({gap_percentage:.2f}%)"))
    
    # 3. Price Momentum Signal (Medium importance - weight: 2)
    if previous_price is not None:
        price_change_pct = ((current_price - previous_price) / previous_price) * 100
        if price_change_pct > 0.5:  # Price increased by more than 0.5%
            signals.append(("BUY", 2, f"Strong upward momentum (+{price_change_pct:.2f}%)"))
        elif price_change_pct < -0.5:  # Price decreased by more than 0.5%
            signals.append(("SELL", 2, f"Strong downward momentum ({price_change_pct:.2f}%)"))
    
    # 4. Volume Confirmation Signal (Low importance - weight: 1)
    if avg_volume and current_volume > avg_volume * 1.5:  # Volume 50% above average
        volume_boost = 1.2  # Boost signal strength by 20%
        signals.append(("VOLUME", 1, f"High volume confirmation ({current_volume/avg_volume:.1f}x avg)"))
    else:
        volume_boost = 1.0
    
    # 5. EMA Trend Signal (Low importance - weight: 1)
    if previous_ema is not None:
        ema_trend = ((current_ema - previous_ema) / previous_ema) * 100
        if ema_trend > 0.1:
            signals.append(("BUY", 1, f"EMA trending up (+{ema_trend:.2f}%)"))
        elif ema_trend < -0.1:
            signals.append(("SELL", 1, f"EMA trending down ({ema_trend:.2f}%)"))
    
    # Calculate weighted signal
    buy_weight = sum(weight for signal_type_local, weight, _ in signals if signal_type_local == "BUY")
    sell_weight = sum(weight for signal_type_local, weight, _ in signals if signal_type_local == "SELL")
    total_weight = buy_weight + sell_weight
    
    # Apply volume boost
    buy_weight *= volume_boost
    sell_weight *= volume_boost
    
    # Determine final signal
    if buy_weight > sell_weight and buy_weight >= 3:
        if buy_weight >= 6:
            signal_type = "STRONG_BUY"
        else:
            signal_type = "BUY"
        signal_strength = min(buy_weight / 8, 1.0)  # Max strength at weight 8
        reason = "; ".join([reason for st, _, reason in signals if st in ["BUY", "VOLUME"]])
        
    elif sell_weight > buy_weight and sell_weight >= 3:
        if sell_weight >= 6:
            signal_type = "STRONG_SELL"
        else:
            signal_type = "SELL"
        signal_strength = min(sell_weight / 8, 1.0)
        reason = "; ".join([reason for st, _, reason in signals if st in ["SELL", "VOLUME"]])
        
    else:
        signal_type = "HOLD"
        signal_strength = 0.5
        if signals:
            reason = "Mixed signals: " + "; ".join([reason for _, _, reason in signals[:2]])
        else:
            reason = "No significant signal detected"
    
    return signal_type, signal_strength, reason


def check_database_size_and_cleanup():
    """Check database size and trigger cleanup if needed"""
    try:
        # Get current database size in MB
        db_size_mb = db.get_database_size_mb()
        
        if db_size_mb >= MAX_DB_SIZE_MB:
            logger.warning(f"Database size ({db_size_mb:.2f}MB) exceeds limit ({MAX_DB_SIZE_MB}MB). Starting cleanup...")
            
            # Perform cleanup
            deleted_records = db.cleanup_old_data(CLEANUP_RETENTION_DAYS)
            
            # Get new size after cleanup
            new_size_mb = db.get_database_size_mb()
            
            logger.info(f"Cleanup completed: {deleted_records} records deleted. "
                       f"Database size reduced from {db_size_mb:.2f}MB to {new_size_mb:.2f}MB")
            
            # Update status
            with data_lock:
                latest_data['status'] = f"Auto-cleanup: DB reduced from {db_size_mb:.1f}MB to {new_size_mb:.1f}MB"
            
            return True
        else:
            logger.debug(f"Database size ({db_size_mb:.2f}MB) is within limit ({MAX_DB_SIZE_MB}MB)")
            return False
            
    except Exception as e:
        logger.error(f"Error during database size check/cleanup: {e}")
        return False


def check_conditions(exchange, symbol, timeframe, ema_period, threshold):
    """Check trading conditions and return status"""
    try:
        # Get latest price
        latest_ohlcv = exchange.get_latest_ohlcv(symbol, timeframe)
        if not latest_ohlcv:
            return None, "Failed to get latest price data"
        
        current_price = latest_ohlcv[4]  # Close price
        current_volume = latest_ohlcv[5] if len(latest_ohlcv) > 5 else 0  # Volume
        
        # Get historical data for EMA calculation
        historical_data = exchange.get_historical_data(symbol, timeframe, ema_period + 10)
        if not historical_data or len(historical_data) < ema_period:
            return None, f"Insufficient historical data: {len(historical_data) if historical_data else 0} candles"
        
        # Extract closing prices and volumes for analysis
        closing_prices = [candle[4] for candle in historical_data]
        volumes = [candle[5] if len(candle) > 5 else 0 for candle in historical_data]
        
        # Calculate current and previous EMA
        current_ema = calculate_ema(closing_prices, ema_period)
        if current_ema is None:
            return None, "Failed to calculate EMA"
        
        # Calculate previous EMA (using data up to the previous candle)
        previous_ema = calculate_ema(closing_prices[:-1], ema_period) if len(closing_prices) > ema_period else None
        previous_price = closing_prices[-2] if len(closing_prices) >= 2 else None
        
        # Calculate average volume
        avg_volume = sum(volumes[-10:]) / len(volumes[-10:]) if volumes else 0
        
        # Calculate gap between current price and EMA (positive if above, negative if below)
        gap = current_price - current_ema
        within_threshold = abs(gap) <= threshold
        
        # Detect support and resistance levels
        sr_data = detect_support_resistance(historical_data, lookback_period=20, min_touches=2)
        
        # Generate trading signal
        signal_type, signal_strength, signal_reason = generate_trading_signal(
            current_price=current_price,
            previous_price=previous_price,
            current_ema=current_ema,
            previous_ema=previous_ema,
            current_volume=current_volume,
            avg_volume=avg_volume,
            threshold=threshold
        )
        
        # Store data in database
        db.store_price_data(
            timestamp=datetime.now(),
            exchange=exchange.__class__.__name__.replace('Exchange', ''),
            symbol=symbol,
            price=current_price,
            volume=current_volume,
            ema_value=current_ema,
            gap=gap,
            signal_triggered=(signal_type in ['BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL'])
        )
        
        # Check alerts
        triggered_alerts = db.check_alerts(current_price, current_volume, current_ema, symbol)
        
        # Store trading signal if significant signal is generated
        if signal_type in ['BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL']:
            db.store_trading_signal(
                timestamp=datetime.now(),
                exchange=exchange.__class__.__name__.replace('Exchange', ''),
                symbol=symbol,
                price=current_price,
                ema_value=current_ema,
                gap=gap,
                signal_type=signal_type,
                message=f"{signal_type} Signal (Strength: {signal_strength:.2f}): {signal_reason}"
            )
        
        return {
            'price': current_price,
            'ema': current_ema,
            'gap': gap,
            'volume': current_volume,
            'within_threshold': within_threshold,
            'signal_type': signal_type,
            'signal_strength': signal_strength,
            'signal_reason': signal_reason,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'historical_prices': closing_prices[-20:],  # Last 20 prices for chart
            'triggered_alerts': triggered_alerts,
            'support_resistance': sr_data
        }, None
        
    except Exception as e:
        return None, f"Error checking conditions: {e}"


def monitoring_thread():
    """Background thread that monitors trading conditions"""
    global latest_data, global_exchange
    
    try:
        # Initialize exchange
        print(f"DEBUG: EXCHANGE environment variable = '{os.getenv('EXCHANGE', 'NOT_SET')}'")
        exchange = ExchangeFactory.create_exchange()
        global_exchange = exchange  # Set global exchange for API routes
        exchange_name = type(exchange).__name__.replace('Exchange', '')
        
        with data_lock:
            latest_data['exchange'] = exchange_name
            latest_data['symbol'] = SYMBOL
            latest_data['threshold'] = THRESHOLD
            latest_data['ema_period'] = EMA_PERIOD
            latest_data['timeframe'] = TIMEFRAME
            latest_data['status'] = f'Connected to {exchange_name}'
        
        logger.info(f"Monitoring thread started with {exchange_name}")
        
        while True:
            result, error = check_conditions(exchange, SYMBOL, TIMEFRAME, EMA_PERIOD, THRESHOLD)
            
            with data_lock:
                if result:
                    latest_data.update(result)
                    
                    # Keep only last 50 historical data points for the chart
                    if len(latest_data['historical_data']) >= 50:
                        latest_data['historical_data'] = latest_data['historical_data'][-49:]
                    
                    # Add current data point
                    latest_data['historical_data'].append({
                        'timestamp': result['timestamp'],
                        'price': result['price'],
                        'ema': result['ema'],
                        'gap': result['gap'],
                        'within_threshold': result['within_threshold']
                    })
                    
                    if result['within_threshold']:
                        latest_data['status'] = f"🚨 SIGNAL: Price within ${THRESHOLD} of EMA!"
                        logger.info(f"TRADING SIGNAL: {SYMBOL} price ${result['price']:.4f} is within ${THRESHOLD} of EMA ${result['ema']:.4f}")
                    else:
                        gap_direction = "above" if result['gap'] > 0 else "below"
                        latest_data['status'] = f"Monitoring: Price ${abs(result['gap']):.4f} {gap_direction} EMA"
                else:
                    latest_data['status'] = f"Error: {error}"
                    logger.error(error)
            
            # Check database size and cleanup if needed (every 10 iterations to avoid frequent checks)
            if hasattr(monitoring_thread, 'iteration_count'):
                monitoring_thread.iteration_count += 1
            else:
                monitoring_thread.iteration_count = 1
                
            if monitoring_thread.iteration_count % 10 == 0:  # Check every 10 iterations
                try:
                    cleanup_performed = check_database_size_and_cleanup()
                    if cleanup_performed:
                        logger.info("Database cleanup completed successfully")
                except Exception as cleanup_error:
                    logger.error(f"Error during database cleanup check: {cleanup_error}")
            
            time.sleep(CHECK_INTERVAL)
            
    except Exception as e:
        with data_lock:
            latest_data['status'] = f"Monitoring error: {e}"
        logger.error(f"Monitoring thread error: {e}")


@app.route('/')
def index():
    """Main index page - primary breakout scanner interface"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard_page():
    """Dashboard page with trading data"""
    with data_lock:
        data = latest_data.copy()
    return render_template('dashboard.html', data=data)


@app.route('/scanner')
def scanner():
    """Scanner page - same as index"""
    return render_template('index.html')

@app.route('/index')
def index_alt():
    """Alternative index route"""
    return render_template('index.html')


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'exchange': global_exchange.get_name() if global_exchange else 'Not initialized',
        'symbol': SYMBOL,
        'database_connected': True
    })


@app.route('/settings')
def settings():
    """Settings page"""
    # Load current settings from database
    db = get_database()
    current_settings = db.get_all_settings()
    return render_template('scan_settings.html', settings=current_settings)

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """API endpoint to get all settings"""
    try:
        db = get_database()
        settings = db.get_all_settings()
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    """API endpoint to save settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        db = get_database()
        
        # Flatten the nested settings structure
        settings_to_save = {}
        
        # Handle scanning parameters
        if 'breakoutThreshold' in data:
            settings_to_save['breakout_threshold'] = float(data['breakoutThreshold'])
        if 'volumeThreshold' in data:
            settings_to_save['volume_threshold'] = float(data['volumeThreshold'])
        if 'timeframe' in data:
            settings_to_save['timeframe'] = data['timeframe']
        
        # Handle indicators
        if 'indicators' in data:
            indicators = data['indicators']
            settings_to_save['rsi_enabled'] = indicators.get('rsi', False)
            settings_to_save['macd_enabled'] = indicators.get('macd', False)
            settings_to_save['bollinger_bands_enabled'] = indicators.get('bollingerBands', False)
            settings_to_save['stochastic_enabled'] = indicators.get('stochastic', False)
        
        # Handle notifications
        if 'notifications' in data:
            notifications = data['notifications']
            settings_to_save['email_notifications'] = notifications.get('email', False)
            settings_to_save['desktop_notifications'] = notifications.get('desktop', False)
            settings_to_save['mobile_notifications'] = notifications.get('mobile', False)
        
        # Handle email address
        if 'emailAddress' in data:
            settings_to_save['notification_email'] = data['emailAddress']
        
        # Handle watchlist
        if 'watchlist' in data:
            if isinstance(data['watchlist'], list):
                settings_to_save['watchlist'] = ','.join(data['watchlist'])
            else:
                settings_to_save['watchlist'] = data['watchlist']
        
        # Save to database
        success = db.update_multiple_settings(settings_to_save)
        
        if success:
            logger.info(f"Settings saved successfully: {list(settings_to_save.keys())}")
            return jsonify({'success': True, 'message': 'Settings saved successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save settings'}), 500
            
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/coin/<symbol>')
def coin_detail(symbol):
    """Coin detail page with charts and metrics"""
    try:
        # Get current data for the symbol
        if global_exchange is None:
            exchange = ExchangeFactory.create_exchange()
        else:
            exchange = global_exchange
        
        # Clean symbol format
        symbol = symbol.upper().replace('-', '/')
        if '/' not in symbol:
            symbol = f"{symbol}/USDT"
        
        # Get current price data
        latest_ohlcv = exchange.get_latest_ohlcv(symbol, '1d')
        current_price = latest_ohlcv[4] if latest_ohlcv else 0
        
        # Get historical data for calculations
        historical_data = exchange.get_historical_data(symbol, '1d', 30)
        
        # Calculate basic metrics
        if historical_data and len(historical_data) >= 2:
            previous_price = historical_data[-2][4]
            price_change_24h = ((current_price - previous_price) / previous_price) * 100
        else:
            price_change_24h = 0
        
        # Calculate EMA if we have data
        gap = None
        signal_type = None
        signal_strength = None
        
        if historical_data and len(historical_data) >= 50:
            closing_prices = [candle[4] for candle in historical_data]
            current_ema = calculate_ema(closing_prices, 50)
            if current_ema:
                gap = current_price - current_ema
                
                # Generate basic signal
                if abs(gap) <= 5.0:  # Within threshold
                    signal_type = "BUY" if gap > 0 else "SELL"
                    signal_strength = min(80, 50 + abs(gap) * 5)
                else:
                    signal_type = "HOLD"
                    signal_strength = 40
        
        # Extract coin name from symbol
        base_currency = symbol.split('/')[0]
        coin_names = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum', 
            'SOL': 'Solana',
            'ADA': 'Cardano',
            'DOT': 'Polkadot',
            'BNB': 'Binance Coin'
        }
        coin_name = coin_names.get(base_currency, base_currency)
        
        # Mock additional data (in production, fetch from exchange or CoinGecko API)
        coin_data = {
            'symbol': base_currency,
            'coin_name': coin_name,
            'current_price': current_price,
            'price_change_24h': price_change_24h,
            'market_cap': current_price * 19000000,  # Mock calculation
            'volume_24h': current_price * 250000,    # Mock calculation
            'circulating_supply': 19000000,          # Mock data
            'ath': current_price * 1.5,              # Mock ATH
            'atl': current_price * 0.1,              # Mock ATL
            'market_cap_rank': 1 if base_currency == 'BTC' else 2,
            'gap': gap,
            'signal_type': signal_type,
            'signal_strength': signal_strength
        }
        
        return render_template('coindetail.html', **coin_data)
        
    except Exception as e:
        logger.error(f"Error getting coin details for {symbol}: {e}")
        # Return with default data
        return render_template('coindetail.html', 
                             symbol=symbol.split('/')[0] if '/' in symbol else symbol,
                             coin_name=symbol.split('/')[0] if '/' in symbol else symbol,
                             current_price=0,
                             price_change_24h=0,
                             market_cap=0,
                             volume_24h=0,
                             circulating_supply=0,
                             ath=0,
                             atl=0,
                             market_cap_rank=1,
                             gap=0,
                             signal_type="HOLD",
                             signal_strength=50)


@app.route('/alerts')
def alerts_page():
    """Alerts page"""
    return render_template('alerts.html')


def analyze_breakout_signal(symbol, volume_threshold=2.0, price_threshold=0.05):
    """
    Analyze a symbol for breakout signals based on price movement and volume
    
    Args:
        symbol: Trading symbol (e.g., 'BTC/USDT')
        volume_threshold: Volume multiplier threshold (e.g., 2.0 = 200% of average)
        price_threshold: Price change threshold (e.g., 0.05 = 5%)
    
    Returns:
        Dict with signal data or None if no signal
    """
    global global_exchange
    
    try:
        # Use global exchange or create new one if not available
        if global_exchange is None:
            global_exchange = ExchangeFactory.create_exchange()
        
        # Get current price data
        latest_ohlcv = global_exchange.get_latest_ohlcv(symbol, '1m')
        current_price = latest_ohlcv[4]  # close price
        current_volume = latest_ohlcv[5]  # volume
        
        # Get historical data for analysis (last 20 candles for volume average)
        historical_data = global_exchange.get_historical_data(symbol, '1m', 20)
        
        if len(historical_data) < 10:
            return None
        
        # Calculate metrics
        prices = [candle[4] for candle in historical_data]
        volumes = [candle[5] for candle in historical_data]
        
        # Price analysis
        previous_price = prices[-2] if len(prices) > 1 else prices[-1]
        price_change = (current_price - previous_price) / previous_price
        price_change_pct = price_change * 100
        
        # Volume analysis
        avg_volume = sum(volumes[-10:]) / 10  # Average of last 10 candles
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Simple momentum analysis
        short_ma = sum(prices[-5:]) / 5 if len(prices) >= 5 else current_price
        long_ma = sum(prices[-10:]) / 10 if len(prices) >= 10 else current_price
        momentum = (short_ma - long_ma) / long_ma if long_ma > 0 else 0
        
        # Determine signal type
        signal_type = 'NEUTRAL'
        signal_strength = 0
        signal_reason = ''
        
        # Check for breakout conditions
        strong_volume = volume_ratio >= volume_threshold
        significant_price_move = abs(price_change) >= price_threshold
        positive_momentum = momentum > 0.01  # 1% momentum threshold
        negative_momentum = momentum < -0.01
        
        if significant_price_move and strong_volume:
            if price_change > 0 and positive_momentum:
                signal_type = 'BULLISH_BREAKOUT'
                signal_strength = min(abs(price_change) * volume_ratio * 10, 100)
                signal_reason = f'Bullish breakout: {price_change_pct:.1f}% price surge with {volume_ratio:.1f}x volume'
            elif price_change < 0 and negative_momentum:
                signal_type = 'BEARISH_BREAKOUT'
                signal_strength = min(abs(price_change) * volume_ratio * 10, 100)
                signal_reason = f'Bearish breakdown: {price_change_pct:.1f}% price drop with {volume_ratio:.1f}x volume'
        elif strong_volume and not significant_price_move:
            signal_type = 'VOLUME_SURGE'
            signal_strength = min(volume_ratio * 20, 100)
            signal_reason = f'Volume surge: {volume_ratio:.1f}x average volume, preparing for move'
        elif significant_price_move and not strong_volume:
            if abs(price_change) >= price_threshold * 1.5:  # Higher threshold without volume
                signal_type = 'PRICE_BREAKOUT'
                signal_strength = min(abs(price_change) * 50, 100)
                signal_reason = f'Price breakout: {price_change_pct:.1f}% move on normal volume'
        
        # Only return signals that meet minimum criteria
        if signal_type != 'NEUTRAL' and signal_strength >= 10:
            return {
                'symbol': symbol,
                'signal_type': signal_type,
                'price': current_price,
                'price_change': price_change,
                'price_change_pct': price_change_pct,
                'volume': current_volume,
                'volume_ratio': volume_ratio,
                'signal_strength': round(signal_strength, 1),
                'signal_reason': signal_reason,
                'timestamp': datetime.now().isoformat(),
                'momentum': momentum
            }
        
        return None
        
    except Exception as e:
        print(f"Error analyzing breakout for {symbol}: {e}")
        return None


@app.route('/api/data')
def api_data():
    """API endpoint for real-time data"""
    with data_lock:
        data = latest_data.copy()
    return jsonify(data)


@app.route('/api/status')
def api_status():
    """API endpoint for system status"""
    with data_lock:
        status_data = {
            'status': latest_data['status'],
            'exchange': latest_data['exchange'],
            'symbol': latest_data['symbol'],
            'last_update': latest_data['timestamp'],
            'check_interval': CHECK_INTERVAL,
            'configuration': {
                'ema_period': latest_data['ema_period'],
                'threshold': latest_data['threshold'],
                'timeframe': latest_data['timeframe']
            }
        }
    return jsonify(status_data)


@app.route('/api/candlestick-data')
def api_candlestick_data():
    """API endpoint for candlestick OHLCV data"""
    hours = int(request.args.get('hours', 24))
    
    try:
        # Get OHLCV data from exchange
        exchange = ExchangeFactory.create_exchange()
        
        # Calculate number of 4-hour candles needed
        num_candles = max(10, (hours // 4) + 5)  # Minimum 10 candles, plus buffer
        
        # Get 4-hour candlestick data
        ohlcv_data = exchange.get_historical_data(SYMBOL, '4h', num_candles)
        
        if not ohlcv_data:
            return jsonify({
                'error': 'No candlestick data available',
                'candlesticks': [],
                'support_resistance': {
                    'support_levels': [],
                    'resistance_levels': [],
                    'current_support': None,
                    'current_resistance': None
                }
            })
        
        # Convert OHLCV data to candlestick format
        candlesticks = []
        for candle in ohlcv_data:
            timestamp, open_price, high, low, close, volume = candle
            candlesticks.append({
                't': int(timestamp),  # Timestamp
                'o': float(open_price),  # Open
                'h': float(high),     # High
                'l': float(low),      # Low
                'c': float(close)     # Close
            })
        
        # Get support and resistance for candlestick chart
        sr_data = detect_support_resistance(ohlcv_data, lookback_period=5, min_touches=1)
        
        return jsonify({
            'candlesticks': candlesticks,
            'support_resistance': sr_data,
            'symbol': SYMBOL,
            'timeframe': '4h',
            'count': len(candlesticks)
        })
        
    except Exception as e:
        logger.error(f"Error getting candlestick data: {e}")
        return jsonify({
            'error': str(e),
            'candlesticks': [],
            'support_resistance': {
                'support_levels': [],
                'resistance_levels': [],
                'current_support': None,
                'current_resistance': None
            }
        }), 500


@app.route('/api/chart-data')
def api_chart_data():
    """API endpoint for chart data from database"""
    hours = int(request.args.get('hours', 24))
    chart_data = db.get_chart_data(SYMBOL, hours)
    
    # Add support and resistance levels using 4-hour timeframe for better level detection
    if chart_data and 'prices' in chart_data and len(chart_data['prices']) > 0:
        try:
            # Get recent OHLCV data for support/resistance calculation using 4-hour timeframe
            exchange = ExchangeFactory.create_exchange()
            # Use 4-hour timeframe for support/resistance - more significant levels
            historical_data_4h = exchange.get_historical_data(SYMBOL, '4h', 200)  # Get more 4h candles for better S/R detection
            
            if historical_data_4h and len(historical_data_4h) > 50:
                # Use more appropriate parameters for 4h timeframe - less strict for better detection
                sr_data = detect_support_resistance(historical_data_4h, lookback_period=5, min_touches=1)
                chart_data['support_resistance'] = sr_data
                logger.info(f"Support/Resistance calculated from {len(historical_data_4h)} 4-hour candles: "
                           f"Support levels: {len(sr_data['support_levels'])}, "
                           f"Resistance levels: {len(sr_data['resistance_levels'])}")
            else:
                chart_data['support_resistance'] = {
                    'support_levels': [],
                    'resistance_levels': [],
                    'current_support': None,
                    'current_resistance': None
                }
                logger.warning(f"Insufficient 4-hour data for S/R calculation: {len(historical_data_4h) if historical_data_4h else 0} candles")
        except Exception as e:
            logger.error(f"Error calculating support/resistance for chart: {e}")
            chart_data['support_resistance'] = {
                'support_levels': [],
                'resistance_levels': [],
                'current_support': None,
                'current_resistance': None
            }
    
    return jsonify(chart_data)


@app.route('/api/signals')
def api_signals():
    """API endpoint for trading signals"""
    limit = int(request.args.get('limit', 20))
    signals = db.get_trading_signals(SYMBOL, limit)
    return jsonify(signals)


@app.route('/api/stats')
def api_stats():
    """API endpoint for database statistics"""
    stats = db.get_database_stats()
    return jsonify(stats)


@app.route('/api/alerts', methods=['GET'])
def api_get_alerts():
    """Get all active alerts"""
    try:
        alerts = db.get_active_alerts()
        return jsonify(alerts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts', methods=['POST'])
@app.route('/api/alerts/create', methods=['POST'])
def api_create_alert():
    """Create a new alert"""
    try:
        data = request.json
        condition_type = data.get('condition_type')
        threshold_value = data.get('threshold_value')
        notification_method = data.get('notification_method', 'in-app')
        symbol = data.get('symbol', 'SOL/USDT')
        
        if not condition_type or threshold_value is None:
            return jsonify({'error': 'Missing required fields'}), 400
        
        alert_id = db.create_alert(condition_type, threshold_value, notification_method, symbol)
        return jsonify({'success': True, 'alert_id': alert_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/active', methods=['GET'])
def api_get_active_alerts():
    """Get all active alerts"""
    try:
        symbol = request.args.get('symbol')  # Don't default to SOL/USDT
        alerts = db.get_active_alerts(symbol)
        return jsonify({'success': True, 'alerts': alerts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/history', methods=['GET'])
def api_get_alert_history():
    """Get alert history"""
    try:
        symbol = request.args.get('symbol')  # Don't default to SOL/USDT
        history = db.get_alert_history(symbol)
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/<int:alert_id>/toggle', methods=['POST'])
def api_toggle_alert(alert_id):
    """Toggle alert active status"""
    try:
        db.toggle_alert(alert_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
def api_delete_alert(alert_id):
    """Delete an alert"""
    try:
        success = db.delete_alert(alert_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Alert not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/latest-data')
def api_latest_data():
    """Get latest price data for live chart"""
    try:
        # Get latest data point from database
        latest_data = db.get_latest_data(1)
        if not latest_data:
            return jsonify({'error': 'No data available'}), 404
        
        data_point = latest_data[0]
        
        # Get current 4H support/resistance levels
        support_resistance_4h = detect_support_resistance()
        
        response_data = {
            'price': data_point[1],  # price column
            'ema': data_point[2],    # ema column
            'timestamp': data_point[4],  # timestamp column
            'support_resistance': support_resistance_4h
        }
        
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in api_latest_data: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/breakout-scanner')
def api_breakout_scanner():
    """Get breakout signals for multiple symbols"""
    try:
        # Get symbols from query parameter or use default list
        symbols_param = request.args.get('symbols', '')
        if symbols_param:
            symbols = symbols_param.split(',')
        else:
            # Default symbols to monitor
            symbols = ['SOL/USDT', 'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT']
        
        # Get thresholds from query parameters
        volume_threshold = float(request.args.get('volume_threshold', 2.0))
        price_threshold = float(request.args.get('price_threshold', 0.05))
        
        signals = []
        
        for symbol in symbols:
            try:
                # Get current market data
                signal_data = analyze_breakout_signal(symbol, volume_threshold, price_threshold)
                if signal_data:
                    signals.append(signal_data)
            except Exception as symbol_error:
                print(f"Error analyzing {symbol}: {symbol_error}")
                continue
        
        return jsonify({
            'success': True,
            'signals': signals,
            'scan_time': datetime.now().isoformat(),
            'symbols_scanned': len(symbols),
            'breakouts_detected': len([s for s in signals if s.get('signal_type') != 'NEUTRAL'])
        })
        
    except Exception as e:
        print(f"Error in breakout scanner: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/breakout-symbols', methods=['GET'])
def api_get_breakout_symbols():
    """Get list of symbols being monitored for breakouts"""
    try:
        # For now, return predefined list - could be stored in database later
        default_symbols = ['SOL/USDT', 'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT']
        
        return jsonify({
            'success': True,
            'symbols': default_symbols
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/breakout-symbols', methods=['POST'])
def api_add_breakout_symbol():
    """Add a symbol to breakout monitoring"""
    try:
        data = request.json
        symbol = data.get('symbol', '').upper()
        
        if not symbol:
            return jsonify({'error': 'Symbol is required'}), 400
        
        # Validate symbol format
        if '/' not in symbol:
            return jsonify({'error': 'Invalid symbol format. Use BASE/QUOTE (e.g., BTC/USDT)'}), 400
        
        # For now, just return success - in production, store in database
        return jsonify({
            'success': True,
            'message': f'Symbol {symbol} added to watchlist',
            'symbol': symbol
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cleanup', methods=['POST'])
def api_manual_cleanup():
    """Manually trigger database cleanup"""
    try:
        data = request.json or {}
        retention_days = data.get('retention_days', CLEANUP_RETENTION_DAYS)
        
        # Get current size
        current_size_mb = db.get_database_size_mb()
        
        # Perform cleanup
        deleted_records = db.cleanup_old_data(retention_days)
        
        # Get new size
        new_size_mb = db.get_database_size_mb()
        
        return jsonify({
            'success': True,
            'deleted_records': deleted_records,
            'size_before_mb': current_size_mb,
            'size_after_mb': new_size_mb,
            'space_freed_mb': round(current_size_mb - new_size_mb, 2),
            'retention_days': retention_days
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Check if required dependencies are available
    try:
        import ccxt
        print("✅ CCXT library found")
    except ImportError:
        print("❌ CCXT library not found. Please install: pip install ccxt")
        exit(1)
    
    try:
        # Test database connection
        db.get_database_stats()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"⚠️  Database warning: {e}")
    
    # Start monitoring thread
    monitor_thread = Thread(target=monitoring_thread, daemon=True)
    monitor_thread.start()
    print("✅ Monitoring thread started")
    
    # Start Flask app
    print("🌐 Starting SolSignals Web Dashboard...")
    print(f"📊 Monitoring {SYMBOL} on {os.getenv('EXCHANGE', 'default')} exchange")
    print(f"⏱️  Check interval: {CHECK_INTERVAL//60} minute(s)")
    print(f"🎯 EMA period: {EMA_PERIOD}, Threshold: ${THRESHOLD}")
    print("🚀 Main page (Index): http://localhost:5000")
    print("📊 Dashboard: http://localhost:5000/dashboard")
    print("🔍 Scanner: http://localhost:5000/scanner")
    print("💚 Health check: http://localhost:5000/health")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except Exception as e:
        print(f"❌ Failed to start Flask app: {e}")
        print("💡 Make sure port 5000 is not in use by another application")