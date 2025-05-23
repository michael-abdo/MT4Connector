"""
Session management for web interface and API endpoints.
"""

import os
import secrets
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g

# Configure logging
logger = logging.getLogger(__name__)

class SessionManager:
    """Manages user sessions for web interface"""
    
    def __init__(self, database):
        """Initialize session manager with database"""
        self.db = database
        self.session_duration_hours = int(os.environ.get('SESSION_DURATION_HOURS', 24))
    
    def create_session(self, telegram_id: int, ip_address: str = None, 
                      user_agent: str = None) -> str:
        """Create a new session and return the token"""
        try:
            # Generate secure random token
            session_token = secrets.token_urlsafe(32)
            
            # Store in database
            success = self.db.create_session(
                telegram_id=telegram_id,
                session_token=session_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_hours=self.session_duration_hours
            )
            
            if success:
                logger.info(f"Created session for user {telegram_id}")
                return session_token
            else:
                logger.error(f"Failed to create session for user {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    def validate_session(self, session_token: str) -> dict:
        """Validate a session token and return user info"""
        try:
            session = self.db.validate_session(session_token)
            
            if session:
                logger.debug(f"Valid session for user {session['telegram_id']}")
                return session
            else:
                logger.debug("Invalid or expired session token")
                return None
                
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None
    
    def destroy_session(self, session_token: str) -> bool:
        """Destroy a session (logout)"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE session_token = %s
                """, (session_token,))
                
            logger.info("Session destroyed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error destroying session: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE expires_at < CURRENT_TIMESTAMP
                """)
                
                deleted = cursor.rowcount
                
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")

def require_session(f):
    """Decorator to require valid session for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get session token from header or cookie
        session_token = request.headers.get('X-Session-Token') or \
                       request.cookies.get('session_token')
        
        if not session_token:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
        
        # Get database and session manager
        from database_postgres import get_database
        db = get_database()
        session_mgr = SessionManager(db)
        
        # Validate session
        session = session_mgr.validate_session(session_token)
        if not session:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired session'
            }), 401
        
        # Store user info in g for use in route
        g.user = {
            'telegram_id': session['telegram_id'],
            'username': session.get('username'),
            'first_name': session.get('first_name'),
            'last_name': session.get('last_name')
        }
        g.session_token = session_token
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_user():
    """Get current user from g object"""
    return getattr(g, 'user', None)

def get_session_token():
    """Get current session token from g object"""
    return getattr(g, 'session_token', None)