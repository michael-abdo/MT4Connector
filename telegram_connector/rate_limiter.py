"""
API rate limiting for production deployment.
"""

import os
import logging
from functools import wraps
from flask import request, jsonify

# Configure logging
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API endpoints"""
    
    def __init__(self, database):
        """Initialize rate limiter with database"""
        self.db = database
        
        # Default rate limits (can be overridden per endpoint)
        self.default_max_requests = int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', 60))
        self.default_window_minutes = int(os.environ.get('RATE_LIMIT_WINDOW_MINUTES', 1))
    
    def get_identifier(self, request):
        """Get identifier for rate limiting (IP address or user ID)"""
        # Try to get user ID from session
        from session_manager import get_current_user
        user = get_current_user()
        
        if user:
            return f"user_{user['telegram_id']}"
        
        # Fall back to IP address
        # Handle proxied requests
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            ip = request.remote_addr
        
        return f"ip_{ip}"
    
    def check_rate_limit(self, identifier: str, endpoint: str, 
                        max_requests: int = None, window_minutes: int = None) -> bool:
        """Check if request is within rate limit"""
        max_requests = max_requests or self.default_max_requests
        window_minutes = window_minutes or self.default_window_minutes
        
        return self.db.check_rate_limit(
            identifier=identifier,
            endpoint=endpoint,
            max_requests=max_requests,
            window_minutes=window_minutes
        )
    
    def cleanup_old_limits(self):
        """Clean up old rate limit records"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM api_rate_limits 
                    WHERE window_start < CURRENT_TIMESTAMP - INTERVAL '1 day'
                """)
                
                deleted = cursor.rowcount
                
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old rate limit records")
                
        except Exception as e:
            logger.error(f"Error cleaning up rate limits: {e}")

def rate_limit(max_requests: int = None, window_minutes: int = None):
    """Decorator to apply rate limiting to routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get database and rate limiter
            from database_postgres import get_database
            db = get_database()
            limiter = RateLimiter(db)
            
            # Get identifier and endpoint
            identifier = limiter.get_identifier(request)
            endpoint = request.endpoint or request.path
            
            # Check rate limit
            if not limiter.check_rate_limit(
                identifier=identifier,
                endpoint=endpoint,
                max_requests=max_requests,
                window_minutes=window_minutes
            ):
                logger.warning(f"Rate limit exceeded for {identifier} on {endpoint}")
                
                return jsonify({
                    'status': 'error',
                    'message': 'Rate limit exceeded. Please try again later.',
                    'retry_after': window_minutes * 60  # seconds
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

# Common rate limit configurations
def strict_limit(f):
    """Strict rate limit for sensitive operations (10 requests per minute)"""
    return rate_limit(max_requests=10, window_minutes=1)(f)

def standard_limit(f):
    """Standard rate limit (60 requests per minute)"""
    return rate_limit(max_requests=60, window_minutes=1)(f)

def relaxed_limit(f):
    """Relaxed rate limit for read operations (300 requests per minute)"""
    return rate_limit(max_requests=300, window_minutes=1)(f)