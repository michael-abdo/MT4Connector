"""
PostgreSQL database implementation for production deployment.
Provides the same interface as database.py but uses PostgreSQL.
"""

import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from contextlib import contextmanager
from cryptography.fernet import Fernet

# Configure logging
logger = logging.getLogger(__name__)

class PostgresDatabase:
    """PostgreSQL database implementation for production use"""
    
    def __init__(self, connection_string=None):
        """Initialize PostgreSQL database connection"""
        if connection_string is None:
            # Get from environment or use default
            connection_string = os.environ.get(
                'DATABASE_URL',
                'postgresql://postgres:password@localhost:5432/solotrendx'
            )
        
        self.connection_string = connection_string
        self._encryption_key = self._get_or_create_key()
        self._fernet = Fernet(self._encryption_key)
        
        # Initialize database schema
        self._init_database()
        
    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup"""
        conn = psycopg2.connect(self.connection_string)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @contextmanager
    def get_cursor(self):
        """Get a database cursor with automatic cleanup"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            yield cursor
    
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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        mt4_account INTEGER,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create user settings table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_settings (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        risk_percent REAL DEFAULT 1.0,
                        default_lot_size REAL DEFAULT 0.01,
                        max_lot_size REAL DEFAULT 1.0,
                        auto_trade BOOLEAN DEFAULT FALSE,
                        notifications BOOLEAN DEFAULT TRUE,
                        max_daily_trades INTEGER DEFAULT 10,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                    )
                """)
                
                # Create signal history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS signal_history (
                        id SERIAL PRIMARY KEY,
                        signal_id VARCHAR(255) UNIQUE NOT NULL,
                        telegram_id BIGINT,
                        mt4_account INTEGER,
                        symbol VARCHAR(20),
                        action VARCHAR(20),
                        volume REAL,
                        price REAL,
                        sl REAL,
                        tp REAL,
                        profit REAL,
                        status VARCHAR(20),
                        ticket INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        executed_at TIMESTAMP,
                        closed_at TIMESTAMP,
                        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                    )
                """)
                
                # Create mt4_accounts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mt4_accounts (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT,
                        account_number INTEGER UNIQUE NOT NULL,
                        account_name VARCHAR(255),
                        server VARCHAR(255),
                        encrypted_password TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_default BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP,
                        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                    )
                """)
                
                # Create account_settings table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS account_settings (
                        id SERIAL PRIMARY KEY,
                        account_number INTEGER UNIQUE NOT NULL,
                        risk_percent REAL DEFAULT 1.0,
                        default_lot_size REAL DEFAULT 0.01,
                        max_lot_size REAL DEFAULT 1.0,
                        auto_trade BOOLEAN DEFAULT FALSE,
                        notifications BOOLEAN DEFAULT TRUE,
                        max_daily_trades INTEGER DEFAULT 10,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (account_number) REFERENCES mt4_accounts(account_number) ON DELETE CASCADE
                    )
                """)
                
                # Create sessions table for session management
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT NOT NULL,
                        session_token VARCHAR(255) UNIQUE NOT NULL,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                    )
                """)
                
                # Create API rate limiting table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS api_rate_limits (
                        id SERIAL PRIMARY KEY,
                        identifier VARCHAR(255) NOT NULL,
                        endpoint VARCHAR(255) NOT NULL,
                        request_count INTEGER DEFAULT 1,
                        window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(identifier, endpoint, window_start)
                    )
                """)
                
                # Create indices for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_telegram_id ON signal_history(telegram_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_status ON signal_history(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_created ON signal_history(created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_telegram_id ON mt4_accounts(telegram_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits ON api_rate_limits(identifier, endpoint, window_start)")
                
                logger.info("PostgreSQL database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL database: {e}")
            raise
    
    # Implement all the same methods as database.py
    def register_user(self, telegram_id: int, username: str = None, 
                     first_name: str = None, last_name: str = None,
                     mt4_account: int = None) -> bool:
        """Register a new user"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (telegram_id, username, first_name, last_name, mt4_account)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (telegram_id) 
                    DO UPDATE SET 
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (telegram_id, username, first_name, last_name, mt4_account))
                
                # Create default settings
                cursor.execute("""
                    INSERT INTO user_settings (telegram_id)
                    VALUES (%s)
                    ON CONFLICT (telegram_id) DO NOTHING
                """, (telegram_id,))
                
            logger.info(f"User {telegram_id} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False
    
    def get_user(self, telegram_id: int) -> dict:
        """Get user information"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE telegram_id = %s AND is_active = TRUE
                """, (telegram_id,))
                
                return cursor.fetchone()
                
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_settings(self, telegram_id: int) -> dict:
        """Get user settings"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT risk_percent, default_lot_size, max_lot_size,
                           auto_trade, notifications, max_daily_trades
                    FROM user_settings
                    WHERE telegram_id = %s
                """, (telegram_id,))
                
                settings = cursor.fetchone()
                if settings:
                    return dict(settings)
                
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
            logger.error(f"Error getting user settings: {e}")
            return {}
    
    def update_user_settings(self, telegram_id: int, settings: dict) -> bool:
        """Update user settings"""
        try:
            allowed_fields = [
                'risk_percent', 'default_lot_size', 'max_lot_size',
                'auto_trade', 'notifications', 'max_daily_trades'
            ]
            
            # Build update query
            update_fields = []
            values = []
            for field in allowed_fields:
                if field in settings:
                    update_fields.append(f"{field} = %s")
                    values.append(settings[field])
            
            if not update_fields:
                return True
            
            values.append(telegram_id)
            
            with self.get_cursor() as cursor:
                cursor.execute(f"""
                    UPDATE user_settings 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = %s
                """, values)
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            return False
    
    def add_mt4_account(self, telegram_id: int, account_number: int, 
                       account_name: str, server: str, password: str) -> dict:
        """Add an MT4 account for a user"""
        try:
            # Encrypt password
            encrypted_password = self._fernet.encrypt(password.encode()).decode()
            
            with self.get_cursor() as cursor:
                # Check if this is the first account
                cursor.execute("""
                    SELECT COUNT(*) as count FROM mt4_accounts 
                    WHERE telegram_id = %s AND is_active = TRUE
                """, (telegram_id,))
                
                is_first = cursor.fetchone()['count'] == 0
                
                # Insert account
                cursor.execute("""
                    INSERT INTO mt4_accounts 
                    (telegram_id, account_number, account_name, server, encrypted_password, is_default)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (account_number) 
                    DO UPDATE SET
                        account_name = EXCLUDED.account_name,
                        server = EXCLUDED.server,
                        encrypted_password = EXCLUDED.encrypted_password,
                        is_active = TRUE,
                        last_used = CURRENT_TIMESTAMP
                    RETURNING *
                """, (telegram_id, account_number, account_name, server, encrypted_password, is_first))
                
                account = dict(cursor.fetchone())
                
                # Create default account settings
                cursor.execute("""
                    INSERT INTO account_settings (account_number)
                    VALUES (%s)
                    ON CONFLICT (account_number) DO NOTHING
                """, (account_number,))
                
                return account
                
        except Exception as e:
            logger.error(f"Error adding MT4 account: {e}")
            return None
    
    def get_user_accounts(self, telegram_id: int) -> list:
        """Get all accounts for a user"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, account_number, account_name, server, 
                           is_default, is_active, created_at, last_used
                    FROM mt4_accounts
                    WHERE telegram_id = %s AND is_active = TRUE
                    ORDER BY is_default DESC, last_used DESC
                """, (telegram_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting user accounts: {e}")
            return []
    
    def get_account_credentials(self, account_number: int) -> dict:
        """Get decrypted credentials for an account"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT account_number, server, encrypted_password
                    FROM mt4_accounts
                    WHERE account_number = %s AND is_active = TRUE
                """, (account_number,))
                
                row = cursor.fetchone()
                if row:
                    account = dict(row)
                    # Decrypt password
                    account['password'] = self._fernet.decrypt(
                        account['encrypted_password'].encode()
                    ).decode()
                    del account['encrypted_password']
                    return account
                    
                return None
                
        except Exception as e:
            logger.error(f"Error getting account credentials: {e}")
            return None
    
    # Session management methods
    def create_session(self, telegram_id: int, session_token: str, 
                      ip_address: str = None, user_agent: str = None,
                      expires_hours: int = 24) -> bool:
        """Create a new user session"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_sessions 
                    (telegram_id, session_token, ip_address, user_agent, expires_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '%s hours')
                """, (telegram_id, session_token, ip_address, user_agent, expires_hours))
                
            return True
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    def validate_session(self, session_token: str) -> dict:
        """Validate a session token and return user info"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT s.*, u.username, u.first_name, u.last_name
                    FROM user_sessions s
                    JOIN users u ON s.telegram_id = u.telegram_id
                    WHERE s.session_token = %s 
                    AND s.expires_at > CURRENT_TIMESTAMP
                """, (session_token,))
                
                session = cursor.fetchone()
                if session:
                    # Update last activity
                    cursor.execute("""
                        UPDATE user_sessions 
                        SET last_activity = CURRENT_TIMESTAMP
                        WHERE session_token = %s
                    """, (session_token,))
                    
                    return dict(session)
                    
                return None
                
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None
    
    # Rate limiting methods
    def check_rate_limit(self, identifier: str, endpoint: str, 
                        max_requests: int = 60, window_minutes: int = 1) -> bool:
        """Check if request is within rate limit"""
        try:
            with self.get_cursor() as cursor:
                # Count requests in current window
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM api_rate_limits
                    WHERE identifier = %s 
                    AND endpoint = %s
                    AND window_start > CURRENT_TIMESTAMP - INTERVAL '%s minutes'
                """, (identifier, endpoint, window_minutes))
                
                count = cursor.fetchone()['count']
                
                if count >= max_requests:
                    return False
                
                # Add request to rate limit table
                cursor.execute("""
                    INSERT INTO api_rate_limits (identifier, endpoint)
                    VALUES (%s, %s)
                """, (identifier, endpoint))
                
                return True
                
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old sessions and rate limit data"""
        try:
            with self.get_cursor() as cursor:
                # Clean expired sessions
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE expires_at < CURRENT_TIMESTAMP
                """)
                
                # Clean old rate limit data
                cursor.execute("""
                    DELETE FROM api_rate_limits 
                    WHERE window_start < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """, (days,))
                
                logger.info("Cleaned up old data successfully")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

# Create singleton instance
_db_instance = None

def get_database() -> PostgresDatabase:
    """Get or create PostgreSQL database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = PostgresDatabase()
    return _db_instance