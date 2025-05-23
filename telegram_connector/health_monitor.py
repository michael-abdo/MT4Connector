"""
Health monitoring and reliability features for production deployment.
"""

import os
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import psutil
import aiohttp

# Configure logging
logger = logging.getLogger(__name__)

class HealthMonitor:
    """Monitors system health and component status"""
    
    def __init__(self, database, mt4_connector, telegram_bot=None):
        """Initialize health monitor"""
        self.db = database
        self.mt4 = mt4_connector
        self.bot = telegram_bot
        self.checks = {}
        self.last_check_time = {}
        self.check_interval = int(os.environ.get('HEALTH_CHECK_INTERVAL', 60))
        self.alert_webhook = os.environ.get('ALERT_WEBHOOK_URL')
        
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        start_time = time.time()
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
            # Check database size and connections
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        pg_database_size(current_database()) as db_size,
                        count(*) as connection_count
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """)
                stats = cursor.fetchone()
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'database_size_mb': round(stats['db_size'] / 1024 / 1024, 2),
                'active_connections': stats['connection_count']
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000
            }
    
    async def check_mt4_connection(self) -> Dict[str, Any]:
        """Check MT4 API connectivity"""
        start_time = time.time()
        try:
            status = self.mt4.get_status()
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy' if status.get('connected') else 'degraded',
                'connected': status.get('connected', False),
                'response_time_ms': round(response_time, 2),
                'server': status.get('server', 'Unknown'),
                'account': status.get('account', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"MT4 health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000
            }
    
    async def check_telegram_bot(self) -> Dict[str, Any]:
        """Check Telegram bot status"""
        start_time = time.time()
        try:
            if self.bot and hasattr(self.bot, 'get_me'):
                bot_info = await self.bot.get_me()
                response_time = (time.time() - start_time) * 1000
                
                return {
                    'status': 'healthy',
                    'bot_username': bot_info.username,
                    'bot_id': bot_info.id,
                    'response_time_ms': round(response_time, 2)
                }
            else:
                return {
                    'status': 'unknown',
                    'message': 'Bot instance not available'
                }
                
        except Exception as e:
            logger.error(f"Telegram bot health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Process info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                'status': 'healthy' if cpu_percent < 80 and memory.percent < 80 else 'degraded',
                'cpu_percent': round(cpu_percent, 2),
                'memory_percent': round(memory.percent, 2),
                'memory_used_mb': round(memory.used / 1024 / 1024, 2),
                'memory_available_mb': round(memory.available / 1024 / 1024, 2),
                'disk_percent': round(disk.percent, 2),
                'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                'process_memory_mb': round(process_memory.rss / 1024 / 1024, 2),
                'process_threads': process.num_threads()
            }
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def check_recent_trades(self) -> Dict[str, Any]:
        """Check recent trade execution status"""
        try:
            # Get trade statistics from last hour
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_signals,
                        COUNT(CASE WHEN status = 'executed' THEN 1 END) as executed,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                        AVG(EXTRACT(EPOCH FROM (executed_at - created_at))) as avg_execution_time
                    FROM signal_history
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
                """)
                stats = cursor.fetchone()
            
            success_rate = 0
            if stats['total_signals'] > 0:
                success_rate = (stats['executed'] / stats['total_signals']) * 100
            
            return {
                'status': 'healthy' if success_rate >= 90 else 'degraded',
                'signals_last_hour': stats['total_signals'],
                'executed': stats['executed'],
                'failed': stats['failed'],
                'success_rate': round(success_rate, 2),
                'avg_execution_seconds': round(stats['avg_execution_time'] or 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Trade statistics check failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        # Run all checks concurrently
        check_tasks = {
            'database': self.check_database(),
            'mt4_connection': self.check_mt4_connection(),
            'telegram_bot': self.check_telegram_bot(),
            'system_resources': self.check_system_resources(),
            'recent_trades': self.check_recent_trades()
        }
        
        check_results = await asyncio.gather(
            *check_tasks.values(),
            return_exceptions=True
        )
        
        # Process results
        for (name, _), result in zip(check_tasks.items(), check_results):
            if isinstance(result, Exception):
                results['checks'][name] = {
                    'status': 'error',
                    'error': str(result)
                }
                results['overall_status'] = 'unhealthy'
            else:
                results['checks'][name] = result
                if result.get('status') == 'unhealthy':
                    results['overall_status'] = 'unhealthy'
                elif result.get('status') == 'degraded' and results['overall_status'] == 'healthy':
                    results['overall_status'] = 'degraded'
        
        # Store results
        self.checks = results
        self.last_check_time[datetime.utcnow()] = results
        
        # Send alerts if unhealthy
        if results['overall_status'] == 'unhealthy':
            await self.send_alert(results)
        
        return results
    
    async def send_alert(self, health_data: Dict[str, Any]):
        """Send health alert via webhook or Telegram"""
        try:
            alert_message = f"🚨 System Health Alert\n\n"
            alert_message += f"Status: {health_data['overall_status'].upper()}\n"
            alert_message += f"Time: {health_data['timestamp']}\n\n"
            
            # Add details of failed checks
            for check_name, check_data in health_data['checks'].items():
                if check_data.get('status') in ['unhealthy', 'error']:
                    alert_message += f"❌ {check_name}: {check_data.get('error', 'Failed')}\n"
            
            # Send via webhook if configured
            if self.alert_webhook:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        self.alert_webhook,
                        json={'text': alert_message}
                    )
            
            # Send via Telegram to admins
            if self.bot:
                admin_ids = os.environ.get('TELEGRAM_ADMIN_IDS', '').split(',')
                for admin_id in admin_ids:
                    if admin_id.strip():
                        try:
                            await self.bot.send_message(
                                chat_id=int(admin_id),
                                text=alert_message
                            )
                        except Exception as e:
                            logger.error(f"Failed to send alert to admin {admin_id}: {e}")
            
            logger.warning(f"Health alert sent: {health_data['overall_status']}")
            
        except Exception as e:
            logger.error(f"Failed to send health alert: {e}")
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        logger.info("Starting health monitoring...")
        
        while True:
            try:
                await self.run_all_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current health status"""
        if not self.checks:
            return {
                'status': 'unknown',
                'message': 'No health checks performed yet'
            }
        
        # Add uptime information
        if self.last_check_time:
            first_check = min(self.last_check_time.keys())
            uptime = datetime.utcnow() - first_check
            self.checks['uptime_seconds'] = uptime.total_seconds()
        
        return self.checks