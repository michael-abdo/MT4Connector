"""
Database module for Telegram Connector
Handles user registration, settings, and signal history
"""
import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
from cryptography.fernet import Fernet
import base64

logger = logging.getLogger(__name__)

class Database:
    """SQLite database handler for user data and signal history"""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'data', 'telegram_connector.db')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Create users table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    mt4_account INTEGER DEFAULT 12345,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_admin BOOLEAN DEFAULT 0
                )
            """)
            
            # Create user settings table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    telegram_id INTEGER PRIMARY KEY,
                    risk_percent REAL DEFAULT 1.0,
                    default_lot_size REAL DEFAULT 0.01,
                    max_lot_size REAL DEFAULT 1.0,
                    auto_trade BOOLEAN DEFAULT 0,
                    notifications BOOLEAN DEFAULT 1,
                    trailing_stop BOOLEAN DEFAULT 0,
                    max_daily_trades INTEGER DEFAULT 10,
                    settings_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                )
            """)
            
            # Create signal history table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE,
                    telegram_id INTEGER,
                    mt4_account INTEGER,
                    symbol TEXT,
                    action TEXT,
                    volume REAL,
                    price REAL,
                    sl REAL,
                    tp REAL,
                    status TEXT,
                    ticket INTEGER,
                    profit REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    closed_at TIMESTAMP,
                    signal_data TEXT,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                )
            """)
            
            # Create mt4_accounts table for multi-account support
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS mt4_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER,
                    account_number INTEGER UNIQUE,
                    account_name TEXT,
                    server TEXT,
                    encrypted_password TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                )
            """)
            
            # Create account_settings table for per-account settings
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS account_settings (
                    account_number INTEGER PRIMARY KEY,
                    risk_percent REAL DEFAULT 1.0,
                    default_lot_size REAL DEFAULT 0.01,
                    max_lot_size REAL DEFAULT 1.0,
                    auto_trade BOOLEAN DEFAULT 0,
                    notifications BOOLEAN DEFAULT 1,
                    max_daily_trades INTEGER DEFAULT 10,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_number) REFERENCES mt4_accounts(account_number)
                )
            """)
            
            # Create indices for performance
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_telegram_id ON signal_history(telegram_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_status ON signal_history(status)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_created ON signal_history(created_at)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_accounts_telegram_id ON mt4_accounts(telegram_id)")
            
            self.conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def register_user(self, telegram_id: int, username: str = None, 
                     first_name: str = None, last_name: str = None,
                     mt4_account: int = 12345) -> bool:
        """Register a new user"""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO users 
                (telegram_id, username, first_name, last_name, mt4_account)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, username, first_name, last_name, mt4_account))
            
            # Create default settings
            self.conn.execute("""
                INSERT OR IGNORE INTO user_settings (telegram_id)
                VALUES (?)
            """, (telegram_id,))
            
            self.conn.commit()
            logger.info(f"User {telegram_id} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False
    
    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user information"""
        try:
            cursor = self.conn.execute("""
                SELECT * FROM users WHERE telegram_id = ?
            """, (telegram_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_user_settings(self, telegram_id: int, settings: Dict[str, Any]) -> bool:
        """Update user settings"""
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            
            allowed_fields = [
                'risk_percent', 'default_lot_size', 'max_lot_size',
                'auto_trade', 'notifications', 'trailing_stop', 'max_daily_trades'
            ]
            
            for field in allowed_fields:
                if field in settings:
                    update_fields.append(f"{field} = ?")
                    values.append(settings[field])
            
            if not update_fields:
                return True  # Nothing to update
            
            # Add timestamp and telegram_id
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(telegram_id)
            
            query = f"""
                UPDATE user_settings 
                SET {', '.join(update_fields)}
                WHERE telegram_id = ?
            """
            
            self.conn.execute(query, values)
            self.conn.commit()
            
            logger.info(f"Updated settings for user {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            return False
    
    def get_user_settings(self, telegram_id: int) -> Dict[str, Any]:
        """Get user settings"""
        try:
            cursor = self.conn.execute("""
                SELECT * FROM user_settings WHERE telegram_id = ?
            """, (telegram_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            # Return defaults if not found
            return {
                'risk_percent': 1.0,
                'default_lot_size': 0.01,
                'max_lot_size': 1.0,
                'auto_trade': False,
                'notifications': True,
                'trailing_stop': False,
                'max_daily_trades': 10
            }
            
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            return {}
    
    def add_signal_history(self, signal_data: Dict[str, Any]) -> bool:
        """Add signal to history"""
        try:
            self.conn.execute("""
                INSERT INTO signal_history 
                (signal_id, telegram_id, mt4_account, symbol, action, 
                 volume, price, sl, tp, status, signal_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_data.get('signal_id'),
                signal_data.get('telegram_id'),
                signal_data.get('mt4_account', 12345),
                signal_data.get('symbol'),
                signal_data.get('action'),
                signal_data.get('volume'),
                signal_data.get('price'),
                signal_data.get('sl'),
                signal_data.get('tp'),
                signal_data.get('status', 'pending'),
                json.dumps(signal_data)
            ))
            
            self.conn.commit()
            logger.info(f"Signal {signal_data.get('signal_id')} added to history")
            return True
            
        except Exception as e:
            logger.error(f"Error adding signal to history: {e}")
            return False
    
    def update_signal_status(self, signal_id: str, status: str, 
                           ticket: int = None, executed_at: datetime = None) -> bool:
        """Update signal status"""
        try:
            if executed_at is None and status == 'executed':
                executed_at = datetime.now()
            
            self.conn.execute("""
                UPDATE signal_history 
                SET status = ?, ticket = ?, executed_at = ?
                WHERE signal_id = ?
            """, (status, ticket, executed_at, signal_id))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating signal status: {e}")
            return False
    
    def get_user_signals(self, telegram_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's signal history"""
        try:
            cursor = self.conn.execute("""
                SELECT * FROM signal_history 
                WHERE telegram_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (telegram_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting user signals: {e}")
            return []
    
    def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Get user trading statistics"""
        try:
            # Total trades
            cursor = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN status = 'executed' THEN 1 END) as executed_trades,
                    COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_trades,
                    SUM(CASE WHEN profit > 0 THEN profit ELSE 0 END) as total_profit,
                    SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END) as total_loss
                FROM signal_history
                WHERE telegram_id = ?
            """, (telegram_id,))
            
            stats = dict(cursor.fetchone())
            
            # Calculate win rate
            if stats['executed_trades'] > 0:
                cursor = self.conn.execute("""
                    SELECT COUNT(*) as winning_trades
                    FROM signal_history
                    WHERE telegram_id = ? AND profit > 0
                """, (telegram_id,))
                
                winning = cursor.fetchone()['winning_trades']
                stats['win_rate'] = (winning / stats['executed_trades']) * 100
            else:
                stats['win_rate'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for credentials"""
        key_file = os.path.join(os.path.dirname(self.db_path), '.encryption_key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def add_mt4_account(self, telegram_id: int, account_number: int, 
                       account_name: str, server: str, password: str,
                       is_default: bool = False) -> bool:
        """Add a new MT4 account for a user"""
        try:
            # Encrypt password
            cipher = Fernet(self._get_encryption_key())
            encrypted_password = cipher.encrypt(password.encode()).decode()
            
            # If setting as default, unset other defaults
            if is_default:
                self.conn.execute("""
                    UPDATE mt4_accounts SET is_default = 0 
                    WHERE telegram_id = ?
                """, (telegram_id,))
            
            # Insert new account
            self.conn.execute("""
                INSERT INTO mt4_accounts 
                (telegram_id, account_number, account_name, server, 
                 encrypted_password, is_default, last_used)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (telegram_id, account_number, account_name, server, 
                  encrypted_password, is_default))
            
            # Create default account settings
            self.conn.execute("""
                INSERT OR IGNORE INTO account_settings (account_number)
                VALUES (?)
            """, (account_number,))
            
            self.conn.commit()
            logger.info(f"Added MT4 account {account_number} for user {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding MT4 account: {e}")
            return False
    
    def get_user_accounts(self, telegram_id: int) -> List[Dict[str, Any]]:
        """Get all MT4 accounts for a user"""
        try:
            cursor = self.conn.execute("""
                SELECT id, account_number, account_name, server, 
                       is_active, is_default, last_used
                FROM mt4_accounts
                WHERE telegram_id = ? AND is_active = 1
                ORDER BY is_default DESC, last_used DESC
            """, (telegram_id,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting user accounts: {e}")
            return []
    
    def get_account_credentials(self, telegram_id: int, account_number: int) -> Optional[Dict[str, Any]]:
        """Get decrypted credentials for an account"""
        try:
            cursor = self.conn.execute("""
                SELECT account_number, server, encrypted_password
                FROM mt4_accounts
                WHERE telegram_id = ? AND account_number = ? AND is_active = 1
            """, (telegram_id, account_number))
            
            row = cursor.fetchone()
            if row:
                # Decrypt password
                cipher = Fernet(self._get_encryption_key())
                password = cipher.decrypt(row['encrypted_password'].encode()).decode()
                
                return {
                    'account_number': row['account_number'],
                    'server': row['server'],
                    'password': password
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting account credentials: {e}")
            return None
    
    def set_default_account(self, telegram_id: int, account_number: int) -> bool:
        """Set a user's default account"""
        try:
            # Unset other defaults
            self.conn.execute("""
                UPDATE mt4_accounts SET is_default = 0 
                WHERE telegram_id = ?
            """, (telegram_id,))
            
            # Set new default
            self.conn.execute("""
                UPDATE mt4_accounts 
                SET is_default = 1, last_used = CURRENT_TIMESTAMP
                WHERE telegram_id = ? AND account_number = ?
            """, (telegram_id, account_number))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error setting default account: {e}")
            return False
    
    def get_default_account(self, telegram_id: int) -> Optional[int]:
        """Get user's default account number"""
        try:
            cursor = self.conn.execute("""
                SELECT account_number FROM mt4_accounts
                WHERE telegram_id = ? AND is_default = 1 AND is_active = 1
            """, (telegram_id,))
            
            row = cursor.fetchone()
            return row['account_number'] if row else None
            
        except Exception as e:
            logger.error(f"Error getting default account: {e}")
            return None
    
    def update_account_settings(self, account_number: int, settings: Dict[str, Any]) -> bool:
        """Update settings for a specific account"""
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            
            allowed_fields = [
                'risk_percent', 'default_lot_size', 'max_lot_size',
                'auto_trade', 'notifications', 'max_daily_trades'
            ]
            
            for field in allowed_fields:
                if field in settings:
                    update_fields.append(f"{field} = ?")
                    values.append(settings[field])
            
            if not update_fields:
                return True
            
            # Add timestamp and account number
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(account_number)
            
            query = f"""
                UPDATE account_settings 
                SET {', '.join(update_fields)}
                WHERE account_number = ?
            """
            
            self.conn.execute(query, values)
            self.conn.commit()
            
            logger.info(f"Updated settings for account {account_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating account settings: {e}")
            return False
    
    def get_account_settings(self, account_number: int) -> Dict[str, Any]:
        """Get settings for a specific account"""
        try:
            cursor = self.conn.execute("""
                SELECT * FROM account_settings WHERE account_number = ?
            """, (account_number,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            # Return defaults if not found
            return {
                'risk_percent': 1.0,
                'default_lot_size': 0.01,
                'max_lot_size': 1.0,
                'auto_trade': False,
                'notifications': True,
                'max_daily_trades': 10
            }
            
        except Exception as e:
            logger.error(f"Error getting account settings: {e}")
            return {}
    
    def update_account_settings(self, account_number: int, settings: dict) -> bool:
        """Update per-account trading settings"""
        try:
            # Build update query dynamically based on provided settings
            allowed_fields = [
                'risk_percent', 'default_lot_size', 'max_lot_size',
                'auto_trade', 'notifications', 'max_daily_trades'
            ]
            
            update_fields = []
            values = []
            
            for field in allowed_fields:
                if field in settings:
                    update_fields.append(f"{field} = ?")
                    values.append(settings[field])
            
            if not update_fields:
                return True  # Nothing to update
            
            # Add account number and timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(account_number)
            
            query = f"""
                UPDATE account_settings 
                SET {', '.join(update_fields)}
                WHERE account_number = ?
            """
            
            self.conn.execute(query, values)
            self.conn.commit()
            
            logger.info(f"Updated settings for account {account_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating account settings: {e}")
            return False
    
    def get_account_stats(self, account_number: int) -> dict:
        """Get trading statistics for a specific account"""
        try:
            # Get executed trades count
            cursor = self.conn.execute("""
                SELECT COUNT(*) as executed_trades
                FROM signal_history
                WHERE mt4_account = ? AND status = 'executed'
            """, (account_number,))
            
            executed_trades = cursor.fetchone()['executed_trades']
            
            if executed_trades == 0:
                return None
            
            # Get win/loss stats
            cursor = self.conn.execute("""
                SELECT 
                    COUNT(CASE WHEN profit > 0 THEN 1 END) as wins,
                    COUNT(CASE WHEN profit < 0 THEN 1 END) as losses,
                    SUM(CASE WHEN profit > 0 THEN profit ELSE 0 END) as total_profit,
                    SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END) as total_loss
                FROM signal_history
                WHERE mt4_account = ? AND status = 'executed'
            """, (account_number,))
            
            row = cursor.fetchone()
            wins = row['wins'] or 0
            losses = row['losses'] or 0
            total_profit = row['total_profit'] or 0
            total_loss = row['total_loss'] or 0
            
            # Calculate win rate
            total_closed = wins + losses
            win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
            
            return {
                'executed_trades': executed_trades,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'total_loss': total_loss,
                'net_profit': total_profit + total_loss
            }
            
        except Exception as e:
            logger.error(f"Error getting account stats: {e}")
            return None
    
    def get_account_settings(self, account_number: int) -> dict:
        """Get per-account trading settings"""
        try:
            cursor = self.conn.execute("""
                SELECT risk_percent, default_lot_size, max_lot_size,
                       auto_trade, notifications, max_daily_trades
                FROM account_settings
                WHERE account_number = ?
            """, (account_number,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            # If no settings exist, create default settings
            self.conn.execute("""
                INSERT INTO account_settings (account_number)
                VALUES (?)
            """, (account_number,))
            self.conn.commit()
            
            # Return defaults
            return {
                'risk_percent': 1.0,
                'default_lot_size': 0.01,
                'max_lot_size': 1.0,
                'auto_trade': False,
                'notifications': True,
                'max_daily_trades': 10
            }
            
        except Exception as e:
            logger.error(f"Error getting account settings: {e}")
            return {}
    
    def remove_account(self, telegram_id: int, account_number: int) -> bool:
        """Remove an account (soft delete)"""
        try:
            self.conn.execute("""
                UPDATE mt4_accounts 
                SET is_active = 0
                WHERE telegram_id = ? AND account_number = ?
            """, (telegram_id, account_number))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error removing account: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

# Create singleton instance
_db_instance = None

def get_database() -> Database:
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance