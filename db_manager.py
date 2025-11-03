#!/usr/bin/env python3
"""
Database Management CLI for Wallet Balance History

This script provides command-line tools for managing the wallet balance database.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def list_balances(args):
    """List current wallet balances"""
    from database import get_db_manager
    
    try:
        db_manager = get_db_manager()
        latest = db_manager.get_latest_balances()
        
        if not latest:
            print("💰 No wallet balances found in database")
            return
        
        print(f"💰 Latest Wallet Balances ({len(latest)} currencies):")
        print("-" * 60)
        
        total_usd_equivalent = 0
        for currency, data in latest.items():
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
            
            print(f"{currency:>8}: Available={data['available_balance']:>12.6f}, "
                  f"Locked={data['locked_balance']:>10.6f}, "
                  f"Total={data['total_balance']:>12.6f}")
            print(f"         Last Updated: {time_str}")
            print()
            
            # Rough USD calculation (assuming USDT = 1 USD for display)
            if currency == 'USDT':
                total_usd_equivalent += data['total_balance']
        
        if total_usd_equivalent > 0:
            print(f"📊 Estimated Total (USDT equivalent): ${total_usd_equivalent:,.2f}")
            
    except Exception as e:
        print(f"❌ Error listing balances: {e}")

def show_history(args):
    """Show wallet balance history"""
    from database import get_db_manager
    
    try:
        db_manager = get_db_manager()
        history = db_manager.get_wallet_history(currency=args.currency, hours=args.hours)
        
        if not history:
            currency_str = f" for {args.currency}" if args.currency else ""
            print(f"📈 No wallet history found{currency_str} in the last {args.hours} hours")
            return
        
        currency_str = f" for {args.currency}" if args.currency else ""
        print(f"📈 Wallet Balance History{currency_str} (Last {args.hours} hours, {len(history)} records):")
        print("-" * 80)
        
        # Group by currency
        by_currency = {}
        for record in history:
            currency = record['currency']
            if currency not in by_currency:
                by_currency[currency] = []
            by_currency[currency].append(record)
        
        for currency, records in by_currency.items():
            print(f"\n💰 {currency} ({len(records)} records):")
            print(f"{'Time':<20} {'Available':>12} {'Locked':>10} {'Total':>12} {'Change':>10}")
            print("-" * 66)
            
            prev_available = None
            for record in reversed(records):  # Show oldest first
                timestamp = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                time_str = timestamp.strftime('%m-%d %H:%M:%S')
                
                change_str = ""
                if prev_available is not None:
                    change = record['available_balance'] - prev_available
                    if change > 0:
                        change_str = f"+{change:.4f}"
                    elif change < 0:
                        change_str = f"{change:.4f}"
                    else:
                        change_str = "0.0000"
                
                print(f"{time_str:<20} {record['available_balance']:>12.6f} "
                      f"{record['locked_balance']:>10.6f} {record['total_balance']:>12.6f} "
                      f"{change_str:>10}")
                
                prev_available = record['available_balance']
            
    except Exception as e:
        print(f"❌ Error showing history: {e}")

def cleanup_data(args):
    """Clean up old database records"""
    from database import get_db_manager
    
    try:
        if not args.force and args.days < 7:
            response = input(f"⚠️  You're about to delete data older than {args.days} days. "
                           f"This action cannot be undone. Continue? (y/N): ")
            if response.lower() != 'y':
                print("❌ Cleanup cancelled")
                return
        
        db_manager = get_db_manager()
        deleted_count = db_manager.cleanup_old_data(days=args.days)
        
        print(f"🧹 Cleanup completed: {deleted_count} records deleted")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

def show_stats(args):
    """Show database statistics"""
    from database import get_db_manager
    
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        from database import WalletBalanceHistory, WalletSummaryHistory
        from sqlalchemy import func
        
        # Get record counts
        balance_count = session.query(WalletBalanceHistory).count()
        summary_count = session.query(WalletSummaryHistory).count()
        
        # Get date range
        oldest_balance = session.query(func.min(WalletBalanceHistory.timestamp)).scalar()
        newest_balance = session.query(func.max(WalletBalanceHistory.timestamp)).scalar()
        
        # Get currency count
        currency_count = session.query(WalletBalanceHistory.currency).distinct().count()
        
        session.close()
        
        print("📊 Database Statistics:")
        print("-" * 40)
        print(f"Balance Records:     {balance_count:,}")
        print(f"Summary Records:     {summary_count:,}")
        print(f"Unique Currencies:   {currency_count}")
        
        if oldest_balance and newest_balance:
            duration = newest_balance - oldest_balance
            print(f"Data Range:          {duration.days} days")
            print(f"Oldest Record:       {oldest_balance.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"Newest Record:       {newest_balance.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
    except Exception as e:
        print(f"❌ Error showing stats: {e}")

def export_data(args):
    """Export wallet data to CSV"""
    import csv
    from database import get_db_manager
    
    try:
        db_manager = get_db_manager()
        history = db_manager.get_wallet_history(currency=args.currency, hours=args.hours)
        
        if not history:
            print("📄 No data to export")
            return
        
        filename = args.output or f"wallet_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'currency', 'available_balance', 'locked_balance', 
                         'total_balance', 'cross_user_margin', 'cross_order_margin']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for record in history:
                writer.writerow(record)
        
        print(f"📄 Data exported to: {filename}")
        print(f"📊 Records exported: {len(history)}")
        
    except Exception as e:
        print(f"❌ Error exporting data: {e}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Wallet Balance Database Management Tool')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List current wallet balances')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show wallet balance history')
    history_parser.add_argument('--currency', '-c', help='Filter by currency (e.g., USDT)')
    history_parser.add_argument('--hours', '-h', type=int, default=24, 
                               help='Hours of history to show (default: 24)')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old database records')
    cleanup_parser.add_argument('--days', '-d', type=int, default=30,
                               help='Keep data newer than this many days (default: 30)')
    cleanup_parser.add_argument('--force', '-f', action='store_true',
                               help='Skip confirmation prompt')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export wallet data to CSV')
    export_parser.add_argument('--currency', '-c', help='Filter by currency (e.g., USDT)')
    export_parser.add_argument('--hours', '-h', type=int, default=168,
                              help='Hours of history to export (default: 168 = 1 week)')
    export_parser.add_argument('--output', '-o', help='Output filename (default: auto-generated)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("💰 Wallet Balance Database Manager")
    print("=" * 40)
    
    # Check database connection
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        return
    
    try:
        if args.command == 'list':
            list_balances(args)
        elif args.command == 'history':
            show_history(args)
        elif args.command == 'cleanup':
            cleanup_data(args)
        elif args.command == 'stats':
            show_stats(args)
        elif args.command == 'export':
            export_data(args)
        else:
            print(f"❌ Unknown command: {args.command}")
            
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()