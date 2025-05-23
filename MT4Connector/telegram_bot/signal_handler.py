"""
Telegram Signal Handler for MT4 Signal Connector.
Handles integration between the MT4 signal processor and Telegram bot.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from threading import Thread
import queue

from .bot import TelegramBot

# Set up logging
logger = logging.getLogger(__name__)

class TelegramSignalHandler:
    """
    Handles integration between MT4 signal processor and Telegram bot.
    Processes incoming trading signals and sends them to Telegram for approval.
    """
    
    def __init__(self, telegram_bot: TelegramBot, mt4_api=None, signal_file: str = "", auto_execute: bool = False):
        """
        Initialize the Telegram signal handler.
        
        Args:
            telegram_bot (TelegramBot): Telegram bot instance
            mt4_api: MT4 API instance for executing trades
            signal_file (str, optional): Path to the EA signal file
            auto_execute (bool, optional): Whether to automatically execute signals without approval
        """
        self.telegram_bot = telegram_bot
        self.mt4_api = mt4_api
        self.signal_file = signal_file
        self.auto_execute = auto_execute
        self.pending_signals = {}  # Storage for signals pending approval
        self.processed_signal_ids = set()  # Track processed signal IDs
        self.running = False
        self.polling_thread = None
        self.signal_queue = queue.Queue()
        
        # Register signal handlers
        self.telegram_bot.register_signal_handler(self._on_signal_response)
        
        logger.info("Telegram signal handler initialized")
    
    def start(self):
        """
        Start monitoring for signals.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.running:
            logger.warning("Signal handler is already running")
            return False
        
        try:
            self.running = True
            
            # Start the polling thread if a signal file is provided
            if self.signal_file:
                self.polling_thread = Thread(target=self._poll_signal_file, daemon=True)
                self.polling_thread.start()
                logger.info(f"Started polling signal file: {self.signal_file}")
            
            # Start processing the signal queue
            Thread(target=self._process_signal_queue, daemon=True).start()
            
            return True
        except Exception as e:
            logger.error(f"Error starting signal handler: {e}")
            self.running = False
            return False
    
    def stop(self):
        """
        Stop monitoring for signals.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        if not self.running:
            logger.warning("Signal handler is not running")
            return False
        
        try:
            self.running = False
            
            # Wait for the polling thread to stop if it exists
            if self.polling_thread and self.polling_thread.is_alive():
                self.polling_thread.join(timeout=2.0)
            
            logger.info("Signal handler stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping signal handler: {e}")
            return False
    
    def process_signal(self, signal: Dict[str, Any]):
        """
        Process a trading signal.
        
        Args:
            signal (dict): Trading signal details
            
        Returns:
            bool: True if signal processed successfully, False otherwise
        """
        try:
            signal_id = signal.get('id')
            
            # Skip if already processed
            if signal_id in self.processed_signal_ids:
                logger.debug(f"Signal {signal_id} already processed, skipping")
                return False
            
            # Add to pending signals
            self.pending_signals[signal_id] = signal
            
            # Add to the signal queue for processing
            self.signal_queue.put(signal)
            
            return True
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return False
    
    def _process_signal_queue(self):
        """
        Process signals from the queue in a background thread.
        """
        while True:
            try:
                if not self.running:
                    break
                
                try:
                    signal = self.signal_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the signal
                self._handle_signal(signal)
                
                # Mark the task as done
                self.signal_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in signal queue processing: {e}")
                time.sleep(1.0)  # Avoid tight loop in case of repeated errors
    
    def _handle_signal(self, signal: Dict[str, Any]):
        """
        Handle a trading signal from the queue.
        
        Args:
            signal (dict): Trading signal details
        """
        try:
            signal_id = signal.get('id')
            
            if not signal_id:
                logger.error("Signal missing ID, cannot process")
                return
            
            # If auto-execute is enabled, skip Telegram approval
            if self.auto_execute:
                self._execute_signal(signal)
                self.processed_signal_ids.add(signal_id)
                return
            
            # Send the signal to Telegram for approval
            sent = self.telegram_bot.send_trading_signal(signal)
            
            if sent > 0:
                logger.info(f"Signal {signal_id} sent to Telegram for approval")
            else:
                logger.warning(f"No recipients received signal {signal_id}")
                
                # If we couldn't send to Telegram but have MT4 API, execute anyway
                if self.mt4_api:
                    logger.info(f"Auto-executing signal {signal_id} as fallback")
                    self._execute_signal(signal)
                    
            # Mark as processed to avoid duplicate processing
            self.processed_signal_ids.add(signal_id)
            
            # Keep processed signals list manageable
            if len(self.processed_signal_ids) > 1000:
                # Only keep the most recent 500 signal IDs
                self.processed_signal_ids = set(list(self.processed_signal_ids)[-500:])
                
        except Exception as e:
            logger.error(f"Error handling signal: {e}")
    
    def _poll_signal_file(self):
        """
        Poll the EA signal file for new signals in a background thread.
        """
        last_modified_time = 0
        
        while self.running:
            try:
                # Check if file exists
                if not os.path.exists(self.signal_file):
                    time.sleep(1.0)
                    continue
                
                # Check if file has been modified
                current_modified_time = os.path.getmtime(self.signal_file)
                if current_modified_time <= last_modified_time:
                    time.sleep(1.0)
                    continue
                
                # File has been modified, read and process signals
                with open(self.signal_file, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        last_modified_time = current_modified_time
                        time.sleep(1.0)
                        continue
                        
                    try:
                        signals = json.loads(content)
                        
                        # Process each signal if it's an array
                        if isinstance(signals, list):
                            for signal in signals:
                                self.process_signal(signal)
                        # Process single signal if it's a dict    
                        elif isinstance(signals, dict):
                            self.process_signal(signals)
                            
                        last_modified_time = current_modified_time
                        
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in signal file: {self.signal_file}")
                
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error polling signal file: {e}")
                time.sleep(5.0)  # Longer delay in case of error
    
    def _on_signal_response(self, signal_id: str, action: str):
        """
        Handle response from Telegram bot for a signal.
        
        Args:
            signal_id (str): Signal ID
            action (str): Response action (approve, reject)
        """
        try:
            # Get the signal from pending signals
            signal = self.pending_signals.get(signal_id)
            if not signal:
                logger.warning(f"Signal {signal_id} not found in pending signals")
                return
            
            if action == "approve":
                # Execute the approved signal
                if self.mt4_api:
                    self._execute_signal(signal)
                    logger.info(f"Signal {signal_id} approved and executed")
                else:
                    logger.warning(f"Signal {signal_id} approved but MT4 API not available")
            elif action == "reject":
                logger.info(f"Signal {signal_id} rejected by user")
            
            # Remove from pending signals
            self.pending_signals.pop(signal_id, None)
            
        except Exception as e:
            logger.error(f"Error processing signal response: {e}")
    
    def _execute_signal(self, signal: Dict[str, Any]):
        """
        Execute a trading signal.
        
        Args:
            signal (dict): Trading signal details
            
        Returns:
            bool: True if executed successfully, False otherwise
        """
        if not self.mt4_api:
            logger.error("MT4 API not available for signal execution")
            return False
        
        try:
            signal_type = signal.get('type', '').lower()
            symbol = signal.get('symbol', '')
            login = signal.get('login', 0)
            volume = signal.get('volume', 0.1)
            price = signal.get('price', 0)
            sl = signal.get('sl', 0)
            tp = signal.get('tp', 0)
            comment = signal.get('comment', '')
            ticket = signal.get('ticket', 0)
            
            # Execute based on signal type
            result = False
            
            if signal_type in ['buy', 'sell', 'buy_limit', 'sell_limit', 'buy_stop', 'sell_stop']:
                # Place new order
                # Translate signal type to MT4 command
                from mt4_api import TradeCommand
                
                cmd_map = {
                    'buy': TradeCommand.OP_BUY,
                    'sell': TradeCommand.OP_SELL,
                    'buy_limit': TradeCommand.OP_BUY_LIMIT,
                    'sell_limit': TradeCommand.OP_SELL_LIMIT,
                    'buy_stop': TradeCommand.OP_BUY_STOP,
                    'sell_stop': TradeCommand.OP_SELL_STOP
                }
                
                cmd = cmd_map.get(signal_type)
                if cmd is None:
                    logger.error(f"Unknown signal type: {signal_type}")
                    return False
                
                # Place the order
                order_ticket = self.mt4_api.place_order(
                    login=login,
                    symbol=symbol,
                    cmd=cmd,
                    volume=volume,
                    price=price,
                    sl=sl,
                    tp=tp,
                    comment=comment
                )
                
                result = order_ticket > 0
                
            elif signal_type == 'close':
                # Close an existing order
                if ticket > 0:
                    result = self.mt4_api.close_order(login, ticket)
                else:
                    logger.error(f"Close signal missing ticket number")
                    return False
                    
            elif signal_type == 'modify':
                # Modify an existing order
                if ticket > 0:
                    result = self.mt4_api.modify_order(login, ticket, price, sl, tp)
                else:
                    logger.error(f"Modify signal missing ticket number")
                    return False
            
            if result:
                logger.info(f"Successfully executed signal: {signal_type} {symbol}")
                return True
            else:
                logger.error(f"Failed to execute signal: {signal_type} {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return False