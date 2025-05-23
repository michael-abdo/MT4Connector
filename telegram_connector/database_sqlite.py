"""
SQLite implementation of database for testing (implements same interface as database_postgres.py)
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from contextlib import contextmanager
from cryptography.fernet import Fernet

# Configure logging
logger = logging.getLogger(__name__)

class SQLiteDatabase:
    """SQLite database implementation for testing"""
    
    def __init__(self, db_path=':memory:'):
        """Initialize SQLite database"""
        self.db_path = db_path
        self._encryption_key = self._get_or_create_key()
        self._fernet = Fernet(self._encryption_key)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Initialize database schema
        self._init_database()
        
    @contextmanager
    def get_connection(self):
        """Get a database connection (compatibility with PostgreSQL interface)"""
        yield self.conn
    
    @contextmanager
    def get_cursor(self):
        """Get a database cursor with automatic cleanup"""
        cursor = self.conn.cursor()
        yield cursor
        self.conn.commit()
    
    def _get_or_create_key(self):
        """Get or create encryption key"""
        key_file = os.path.join(os.path.dirname(__file__), '.encryption_key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def _init_database(self):
        """Initialize database schema"""
        try:
            cursor = self.conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    mt4_account INTEGER,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create user settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    risk_percent REAL DEFAULT 1.0,
                    default_lot_size REAL DEFAULT 0.01,
                    max_lot_size REAL DEFAULT 1.0,
                    auto_trade INTEGER DEFAULT 0,
                    notifications INTEGER DEFAULT 1,
                    max_daily_trades INTEGER DEFAULT 10,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                )
            """)
            
            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                )
            """)
            
            # Create rate limits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    request_count INTEGER DEFAULT 1,
                    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(identifier, endpoint, window_start)
                )
            """)
            
            self.conn.commit()
            logger.info("SQLite database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {e}")
            raise
    
    def create_session(self, telegram_id: int, session_token: str, 
                      ip_address: str = None, user_agent: str = None,
                      expires_hours: int = 24) -> bool:
        """Create a new user session"""
        try:
            cursor = self.conn.cursor()
            expires_at = datetime.now().timestamp() + (expires_hours * 3600)
            
            cursor.execute("""
                INSERT INTO user_sessions 
                (telegram_id, session_token, ip_address, user_agent, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, session_token, ip_address, user_agent, expires_at))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    def validate_session(self, session_token: str) -> dict:
        """Validate a session token"""
        try:
            cursor = self.conn.cursor()
            now = datetime.now().timestamp()
            
            cursor.execute("""
                SELECT s.*, u.username, u.first_name, u.last_name
                FROM user_sessions s
                JOIN users u ON s.telegram_id = u.telegram_id
                WHERE s.session_token = ? AND s.expires_at > ?
            """, (session_token, now))
            
            row = cursor.fetchone()
            if row:
                # Update last activity
                cursor.execute("""
                    UPDATE user_sessions 
                    SET last_activity = CURRENT_TIMESTAMP
                    WHERE session_token = ?
                """, (session_token,))
                self.conn.commit()
                
                return dict(row)
                
            return None
            
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None
    
    def check_rate_limit(self, identifier: str, endpoint: str, 
                        max_requests: int = 60, window_minutes: int = 1) -> bool:
        """Check if request is within rate limit"""
        try:
            cursor = self.conn.cursor()
            window_start = datetime.now().timestamp() - (window_minutes * 60)
            
            # Count requests in current window
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM api_rate_limits
                WHERE identifier = ? AND endpoint = ?
                AND window_start > ?
            """, (identifier, endpoint, window_start))
            
            count = cursor.fetchone()['count']
            
            if count >= max_requests:
                return False
            
            # Add request
            cursor.execute("""
                INSERT INTO api_rate_limits (identifier, endpoint)
                VALUES (?, ?)
            """, (identifier, endpoint))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True

# Make it compatible with PostgresDatabase import
PostgresDatabase = SQLiteDatabase

def get_database() -> SQLiteDatabase:
    """Get or create database instance"""
    return SQLiteDatabase()