#!/usr/bin/env python3
"""
Migration script from SQLite to PostgreSQL for production deployment.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import Database as SQLiteDatabase
from database_postgres import PostgresDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_data():
    """Migrate all data from SQLite to PostgreSQL"""
    logger.info("Starting migration from SQLite to PostgreSQL...")
    
    # Initialize databases
    sqlite_db = SQLiteDatabase()
    postgres_db = PostgresDatabase()
    
    try:
        # Get SQLite connection
        sqlite_conn = sqlite_db.conn
        
        # Migrate users
        logger.info("Migrating users...")
        users = sqlite_conn.execute("SELECT * FROM users").fetchall()
        migrated_users = 0
        
        for user in users:
            success = postgres_db.register_user(
                telegram_id=user['telegram_id'],
                username=user['username'],
                first_name=user['first_name'],
                last_name=user['last_name'],
                mt4_account=user['mt4_account']
            )
            if success:
                migrated_users += 1
        
        logger.info(f"Migrated {migrated_users} users")
        
        # Migrate user settings
        logger.info("Migrating user settings...")
        settings = sqlite_conn.execute("SELECT * FROM user_settings").fetchall()
        migrated_settings = 0
        
        for setting in settings:
            settings_dict = {
                'risk_percent': setting['risk_percent'],
                'default_lot_size': setting['default_lot_size'],
                'max_lot_size': setting['max_lot_size'],
                'auto_trade': bool(setting['auto_trade']),
                'notifications': bool(setting['notifications']),
                'max_daily_trades': setting['max_daily_trades']
            }
            
            success = postgres_db.update_user_settings(
                telegram_id=setting['telegram_id'],
                settings=settings_dict
            )
            if success:
                migrated_settings += 1
        
        logger.info(f"Migrated {migrated_settings} user settings")
        
        # Migrate MT4 accounts
        logger.info("Migrating MT4 accounts...")
        accounts = sqlite_conn.execute("SELECT * FROM mt4_accounts").fetchall()
        migrated_accounts = 0
        
        for account in accounts:
            if not account['is_active']:
                continue
                
            # Get decrypted password from SQLite
            creds = sqlite_db.get_account_credentials(account['account_number'])
            if creds and creds.get('password'):
                result = postgres_db.add_mt4_account(
                    telegram_id=account['telegram_id'],
                    account_number=account['account_number'],
                    account_name=account['account_name'],
                    server=account['server'],
                    password=creds['password']
                )
                if result:
                    migrated_accounts += 1
                    
                    # Set default account if needed
                    if account['is_default']:
                        with postgres_db.get_cursor() as cursor:
                            cursor.execute("""
                                UPDATE mt4_accounts 
                                SET is_default = TRUE 
                                WHERE account_number = %s
                            """, (account['account_number'],))
        
        logger.info(f"Migrated {migrated_accounts} MT4 accounts")
        
        # Migrate account settings
        logger.info("Migrating account settings...")
        acc_settings = sqlite_conn.execute("SELECT * FROM account_settings").fetchall()
        migrated_acc_settings = 0
        
        for acc_setting in acc_settings:
            settings_dict = {
                'risk_percent': acc_setting['risk_percent'],
                'default_lot_size': acc_setting['default_lot_size'],
                'max_lot_size': acc_setting['max_lot_size'],
                'auto_trade': bool(acc_setting['auto_trade']),
                'notifications': bool(acc_setting['notifications']),
                'max_daily_trades': acc_setting['max_daily_trades']
            }
            
            # Check if account exists in PostgreSQL
            with postgres_db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 1 FROM mt4_accounts 
                    WHERE account_number = %s
                """, (acc_setting['account_number'],))
                
                if cursor.fetchone():
                    with postgres_db.get_cursor() as update_cursor:
                        # Update account settings
                        for field, value in settings_dict.items():
                            update_cursor.execute(f"""
                                UPDATE account_settings 
                                SET {field} = %s 
                                WHERE account_number = %s
                            """, (value, acc_setting['account_number']))
                    migrated_acc_settings += 1
        
        logger.info(f"Migrated {migrated_acc_settings} account settings")
        
        # Migrate signal history
        logger.info("Migrating signal history...")
        signals = sqlite_conn.execute("SELECT * FROM signal_history").fetchall()
        migrated_signals = 0
        
        with postgres_db.get_connection() as conn:
            cursor = conn.cursor()
            
            for signal in signals:
                try:
                    cursor.execute("""
                        INSERT INTO signal_history 
                        (signal_id, telegram_id, mt4_account, symbol, action, 
                         volume, price, sl, tp, profit, status, ticket, 
                         created_at, executed_at, closed_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (signal_id) DO NOTHING
                    """, (
                        signal['signal_id'],
                        signal['telegram_id'],
                        signal['mt4_account'],
                        signal['symbol'],
                        signal['action'],
                        signal['volume'],
                        signal['price'],
                        signal['sl'],
                        signal['tp'],
                        signal['profit'],
                        signal['status'],
                        signal['ticket'],
                        signal['created_at'],
                        signal['executed_at'],
                        signal['closed_at']
                    ))
                    migrated_signals += 1
                except Exception as e:
                    logger.warning(f"Failed to migrate signal {signal['signal_id']}: {e}")
        
        logger.info(f"Migrated {migrated_signals} signal history records")
        
        # Summary
        logger.info("Migration completed successfully!")
        logger.info(f"Summary:")
        logger.info(f"  - Users: {migrated_users}")
        logger.info(f"  - User Settings: {migrated_settings}")
        logger.info(f"  - MT4 Accounts: {migrated_accounts}")
        logger.info(f"  - Account Settings: {migrated_acc_settings}")
        logger.info(f"  - Signal History: {migrated_signals}")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    finally:
        sqlite_db.close()

def verify_migration():
    """Verify the migration was successful"""
    logger.info("Verifying migration...")
    
    sqlite_db = SQLiteDatabase()
    postgres_db = PostgresDatabase()
    
    try:
        # Count records in both databases
        sqlite_conn = sqlite_db.conn
        
        # Users
        sqlite_users = sqlite_conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        with postgres_db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users")
            pg_users = cursor.fetchone()['count']
        
        logger.info(f"Users - SQLite: {sqlite_users}, PostgreSQL: {pg_users}")
        
        # MT4 Accounts
        sqlite_accounts = sqlite_conn.execute(
            "SELECT COUNT(*) FROM mt4_accounts WHERE is_active = 1"
        ).fetchone()[0]
        with postgres_db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM mt4_accounts WHERE is_active = TRUE")
            pg_accounts = cursor.fetchone()['count']
        
        logger.info(f"MT4 Accounts - SQLite: {sqlite_accounts}, PostgreSQL: {pg_accounts}")
        
        # Signal History
        sqlite_signals = sqlite_conn.execute("SELECT COUNT(*) FROM signal_history").fetchone()[0]
        with postgres_db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM signal_history")
            pg_signals = cursor.fetchone()['count']
        
        logger.info(f"Signal History - SQLite: {sqlite_signals}, PostgreSQL: {pg_signals}")
        
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False
    finally:
        sqlite_db.close()

if __name__ == "__main__":
    # Check if PostgreSQL is configured
    if not os.environ.get('DATABASE_URL'):
        logger.warning("DATABASE_URL not set. Using default PostgreSQL connection.")
        logger.info("Set DATABASE_URL environment variable for production use.")
    
    # Run migration
    if migrate_data():
        logger.info("Migration successful!")
        verify_migration()
    else:
        logger.error("Migration failed!")
        sys.exit(1)