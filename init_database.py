#!/usr/bin/env python3
"""
Database initialization script for Wallet Balance History

This script initializes the database and creates all necessary tables.
Run this before starting the application for the first time.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Initialize the database"""
    print("🚀 Initializing Wallet Balance History Database...")
    
    try:
        # Check if DATABASE_URL is set
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ ERROR: DATABASE_URL not found in environment variables")
            print("   Please check your .env file and ensure DATABASE_URL is set")
            return False
        
        print(f"🔗 Database URL: {database_url}")
        
        # Import and initialize database
        from database import DatabaseManager
        
        # Create database manager (this will create tables)
        db_manager = DatabaseManager(database_url)
        
        print("✅ Database initialization completed successfully!")
        print("\n📋 Database Tables Created:")
        print("   - wallet_balance_history: Stores individual currency balances over time")
        print("   - wallet_summary_history: Stores wallet summary snapshots over time")
        
        print("\n🔍 Testing database connection...")
        
        # Test storing and retrieving data
        test_wallet_data = {
            "wallets": [
                {
                    "currency_short_name": "USDT",
                    "balance": 50.0,
                    "locked_balance": 5.0,
                    "cross_user_margin": 0.0,
                    "cross_order_margin": 0.0
                }
            ]
        }
        
        test_summary = {
            "total_balance": 55.0,
            "available_balance": 50.0,
            "total_locked": 5.0
        }
        
        # Store test data
        success = db_manager.store_wallet_balance(test_wallet_data, test_summary)
        if success:
            print("✅ Test data storage: SUCCESS")
        else:
            print("❌ Test data storage: FAILED")
            return False
        
        # Retrieve test data
        history = db_manager.get_wallet_history(hours=1)
        if history:
            print(f"✅ Test data retrieval: SUCCESS ({len(history)} records)")
        else:
            print("⚠️  Test data retrieval: No records found (this might be expected)")
        
        # Clean up test data
        cleanup_count = db_manager.cleanup_old_data(days=0)  # Remove all data
        print(f"🧹 Cleaned up {cleanup_count} test records")
        
        print("\n🎉 Database is ready for use!")
        print("\n📌 Next Steps:")
        print("   1. Start the Flask dashboard: python scanner_dashboard.py")
        print("   2. Wallet balance data will be automatically stored when fetched")
        print("   3. View wallet history at: http://localhost:5000/wallets/history")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        print("\n📋 Full error details:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)