"""
Database models and connection for Wallet Balance History
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class WalletBalanceHistory(Base):
    """Model for storing wallet balance history over time"""
    __tablename__ = 'wallet_balance_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    currency = Column(String(10), nullable=False)  # e.g., 'USDT', 'BTC', etc.
    available_balance = Column(Float, nullable=False, default=0.0)
    locked_balance = Column(Float, nullable=False, default=0.0)
    total_balance = Column(Float, nullable=False, default=0.0)
    cross_user_margin = Column(Float, nullable=True, default=0.0)
    cross_order_margin = Column(Float, nullable=True, default=0.0)
    
    # Store full wallet data as JSON for reference
    raw_data = Column(Text, nullable=True)
    
    # Add indexes for better query performance
    __table_args__ = (
        Index('idx_currency_timestamp', 'currency', 'timestamp'),
        Index('idx_timestamp', 'timestamp'),
        Index('idx_currency', 'currency'),
    )
    
    def __repr__(self):
        return f"<WalletBalance(currency='{self.currency}', available={self.available_balance}, timestamp='{self.timestamp}')>"

class WalletSummaryHistory(Base):
    """Model for storing wallet summary snapshots over time"""
    __tablename__ = 'wallet_summary_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    total_balance_usd = Column(Float, nullable=False, default=0.0)
    total_available_usd = Column(Float, nullable=False, default=0.0)
    total_locked_usd = Column(Float, nullable=False, default=0.0)
    currencies_count = Column(Integer, nullable=False, default=0)
    
    # Store summary metadata
    summary_data = Column(Text, nullable=True)
    
    # Add indexes
    __table_args__ = (
        Index('idx_summary_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<WalletSummary(total_usd={self.total_balance_usd}, timestamp='{self.timestamp}')>"

class DatabaseManager:
    """Database manager for wallet balance tracking"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL not provided and not found in environment variables")
        
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            logger.info(f"🔗 Connecting to database...")
            self.engine = create_engine(
                self.database_url,
                echo=False,  # Set to True for SQL query logging
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=3600    # Recycle connections after 1 hour
            )
            
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database connection established and tables created")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def store_wallet_balance(self, wallet_data: Dict[str, Any], summary_data: Dict[str, Any] = None) -> bool:
        """
        Store wallet balance data to database
        
        Args:
            wallet_data: Dictionary containing wallet information from API
            summary_data: Optional summary data
            
        Returns:
            bool: True if successful, False otherwise
        """
        session = self.get_session()
        try:
            current_time = datetime.now(timezone.utc)
            
            # Extract wallets from the data structure
            wallets = []
            if isinstance(wallet_data, dict):
                if 'wallets' in wallet_data:
                    wallets = wallet_data['wallets']
                elif isinstance(wallet_data.get('data'), list):
                    wallets = wallet_data['data']
                else:
                    # Assume it's a single wallet entry
                    wallets = [wallet_data]
            elif isinstance(wallet_data, list):
                wallets = wallet_data
            
            # Store individual wallet balances
            for wallet in wallets:
                if not isinstance(wallet, dict):
                    continue
                    
                currency = wallet.get('currency_short_name', 'UNKNOWN')
                available = float(wallet.get('balance', 0))  # API balance is available amount
                locked = float(wallet.get('locked_balance', 0))
                total = available + locked  # Calculate total
                cross_margin = float(wallet.get('cross_user_margin', 0))
                cross_order_margin = float(wallet.get('cross_order_margin', 0))
                
                # Skip zero balances to keep database clean
                if total == 0 and locked == 0:
                    continue
                
                wallet_record = WalletBalanceHistory(
                    timestamp=current_time,
                    currency=currency,
                    available_balance=available,
                    locked_balance=locked,
                    total_balance=total,
                    cross_user_margin=cross_margin,
                    cross_order_margin=cross_order_margin,
                    raw_data=json.dumps(wallet, default=str)
                )
                
                session.add(wallet_record)
            
            # Store wallet summary if provided
            if summary_data:
                summary_record = WalletSummaryHistory(
                    timestamp=current_time,
                    total_balance_usd=float(summary_data.get('total_balance', 0)),
                    total_available_usd=float(summary_data.get('available_balance', 0)),
                    total_locked_usd=float(summary_data.get('total_locked', 0)),
                    currencies_count=len(wallets),
                    summary_data=json.dumps(summary_data, default=str)
                )
                session.add(summary_record)
            
            session.commit()
            logger.info(f"💾 Stored wallet data for {len(wallets)} currencies at {current_time}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error storing wallet data: {e}")
            return False
        finally:
            session.close()
    
    def get_wallet_history(self, currency: str = None, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get wallet balance history
        
        Args:
            currency: Optional currency filter (e.g., 'USDT')
            hours: Number of hours of history to retrieve
            
        Returns:
            List of wallet balance records
        """
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            query = session.query(WalletBalanceHistory).filter(
                WalletBalanceHistory.timestamp >= cutoff_time
            )
            
            if currency:
                query = query.filter(WalletBalanceHistory.currency == currency)
            
            records = query.order_by(WalletBalanceHistory.timestamp.desc()).all()
            
            result = []
            for record in records:
                result.append({
                    'id': record.id,
                    'timestamp': record.timestamp.isoformat(),
                    'currency': record.currency,
                    'available_balance': record.available_balance,
                    'locked_balance': record.locked_balance,
                    'total_balance': record.total_balance,
                    'cross_user_margin': record.cross_user_margin,
                    'cross_order_margin': record.cross_order_margin
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error retrieving wallet history: {e}")
            return []
        finally:
            session.close()
    
    def get_daily_wallet_history(self, currency: str = None, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get wallet balance history aggregated by day (one data point per day)
        
        Args:
            currency: Optional currency filter (e.g., 'USDT')
            days: Number of days of history to retrieve
            
        Returns:
            List of daily wallet balance records (latest balance per day)
        """
        session = self.get_session()
        try:
            from datetime import timedelta
            from sqlalchemy import func, case
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Create a subquery to get the latest record for each currency and day
            # We use date_trunc to group by day
            subquery = session.query(
                WalletBalanceHistory.currency,
                func.date_trunc('day', WalletBalanceHistory.timestamp).label('day'),
                func.max(WalletBalanceHistory.timestamp).label('max_timestamp')
            ).filter(
                WalletBalanceHistory.timestamp >= cutoff_time
            ).group_by(
                WalletBalanceHistory.currency,
                func.date_trunc('day', WalletBalanceHistory.timestamp)
            ).subquery()
            
            # Join to get the complete records for the latest timestamp of each day
            query = session.query(WalletBalanceHistory).join(
                subquery,
                (WalletBalanceHistory.currency == subquery.c.currency) &
                (WalletBalanceHistory.timestamp == subquery.c.max_timestamp)
            )
            
            if currency:
                query = query.filter(WalletBalanceHistory.currency == currency)
            
            records = query.order_by(WalletBalanceHistory.timestamp.desc()).all()
            
            result = []
            for record in records:
                result.append({
                    'id': record.id,
                    'timestamp': record.timestamp.isoformat(),
                    'currency': record.currency,
                    'available_balance': record.available_balance,
                    'locked_balance': record.locked_balance,
                    'total_balance': record.total_balance,
                    'cross_user_margin': record.cross_user_margin,
                    'cross_order_margin': record.cross_order_margin
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error retrieving daily wallet history: {e}")
            return []
        finally:
            session.close()
    
    def get_balance_summary_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get wallet summary history
        
        Args:
            hours: Number of hours of history to retrieve
            
        Returns:
            List of wallet summary records
        """
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            records = session.query(WalletSummaryHistory).filter(
                WalletSummaryHistory.timestamp >= cutoff_time
            ).order_by(WalletSummaryHistory.timestamp.desc()).all()
            
            result = []
            for record in records:
                result.append({
                    'id': record.id,
                    'timestamp': record.timestamp.isoformat(),
                    'total_balance_usd': record.total_balance_usd,
                    'total_available_usd': record.total_available_usd,
                    'total_locked_usd': record.total_locked_usd,
                    'currencies_count': record.currencies_count
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error retrieving summary history: {e}")
            return []
        finally:
            session.close()
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Clean up old wallet data beyond specified days
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of records deleted
        """
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Delete old wallet balance records
            deleted_wallets = session.query(WalletBalanceHistory).filter(
                WalletBalanceHistory.timestamp < cutoff_time
            ).delete()
            
            # Delete old summary records
            deleted_summaries = session.query(WalletSummaryHistory).filter(
                WalletSummaryHistory.timestamp < cutoff_time
            ).delete()
            
            session.commit()
            
            total_deleted = deleted_wallets + deleted_summaries
            logger.info(f"🧹 Cleaned up {total_deleted} old records (older than {days} days)")
            return total_deleted
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error during cleanup: {e}")
            return 0
        finally:
            session.close()
    
    def get_latest_balances(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the latest balance for each currency
        
        Returns:
            Dictionary with currency as key and latest balance data as value
        """
        session = self.get_session()
        try:
            from sqlalchemy import func
            
            # Subquery to get the latest timestamp for each currency
            subquery = session.query(
                WalletBalanceHistory.currency,
                func.max(WalletBalanceHistory.timestamp).label('max_timestamp')
            ).group_by(WalletBalanceHistory.currency).subquery()
            
            # Join to get the complete records for latest timestamps
            records = session.query(WalletBalanceHistory).join(
                subquery,
                (WalletBalanceHistory.currency == subquery.c.currency) &
                (WalletBalanceHistory.timestamp == subquery.c.max_timestamp)
            ).all()
            
            result = {}
            for record in records:
                result[record.currency] = {
                    'available_balance': record.available_balance,
                    'locked_balance': record.locked_balance,
                    'total_balance': record.total_balance,
                    'timestamp': record.timestamp.isoformat(),
                    'cross_user_margin': record.cross_user_margin,
                    'cross_order_margin': record.cross_order_margin
                }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error retrieving latest balances: {e}")
            return {}
        finally:
            session.close()

# Global database manager instance
db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get or create global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

def store_wallet_data(wallet_data: Dict[str, Any], summary_data: Dict[str, Any] = None) -> bool:
    """Convenience function to store wallet data"""
    try:
        manager = get_db_manager()
        return manager.store_wallet_balance(wallet_data, summary_data)
    except Exception as e:
        logger.error(f"❌ Failed to store wallet data: {e}")
        return False

if __name__ == "__main__":
    # Test the database connection and models
    print("🧪 Testing database connection...")
    
    try:
        manager = DatabaseManager()
        print("✅ Database connection successful!")
        
        # Test storing sample data
        sample_wallet = {
            "wallets": [
                {
                    "currency_short_name": "USDT",
                    "balance": 100.50,
                    "locked_balance": 10.25,
                    "cross_user_margin": 5.0,
                    "cross_order_margin": 2.0
                },
                {
                    "currency_short_name": "BTC",
                    "balance": 0.005,
                    "locked_balance": 0.001,
                    "cross_user_margin": 0.0,
                    "cross_order_margin": 0.0
                }
            ]
        }
        
        sample_summary = {
            "total_balance": 110.75,
            "available_balance": 100.505,
            "total_locked": 10.251
        }
        
        success = manager.store_wallet_balance(sample_wallet, sample_summary)
        if success:
            print("✅ Sample data stored successfully!")
        else:
            print("❌ Failed to store sample data")
            
        # Test retrieving data
        history = manager.get_wallet_history(currency="USDT", hours=1)
        print(f"📊 Retrieved {len(history)} USDT balance records")
        
        latest = manager.get_latest_balances()
        print(f"💰 Latest balances for {len(latest)} currencies")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")