# Wallet Balance Database Setup

This document explains how to set up and use the wallet balance history database.

## Overview

The wallet balance tracking system stores your CoinDCX futures wallet balances over time, allowing you to:
- Track balance changes throughout the day
- View historical data for any currency
- Analyze wallet performance over time
- Export data for external analysis

## Database Setup

### 1. Prerequisites

Install required Python packages:
```bash
pip install -r requirements.txt
```

### 2. Database Configuration

Set your PostgreSQL database URL in the `.env` file:
```bash
DATABASE_URL="postgresql://username:password@localhost:5432/database_name"
```

Example:
```bash
DATABASE_URL="postgresql://postgres:abc123@localhost:5432/paper_trading_agent"
```

### 3. Initialize Database

Run the initialization script to create tables:
```bash
python init_database.py
```

This will:
- Connect to your PostgreSQL database
- Create the necessary tables
- Test the connection
- Provide setup confirmation

## Database Tables

### `wallet_balance_history`
Stores individual currency balance records over time:
- `id`: Primary key
- `timestamp`: When the balance was recorded (UTC)
- `currency`: Currency code (USDT, BTC, etc.)
- `available_balance`: Available balance (what you can trade with)
- `locked_balance`: Locked balance (in open orders/margin)
- `total_balance`: Total balance (available + locked)
- `cross_user_margin`: Cross margin amount
- `cross_order_margin`: Order margin amount
- `raw_data`: Full API response (JSON)

### `wallet_summary_history`
Stores wallet summary snapshots:
- `id`: Primary key
- `timestamp`: When the summary was recorded (UTC)
- `total_balance_usd`: Total balance in USD equivalent
- `total_available_usd`: Total available in USD equivalent
- `total_locked_usd`: Total locked in USD equivalent
- `currencies_count`: Number of currencies with balances
- `summary_data`: Additional summary metadata (JSON)

## Automatic Data Collection

Balance data is automatically stored when:
- You refresh wallet data in the dashboard
- Auto-refresh runs every 3 minutes
- API calls are made to fetch wallet balances

## Using the Dashboard

### View Current Balances
Navigate to the dashboard and click "Refresh Wallet" to see current balances. This data is automatically stored in the database.

### View Balance History
1. In the dashboard, find the "Wallet Balance History" section
2. Select currency filter (optional)
3. Choose timeframe (1 hour to 1 week)
4. Click "Load History"

### API Endpoints

Access wallet history via REST API:

```bash
# Get all currency history for last 24 hours
GET /wallets/history?hours=24

# Get USDT history for last week
GET /wallets/history?currency=USDT&hours=168

# Get wallet summary history
GET /wallets/summary/history?hours=24

# Get latest balances from database
GET /wallets/latest
```

## Command Line Management

Use the `db_manager.py` CLI tool for database operations:

### View Current Balances
```bash
python db_manager.py list
```

### View History
```bash
# All currencies, last 24 hours
python db_manager.py history

# USDT only, last week
python db_manager.py history --currency USDT --hours 168
```

### Database Statistics
```bash
python db_manager.py stats
```

### Export Data
```bash
# Export USDT data for last week to CSV
python db_manager.py export --currency USDT --hours 168 --output usdt_week.csv
```

### Cleanup Old Data
```bash
# Keep only last 30 days
python db_manager.py cleanup --days 30

# Keep only last 7 days (with confirmation prompt)
python db_manager.py cleanup --days 7

# Force cleanup without confirmation
python db_manager.py cleanup --days 7 --force
```

## Database Maintenance

### Automatic Cleanup
Set up automatic cleanup by adding to your environment:
```bash
MAX_DB_SIZE_MB=100.0
CLEANUP_RETENTION_DAYS=30
```

### Manual Cleanup
Use the cleanup endpoint:
```bash
POST /database/cleanup
Content-Type: application/json

{
  "days": 30
}
```

### Performance Tips

1. **Indexes**: The database includes optimized indexes for common queries
2. **Regular Cleanup**: Clean up old data regularly to maintain performance
3. **Currency Filtering**: Use currency filters for faster queries on large datasets
4. **Time Windows**: Use appropriate time windows - shorter ranges are faster

## Troubleshooting

### Connection Issues
1. Verify DATABASE_URL is correct
2. Ensure PostgreSQL is running
3. Check database credentials and permissions

### Missing Data
1. Ensure the dashboard is fetching wallet data
2. Check if auto-refresh is working
3. Verify API credentials are configured

### Performance Issues
1. Run database cleanup to remove old data
2. Check database size and available disk space
3. Consider indexing if querying large datasets

## Data Privacy

- All data is stored locally in your PostgreSQL database
- No data is sent to external services
- Raw API responses are stored for debugging (can be disabled)
- Clean up old data regularly for privacy

## Backup and Recovery

### Backup Database
```bash
pg_dump -h localhost -U postgres -d paper_trading_agent > wallet_backup.sql
```

### Restore Database
```bash
psql -h localhost -U postgres -d paper_trading_agent < wallet_backup.sql
```

## Support

For issues or questions:
1. Check the logs in the Flask dashboard
2. Use `python db_manager.py stats` to verify database state
3. Test connection with `python init_database.py`