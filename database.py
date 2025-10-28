"""
SQLite database module for storing trading data and signals.
"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os

logger = logging.getLogger(__name__)

class TradingDatabase:
    """SQLite database handler for trading data storage."""
    
    def __init__(self, db_path: str = "trading_data.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create price_data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS price_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        exchange TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        price REAL NOT NULL,
                        volume REAL,
                        ema_value REAL,
                        gap REAL,
                        signal_triggered BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create trading_signals table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trading_signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        exchange TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        price REAL NOT NULL,
                        ema_value REAL NOT NULL,
                        gap REAL NOT NULL,
                        signal_type TEXT NOT NULL,
                        message TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create alerts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        condition_type TEXT NOT NULL,
                        threshold_value REAL NOT NULL,
                        notification_method TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        symbol TEXT NOT NULL DEFAULT 'SOL/USDT',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_triggered DATETIME
                    )
                ''')
                
                # Create settings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key TEXT UNIQUE NOT NULL,
                        setting_value TEXT NOT NULL,
                        setting_type TEXT NOT NULL DEFAULT 'string',
                        category TEXT NOT NULL DEFAULT 'general',
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create coin_data table for storing all coins data
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS coin_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        futures_symbol TEXT NOT NULL,
                        current_price REAL NOT NULL,
                        ema_50 REAL NOT NULL,
                        price_diff REAL NOT NULL,
                        diff_percentage REAL NOT NULL,
                        volume_24h REAL NOT NULL,
                        trend TEXT NOT NULL,
                        last_updated DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol) ON CONFLICT REPLACE
                    )
                ''')
                
                # Create index for faster queries
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_timestamp ON price_data(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON trading_signals(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(setting_key)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_coin_data_symbol ON coin_data(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_coin_data_updated ON coin_data(last_updated)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_coin_data_diff_pct ON coin_data(diff_percentage)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_coin_data_volume ON coin_data(volume_24h)')
                
                # Insert default settings if they don't exist
                default_settings = [
                    ('breakout_threshold', '5', 'float', 'scanning'),
                    ('volume_threshold', '150', 'float', 'scanning'),
                    ('timeframe', '4h', 'string', 'scanning'),
                    ('rsi_enabled', 'true', 'boolean', 'indicators'),
                    ('macd_enabled', 'true', 'boolean', 'indicators'),
                    ('bollinger_bands_enabled', 'false', 'boolean', 'indicators'),
                    ('stochastic_enabled', 'false', 'boolean', 'indicators'),
                    ('email_notifications', 'true', 'boolean', 'notifications'),
                    ('desktop_notifications', 'false', 'boolean', 'notifications'),
                    ('mobile_notifications', 'true', 'boolean', 'notifications'),
                    ('notification_email', '', 'string', 'notifications'),
                    ('watchlist', 'BTC,ETH,ADA,SOL', 'string', 'watchlist')
                ]
                
                for key, value, type_, category in default_settings:
                    cursor.execute('''
                        INSERT OR IGNORE INTO settings 
                        (setting_key, setting_value, setting_type, category)
                        VALUES (?, ?, ?, ?)
                    ''', (key, value, type_, category))
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def store_price_data(self, timestamp: datetime, exchange: str, symbol: str, 
                        price: float, volume: float = None, ema_value: float = None, 
                        gap: float = None, signal_triggered: bool = False):
        """Store price data point in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO price_data 
                    (timestamp, exchange, symbol, price, volume, ema_value, gap, signal_triggered)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, exchange, symbol, price, volume, ema_value, gap, signal_triggered))
                conn.commit()
                
        except sqlite3.Error as e:
            logger.error(f"Error storing price data: {e}")
    
    def store_trading_signal(self, timestamp: datetime, exchange: str, symbol: str,
                           price: float, ema_value: float, gap: float, 
                           signal_type: str = "BUY", message: str = None):
        """Store trading signal in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trading_signals 
                    (timestamp, exchange, symbol, price, ema_value, gap, signal_type, message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, exchange, symbol, price, ema_value, gap, signal_type, message))
                conn.commit()
                logger.info(f"Trading signal stored: {signal_type} at {price}")
                
        except sqlite3.Error as e:
            logger.error(f"Error storing trading signal: {e}")
    
    def get_recent_price_data(self, symbol: str = "SOL/USDT", limit: int = 100) -> List[Dict]:
        """Get recent price data for charts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, price, ema_value, gap, signal_triggered
                    FROM price_data 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (symbol, limit))
                
                rows = cursor.fetchall()
                return [
                    {
                        'timestamp': row[0],
                        'price': row[1],
                        'ema_value': row[2],
                        'gap': row[3],
                        'signal_triggered': bool(row[4])
                    }
                    for row in rows
                ]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving price data: {e}")
            return []
    
    def get_trading_signals(self, symbol: str = "SOL/USDT", limit: int = 50) -> List[Dict]:
        """Get recent trading signals."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, price, ema_value, gap, signal_type, message
                    FROM trading_signals 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (symbol, limit))
                
                rows = cursor.fetchall()
                return [
                    {
                        'timestamp': row[0],
                        'price': row[1],
                        'ema_value': row[2],
                        'gap': row[3],
                        'signal_type': row[4],
                        'message': row[5]
                    }
                    for row in rows
                ]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving trading signals: {e}")
            return []
    
    def get_chart_data(self, symbol: str = "SOL/USDT", hours: int = 24) -> Dict:
        """Get formatted chart data for the last N hours."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, price, ema_value, gap, volume
                    FROM price_data 
                    WHERE symbol = ? 
                    AND datetime(timestamp) >= datetime('now', '-{} hours')
                    ORDER BY timestamp ASC
                '''.format(hours), (symbol,))
                
                rows = cursor.fetchall()
                
                if not rows:
                    return {'labels': [], 'prices': [], 'ema_values': [], 'gaps': [], 'volumes': []}
                
                labels = []
                prices = []
                ema_values = []
                gaps = []
                volumes = []
                
                for row in rows:
                    # Format timestamp for chart labels
                    dt = datetime.fromisoformat(row[0])
                    labels.append(dt.strftime('%H:%M'))
                    prices.append(row[1])
                    ema_values.append(row[2] if row[2] is not None else 0)
                    gaps.append(row[3] if row[3] is not None else 0)
                    volumes.append(row[4] if row[4] is not None else 0)
                
                return {
                    'labels': labels,
                    'prices': prices,
                    'ema_values': ema_values,
                    'gaps': gaps,
                    'volumes': volumes
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving chart data: {e}")
            return {'labels': [], 'prices': [], 'ema_values': [], 'gaps': [], 'volumes': []}
    
    def get_database_stats(self) -> Dict:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count records
                cursor.execute('SELECT COUNT(*) FROM price_data')
                price_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM trading_signals')
                signals_count = cursor.fetchone()[0]
                
                # Get latest data point
                cursor.execute('SELECT MAX(timestamp) FROM price_data')
                latest_timestamp = cursor.fetchone()[0]
                
                # Get database file size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    'price_records': price_count,
                    'signal_records': signals_count,
                    'latest_timestamp': latest_timestamp,
                    'database_size_kb': round(db_size / 1024, 2)
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def get_database_size_mb(self) -> float:
        """Get database file size in MB."""
        try:
            if os.path.exists(self.db_path):
                size_bytes = os.path.getsize(self.db_path)
                size_mb = size_bytes / (1024 * 1024)  # Convert to MB
                return round(size_mb, 2)
            return 0.0
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return 0.0
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up data older than specified days."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old price data
                cursor.execute('''
                    DELETE FROM price_data 
                    WHERE datetime(timestamp) < datetime('now', '-{} days')
                '''.format(days))
                
                deleted_price = cursor.rowcount
                
                # Delete old signals
                cursor.execute('''
                    DELETE FROM trading_signals 
                    WHERE datetime(timestamp) < datetime('now', '-{} days')
                '''.format(days))
                
                deleted_signals = cursor.rowcount
                
                # Delete old alerts that have been triggered (keep active ones)
                cursor.execute('''
                    DELETE FROM alerts 
                    WHERE triggered_at IS NOT NULL 
                    AND datetime(triggered_at) < datetime('now', '-{} days')
                '''.format(days))
                
                deleted_alerts = cursor.rowcount
                conn.commit()
                
                total_deleted = deleted_price + deleted_signals + deleted_alerts
                logger.info(f"Cleaned up {deleted_price} price records, {deleted_signals} signal records, "
                           f"and {deleted_alerts} old alerts (total: {total_deleted})")
                
                # Vacuum to reclaim space
                cursor.execute('VACUUM')
                logger.info("Database vacuum completed")
                
                return total_deleted
                
        except sqlite3.Error as e:
            logger.error(f"Error cleaning up old data: {e}")
            return 0
    
    def create_alert(self, condition_type: str, threshold_value: float, 
                    notification_method: str, symbol: str = "SOL/USDT") -> int:
        """Create a new alert."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alerts 
                    (condition_type, threshold_value, notification_method, symbol)
                    VALUES (?, ?, ?, ?)
                ''', (condition_type, threshold_value, notification_method, symbol))
                conn.commit()
                alert_id = cursor.lastrowid
                logger.info(f"Alert created: {condition_type} at {threshold_value}")
                return alert_id
                
        except sqlite3.Error as e:
            logger.error(f"Error creating alert: {e}")
            return 0
    
    def get_active_alerts(self, symbol: str = None) -> List[Dict]:
        """Get all active alerts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if symbol:
                    # Filter by specific symbol
                    cursor.execute('''
                        SELECT id, condition_type, threshold_value, notification_method, 
                               created_at, last_triggered, is_active, symbol
                        FROM alerts 
                        WHERE is_active = TRUE AND symbol = ?
                        ORDER BY created_at DESC
                    ''', (symbol,))
                else:
                    # Get all active alerts regardless of symbol
                    cursor.execute('''
                        SELECT id, condition_type, threshold_value, notification_method, 
                               created_at, last_triggered, is_active, symbol
                        FROM alerts 
                        WHERE is_active = TRUE
                        ORDER BY created_at DESC
                    ''')
                
                rows = cursor.fetchall()
                return [
                    {
                        'id': row[0],
                        'condition_type': row[1],
                        'threshold_value': row[2],
                        'notification_method': row[3],
                        'created_at': row[4],
                        'last_triggered': row[5],
                        'is_active': row[6],
                        'symbol': row[7]
                    }
                    for row in rows
                ]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving alerts: {e}")
            return []
    
    def update_alert_status(self, alert_id: int, is_active: bool) -> bool:
        """Update alert active status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE alerts 
                    SET is_active = ?
                    WHERE id = ?
                ''', (is_active, alert_id))
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Error updating alert status: {e}")
            return False
    
    def toggle_alert(self, alert_id: int) -> bool:
        """Toggle alert active status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE alerts 
                    SET is_active = NOT is_active
                    WHERE id = ?
                ''', (alert_id,))
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Error toggling alert status: {e}")
            return False
    
    def trigger_alert(self, alert_id: int) -> bool:
        """Mark alert as triggered."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE alerts 
                    SET last_triggered = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (alert_id,))
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Error triggering alert: {e}")
            return False
    
    def delete_alert(self, alert_id: int) -> bool:
        """Delete an alert."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM alerts WHERE id = ?', (alert_id,))
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Error deleting alert: {e}")
            return False
    
    def check_alerts(self, current_price: float, current_volume: float, 
                    ema_value: float, symbol: str = "SOL/USDT") -> List[Dict]:
        """Check if any alerts should be triggered."""
        triggered_alerts = []
        alerts = self.get_active_alerts(symbol)
        
        for alert in alerts:
            should_trigger = False
            condition = alert['condition_type']
            threshold = alert['threshold_value']
            
            if condition == "Price crosses EMA":
                should_trigger = abs(current_price - ema_value) <= threshold
            elif condition == "Price above EMA":
                should_trigger = current_price > ema_value + threshold
            elif condition == "Price below EMA":
                should_trigger = current_price < ema_value - threshold
            elif condition == "Volume spike":
                # Check if volume is X% higher than threshold
                should_trigger = current_volume > (threshold / 100)
            
            if should_trigger:
                self.trigger_alert(alert['id'])
                triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def get_alert_history(self, symbol: str = None) -> List[Dict]:
        """Get alert history (triggered alerts)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if symbol:
                    cursor.execute('''
                        SELECT id, condition_type, threshold_value, notification_method, 
                               symbol, last_triggered, created_at
                        FROM alerts 
                        WHERE symbol = ? AND last_triggered IS NOT NULL
                        ORDER BY last_triggered DESC
                        LIMIT 50
                    ''', (symbol,))
                else:
                    cursor.execute('''
                        SELECT id, condition_type, threshold_value, notification_method, 
                               symbol, last_triggered, created_at
                        FROM alerts 
                        WHERE last_triggered IS NOT NULL
                        ORDER BY last_triggered DESC
                        LIMIT 50
                    ''')
                
                columns = [description[0] for description in cursor.description]
                alerts = []
                for row in cursor.fetchall():
                    alert_dict = dict(zip(columns, row))
                    alerts.append(alert_dict)
                
                return alerts
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving alert history: {e}")
            return []
    
    def get_setting(self, key: str, default_value: str = None) -> str:
        """Get a setting value by key."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT setting_value FROM settings WHERE setting_key = ?', (key,))
                result = cursor.fetchone()
                return result[0] if result else default_value
        except sqlite3.Error as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default_value
    
    def set_setting(self, key: str, value: str, setting_type: str = 'string', category: str = 'general') -> bool:
        """Set a setting value by key."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO settings 
                    (setting_key, setting_value, setting_type, category, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (key, value, setting_type, category))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error setting {key}: {e}")
            return False
    
    def get_settings_by_category(self, category: str) -> Dict[str, str]:
        """Get all settings for a specific category."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT setting_key, setting_value, setting_type 
                    FROM settings 
                    WHERE category = ?
                ''', (category,))
                results = cursor.fetchall()
                
                settings = {}
                for key, value, setting_type in results:
                    # Convert based on type
                    if setting_type == 'boolean':
                        settings[key] = value.lower() == 'true'
                    elif setting_type == 'float':
                        settings[key] = float(value)
                    elif setting_type == 'int':
                        settings[key] = int(value)
                    else:
                        settings[key] = value
                
                return settings
        except sqlite3.Error as e:
            logger.error(f"Error getting settings for category {category}: {e}")
            return {}
    
    def get_all_settings(self) -> Dict[str, Dict]:
        """Get all settings grouped by category."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT setting_key, setting_value, setting_type, category 
                    FROM settings 
                    ORDER BY category, setting_key
                ''')
                results = cursor.fetchall()
                
                settings = {}
                for key, value, setting_type, category in results:
                    if category not in settings:
                        settings[category] = {}
                    
                    # Convert based on type
                    if setting_type == 'boolean':
                        settings[category][key] = value.lower() == 'true'
                    elif setting_type == 'float':
                        settings[category][key] = float(value)
                    elif setting_type == 'int':
                        settings[category][key] = int(value)
                    else:
                        settings[category][key] = value
                
                return settings
        except sqlite3.Error as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    def update_multiple_settings(self, settings_dict: Dict[str, any]) -> bool:
        """Update multiple settings at once."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Define category mapping for different settings
                category_map = {
                    'breakout_threshold': 'scanning',
                    'volume_threshold': 'scanning',
                    'timeframe': 'scanning',
                    'rsi_enabled': 'indicators',
                    'macd_enabled': 'indicators',
                    'bollinger_bands_enabled': 'indicators',
                    'stochastic_enabled': 'indicators',
                    'email_notifications': 'notifications',
                    'desktop_notifications': 'notifications',
                    'mobile_notifications': 'notifications',
                    'notification_email': 'notifications',
                    'watchlist': 'watchlist'
                }
                
                for key, value in settings_dict.items():
                    # Determine type
                    if isinstance(value, bool):
                        setting_type = 'boolean'
                        setting_value = str(value).lower()
                    elif isinstance(value, float):
                        setting_type = 'float'
                        setting_value = str(value)
                    elif isinstance(value, int):
                        setting_type = 'int'
                        setting_value = str(value)
                    else:
                        setting_type = 'string'
                        setting_value = str(value)
                    
                    # Get category for this setting
                    category = category_map.get(key, 'general')
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO settings 
                        (setting_key, setting_value, setting_type, category, updated_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (key, setting_value, setting_type, category))
                
                conn.commit()
                logger.info(f"Updated {len(settings_dict)} settings")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating multiple settings: {e}")
            return False
    
    def store_coin_data(self, coin_data: dict):
        """Store or update coin data in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO coin_data 
                    (symbol, futures_symbol, current_price, ema_50, price_diff, 
                     diff_percentage, volume_24h, trend, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    coin_data['symbol'],
                    coin_data['futures_symbol'],
                    coin_data['current_price'],
                    coin_data['ema_50'],
                    coin_data['price_diff'],
                    coin_data['diff_percentage'],
                    coin_data['volume_24h'],
                    coin_data['trend'],
                    datetime.now()
                ))
                conn.commit()
                
        except sqlite3.Error as e:
            logger.error(f"Error storing coin data for {coin_data.get('symbol', 'unknown')}: {e}")
    
    def store_multiple_coin_data(self, coins_data: list):
        """Store multiple coin data records efficiently."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Prepare data for batch insert
                data_tuples = []
                current_time = datetime.now()
                
                for coin_data in coins_data:
                    data_tuples.append((
                        coin_data['symbol'],
                        coin_data['futures_symbol'],
                        coin_data['current_price'],
                        coin_data['ema_50'],
                        coin_data['price_diff'],
                        coin_data['diff_percentage'],
                        coin_data['volume_24h'],
                        coin_data['trend'],
                        current_time
                    ))
                
                # Batch insert
                cursor.executemany('''
                    INSERT OR REPLACE INTO coin_data 
                    (symbol, futures_symbol, current_price, ema_50, price_diff, 
                     diff_percentage, volume_24h, trend, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', data_tuples)
                
                conn.commit()
                logger.info(f"Stored {len(coins_data)} coin data records")
                
        except sqlite3.Error as e:
            logger.error(f"Error storing multiple coin data: {e}")
    
    def get_all_coin_data(self, order_by: str = 'symbol', order_direction: str = 'ASC', 
                         limit: int = None, offset: int = None):
        """Get all coin data from database with optional sorting and pagination."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query with optional ordering and pagination
                valid_columns = ['symbol', 'current_price', 'ema_50', 'price_diff', 
                               'diff_percentage', 'volume_24h', 'last_updated']
                
                if order_by not in valid_columns:
                    order_by = 'symbol'
                
                if order_direction.upper() not in ['ASC', 'DESC']:
                    order_direction = 'ASC'
                
                query = f'''
                    SELECT symbol, futures_symbol, current_price, ema_50, price_diff,
                           diff_percentage, volume_24h, trend, last_updated
                    FROM coin_data 
                    ORDER BY {order_by} {order_direction}
                '''
                
                if limit:
                    query += f' LIMIT {limit}'
                    if offset:
                        query += f' OFFSET {offset}'
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                columns = ['symbol', 'futures_symbol', 'current_price', 'ema_50', 'price_diff',
                          'diff_percentage', 'volume_24h', 'trend', 'last_updated']
                
                coin_data_list = []
                for row in rows:
                    coin_dict = dict(zip(columns, row))
                    # Format timestamp
                    if coin_dict['last_updated']:
                        coin_dict['timestamp'] = coin_dict['last_updated']
                    coin_data_list.append(coin_dict)
                
                return coin_data_list
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving coin data: {e}")
            return []
    
    def get_coin_data_stats(self):
        """Get statistics about coin data in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM coin_data')
                total_coins = cursor.fetchone()[0]
                
                cursor.execute('SELECT MAX(last_updated) FROM coin_data')
                last_update = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM coin_data 
                    WHERE diff_percentage > 0
                ''')
                bullish_count = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM coin_data 
                    WHERE diff_percentage < 0
                ''')
                bearish_count = cursor.fetchone()[0]
                
                return {
                    'total_coins': total_coins,
                    'last_update': last_update,
                    'bullish_count': bullish_count,
                    'bearish_count': bearish_count,
                    'neutral_count': total_coins - bullish_count - bearish_count
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error getting coin data stats: {e}")
            return {
                'total_coins': 0,
                'last_update': None,
                'bullish_count': 0,
                'bearish_count': 0,
                'neutral_count': 0
            }
    
    def search_coin_data(self, search_term: str, limit: int = 50):
        """Search coin data by symbol."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT symbol, futures_symbol, current_price, ema_50, price_diff,
                           diff_percentage, volume_24h, trend, last_updated
                    FROM coin_data 
                    WHERE symbol LIKE ? OR futures_symbol LIKE ?
                    ORDER BY symbol
                    LIMIT ?
                ''', (f'%{search_term}%', f'%{search_term}%', limit))
                
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                columns = ['symbol', 'futures_symbol', 'current_price', 'ema_50', 'price_diff',
                          'diff_percentage', 'volume_24h', 'trend', 'last_updated']
                
                coin_data_list = []
                for row in rows:
                    coin_dict = dict(zip(columns, row))
                    if coin_dict['last_updated']:
                        coin_dict['timestamp'] = coin_dict['last_updated']
                    coin_data_list.append(coin_dict)
                
                return coin_data_list
                
        except sqlite3.Error as e:
            logger.error(f"Error searching coin data: {e}")
            return []

# Singleton instance
_db_instance = None

def get_database() -> TradingDatabase:
    """Get singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = TradingDatabase()
    return _db_instance