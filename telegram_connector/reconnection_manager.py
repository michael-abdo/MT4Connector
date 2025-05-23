"""
Automatic reconnection manager for MT4 and Telegram connections.
"""

import os
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Callable

# Configure logging
logger = logging.getLogger(__name__)

class ReconnectionManager:
    """Manages automatic reconnection for services"""
    
    def __init__(self):
        """Initialize reconnection manager"""
        self.reconnect_intervals = [5, 10, 30, 60, 300]  # seconds
        self.max_retries = len(self.reconnect_intervals)
        self.connection_states = {}
        self.retry_counts = {}
        self.last_connection_time = {}
        
    async def monitor_connection(self, 
                               service_name: str,
                               check_function: Callable,
                               reconnect_function: Callable,
                               check_interval: int = 30):
        """Monitor a service connection and reconnect if needed"""
        
        logger.info(f"Starting connection monitor for {service_name}")
        self.connection_states[service_name] = 'unknown'
        self.retry_counts[service_name] = 0
        
        while True:
            try:
                # Check connection status
                is_connected = await self._run_async_or_sync(check_function)
                
                if is_connected:
                    # Connection is good
                    if self.connection_states[service_name] != 'connected':
                        logger.info(f"{service_name} connection established")
                        self.connection_states[service_name] = 'connected'
                        self.retry_counts[service_name] = 0
                        self.last_connection_time[service_name] = datetime.utcnow()
                else:
                    # Connection lost
                    if self.connection_states[service_name] == 'connected':
                        logger.warning(f"{service_name} connection lost")
                    
                    self.connection_states[service_name] = 'disconnected'
                    
                    # Attempt reconnection
                    await self._attempt_reconnection(
                        service_name,
                        reconnect_function
                    )
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring {service_name}: {e}")
                self.connection_states[service_name] = 'error'
                await asyncio.sleep(check_interval)
    
    async def _attempt_reconnection(self, 
                                  service_name: str,
                                  reconnect_function: Callable) -> bool:
        """Attempt to reconnect a service"""
        
        retry_count = self.retry_counts[service_name]
        
        if retry_count >= self.max_retries:
            logger.error(f"{service_name} max reconnection attempts reached")
            await self._send_reconnection_alert(service_name, 'max_retries')
            return False
        
        # Get retry interval
        retry_interval = self.reconnect_intervals[min(retry_count, len(self.reconnect_intervals) - 1)]
        
        logger.info(f"Attempting to reconnect {service_name} (attempt {retry_count + 1}/{self.max_retries}) in {retry_interval}s")
        await asyncio.sleep(retry_interval)
        
        try:
            # Attempt reconnection
            success = await self._run_async_or_sync(reconnect_function)
            
            if success:
                logger.info(f"{service_name} reconnection successful")
                self.connection_states[service_name] = 'connected'
                self.retry_counts[service_name] = 0
                await self._send_reconnection_alert(service_name, 'reconnected')
                return True
            else:
                logger.warning(f"{service_name} reconnection failed")
                self.retry_counts[service_name] += 1
                return False
                
        except Exception as e:
            logger.error(f"Error reconnecting {service_name}: {e}")
            self.retry_counts[service_name] += 1
            return False
    
    async def _run_async_or_sync(self, func: Callable):
        """Run a function whether it's async or sync"""
        if asyncio.iscoroutinefunction(func):
            return await func()
        else:
            return func()
    
    async def _send_reconnection_alert(self, service_name: str, status: str):
        """Send alert about reconnection status"""
        try:
            # Import here to avoid circular dependency
            from telegram_sender import notify_admins_sync
            
            if status == 'max_retries':
                message = (
                    f"🔴 {service_name} Connection Failed\n\n"
                    f"Maximum reconnection attempts reached.\n"
                    f"Manual intervention may be required."
                )
            elif status == 'reconnected':
                downtime = 'unknown'
                if service_name in self.last_connection_time:
                    downtime_delta = datetime.utcnow() - self.last_connection_time[service_name]
                    downtime = str(downtime_delta).split('.')[0]
                
                message = (
                    f"🟢 {service_name} Reconnected\n\n"
                    f"Connection restored successfully.\n"
                    f"Downtime: {downtime}"
                )
            else:
                message = f"ℹ️ {service_name} connection status: {status}"
            
            # Send notification
            notify_admins_sync(message)
            
        except Exception as e:
            logger.error(f"Failed to send reconnection alert: {e}")
    
    def get_connection_status(self) -> dict:
        """Get current connection status for all services"""
        status = {
            'services': {},
            'overall_status': 'healthy'
        }
        
        for service, state in self.connection_states.items():
            service_info = {
                'state': state,
                'retry_count': self.retry_counts.get(service, 0),
                'last_connected': self.last_connection_time.get(service)
            }
            
            if state != 'connected':
                status['overall_status'] = 'degraded'
            
            status['services'][service] = service_info
        
        return status


class MT4ReconnectionHandler:
    """Specific reconnection handler for MT4"""
    
    def __init__(self, mt4_connector):
        """Initialize MT4 reconnection handler"""
        self.mt4 = mt4_connector
        self.manager = ReconnectionManager()
        
    def check_connection(self) -> bool:
        """Check MT4 connection status"""
        try:
            status = self.mt4.get_status()
            return status.get('connected', False)
        except:
            return False
    
    def reconnect(self) -> bool:
        """Attempt to reconnect to MT4"""
        try:
            return self.mt4.check_connection()
        except Exception as e:
            logger.error(f"MT4 reconnection error: {e}")
            return False
    
    async def start_monitoring(self):
        """Start monitoring MT4 connection"""
        await self.manager.monitor_connection(
            'MT4_API',
            self.check_connection,
            self.reconnect,
            check_interval=30
        )


class TelegramReconnectionHandler:
    """Specific reconnection handler for Telegram bot"""
    
    def __init__(self, telegram_bot):
        """Initialize Telegram reconnection handler"""
        self.bot = telegram_bot
        self.manager = ReconnectionManager()
        
    async def check_connection(self) -> bool:
        """Check Telegram bot connection"""
        try:
            if self.bot and hasattr(self.bot, 'get_me'):
                await self.bot.get_me()
                return True
            return False
        except:
            return False
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect Telegram bot"""
        try:
            if self.bot and hasattr(self.bot, 'initialize'):
                await self.bot.initialize()
                return True
            return False
        except Exception as e:
            logger.error(f"Telegram reconnection error: {e}")
            return False
    
    async def start_monitoring(self):
        """Start monitoring Telegram connection"""
        await self.manager.monitor_connection(
            'Telegram_Bot',
            self.check_connection,
            self.reconnect,
            check_interval=60
        )