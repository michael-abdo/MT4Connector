"""
Production configuration for SoloTrend X Telegram Connector
"""

import os
from pathlib import Path

# Base configuration
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / 'data'
LOG_DIR = DATA_DIR / 'logs'

# Create directories if they don't exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:password@localhost:5432/solotrendx'
)

# Use PostgreSQL in production
USE_POSTGRES = True

# Session configuration
SESSION_DURATION_HOURS = int(os.environ.get('SESSION_DURATION_HOURS', 24))
SESSION_SECRET_KEY = os.environ.get('SESSION_SECRET_KEY', os.urandom(32).hex())

# Rate limiting configuration
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', 60))
RATE_LIMIT_WINDOW_MINUTES = int(os.environ.get('RATE_LIMIT_WINDOW_MINUTES', 1))

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_ADMIN_IDS = os.environ.get('TELEGRAM_ADMIN_IDS', '').split(',')
TELEGRAM_ALLOWED_USER_IDS = os.environ.get('TELEGRAM_ALLOWED_USER_IDS', '').split(',')

# MT4 API configuration
MT4_API_URL = os.environ.get('MT4_API_URL', 'http://localhost:8000')
MOCK_MODE = os.environ.get('MOCK_MODE', 'False').lower() == 'true'

# Flask configuration
FLASK_ENV = 'production'
DEBUG = False
TESTING = False
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', SESSION_SECRET_KEY)

# Security configuration
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
SECURE_COOKIES = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Logging configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = LOG_DIR / 'production.log'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Health check configuration
HEALTH_CHECK_INTERVAL = int(os.environ.get('HEALTH_CHECK_INTERVAL', 60))
HEALTH_CHECK_TIMEOUT = int(os.environ.get('HEALTH_CHECK_TIMEOUT', 10))

# Monitoring configuration
ENABLE_METRICS = os.environ.get('ENABLE_METRICS', 'True').lower() == 'true'
METRICS_PORT = int(os.environ.get('METRICS_PORT', 9090))

# Alert configuration
ALERT_WEBHOOK_URL = os.environ.get('ALERT_WEBHOOK_URL')
ALERT_EMAIL = os.environ.get('ALERT_EMAIL')
SMTP_HOST = os.environ.get('SMTP_HOST', 'localhost')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

# Cleanup configuration
CLEANUP_INTERVAL_HOURS = int(os.environ.get('CLEANUP_INTERVAL_HOURS', 24))
SESSION_CLEANUP_DAYS = int(os.environ.get('SESSION_CLEANUP_DAYS', 7))
RATE_LIMIT_CLEANUP_DAYS = int(os.environ.get('RATE_LIMIT_CLEANUP_DAYS', 1))
LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', 30))