"""
Signal Processor module.
Reads signal files from EA and executes them via MT4 Manager API.
"""

import os
import time
import json
import logging
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Adjust imports to work when run from different locations
import sys
from pathlib import Path

# Add the parent directory to sys.path if not already there
src_dir = Path(__file__).parent
root_dir = src_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    # First try importing directly
    from mt4_api import MT4Manager, TradeCommand
    from dx_integration import DXIntegration
    from config import EA_SIGNAL_FILE, SIGNAL_CHECK_INTERVAL
except ImportError:
    # If that fails, try importing from src
    from src.mt4_api import MT4Manager, TradeCommand
    from src.dx_integration import DXIntegration
    from src.config import EA_SIGNAL_FILE, SIGNAL_CHECK_INTERVAL

# Set up logging
logger = logging.getLogger(__name__)

class SignalFileHandler(FileSystemEventHandler):
    """
    Handler for EA signal file changes.
    """
    
    def __init__(self, processor):
        """
        Initialize the signal file handler.
        
        Args:
            processor (SignalProcessor): Signal processor instance
        """
        self.processor = processor
        self.last_modified = 0
    
    def on_modified(self, event):
        """
        Handle file modification events.
        
        Args:
            event (FileModifiedEvent): File modification event
        """
        if not event.is_directory and event.src_path == EA_SIGNAL_FILE:
            # Avoid double processing due to some systems firing multiple events
            current_time = time.time()
            if current_time - self.last_modified > 1:  # Debounce for 1 second
                self.last_modified = current_time
                self.processor.process_signals()

class SignalProcessor:
    """
    Signal Processor class.
    Reads signal files from EA and executes them via MT4 Manager API.
    """
    
    def __init__(self, mt4_api=None, dx_api=None):
        """
        Initialize the signal processor.
        
        Args:
            mt4_api (MT4Manager, optional): MT4 Manager API instance
            dx_api (DXIntegration, optional): DX Integration instance
        """
        self.mt4_api = mt4_api if mt4_api else MT4Manager()
        self.dx_api = dx_api if dx_api else DXIntegration()
        self.connected = False
        self.observer = None
        self.processed_signals = set()  # Track processed signal IDs
        self.last_check_time = 0
        
        logger.info("Signal Processor initialized")
    
    def connect(self, server, port, login, password):
        """
        Connect to MT4 server.
        
        Args:
            server (str): Server IP address
            port (int): Server port
            login (int): Login ID
            password (str): Password
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.mt4_api.connect(server, port):
            logger.error(f"Failed to connect to MT4 server {server}:{port}")
            return False
        
        if not self.mt4_api.login(login, password):
            logger.error(f"Failed to login to MT4 server with login {login}")
            self.mt4_api.disconnect()
            return False
        
        logger.info(f"Successfully connected to MT4 server {server}:{port} with login {login}")
        self.connected = True
        return True
    
    def disconnect(self):
        """
        Disconnect from MT4 server.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        if self.connected:
            result = self.mt4_api.disconnect()
            if result:
                logger.info("Successfully disconnected from MT4 server")
                self.connected = False
            else:
                logger.error("Failed to disconnect from MT4 server")
            
            return result
        
        return True
    
    def start_file_monitoring(self):
        """
        Start monitoring EA signal file for changes.
        
        Returns:
            bool: True if monitoring started, False otherwise
        """
        if self.observer:
            logger.warning("Signal file monitoring already started")
            return False
        
        # Create signal directory if it doesn't exist
        signal_dir = os.path.dirname(EA_SIGNAL_FILE)
        if not os.path.exists(signal_dir):
            os.makedirs(signal_dir)
            
        # Create empty signal file if it doesn't exist
        if not os.path.exists(EA_SIGNAL_FILE):
            with open(EA_SIGNAL_FILE, 'w') as f:
                f.write('[]')
        
        try:
            event_handler = SignalFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, os.path.dirname(EA_SIGNAL_FILE), recursive=False)
            self.observer.start()
            logger.info(f"Started monitoring EA signal file: {EA_SIGNAL_FILE}")
            return True
        except Exception as e:
            logger.error(f"Error starting signal file monitoring: {e}")
            return False
    
    def stop_file_monitoring(self):
        """
        Stop monitoring EA signal file.
        
        Returns:
            bool: True if monitoring stopped, False otherwise
        """
        if not self.observer:
            return True
        
        try:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped monitoring EA signal file")
            return True
        except Exception as e:
            logger.error(f"Error stopping signal file monitoring: {e}")
            return False
    
    def check_signal_file(self):
        """
        Check EA signal file for new signals.
        
        Returns:
            bool: True if check successful, False otherwise
        """
        # Rate limit checks to avoid excessive file operations
        current_time = time.time()
        if current_time - self.last_check_time < SIGNAL_CHECK_INTERVAL:
            return True
        
        self.last_check_time = current_time
        
        try:
            if not os.path.exists(EA_SIGNAL_FILE):
                logger.warning(f"Signal file not found: {EA_SIGNAL_FILE}")
                return False
            
            # Process the signal file
            self.process_signals()
            return True
        except Exception as e:
            logger.error(f"Error checking signal file: {e}")
            return False
    
    def process_signals(self):
        """
        Process signals from EA signal file.
        
        Returns:
            int: Number of signals processed
        """
        if not self.connected:
            logger.error("Not connected to MT4 server")
            return 0
        
        processed_count = 0
        
        try:
            # Read signal file
            with open(EA_SIGNAL_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return 0
                
                try:
                    signals = json.loads(content)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in signal file: {EA_SIGNAL_FILE}")
                    return 0
            
            # Process each signal
            for signal in signals:
                # Skip if already processed
                signal_id = signal.get('id')
                if not signal_id or signal_id in self.processed_signals:
                    continue
                
                # Process the signal
                if self.execute_signal(signal):
                    self.processed_signals.add(signal_id)
                    processed_count += 1
                    print(f"🔄 Total signals processed: {processed_count}")
                
                # Keep processed signals list manageable
                if len(self.processed_signals) > 1000:
                    # Only keep the most recent 500 signal IDs
                    self.processed_signals = set(list(self.processed_signals)[-500:])
            
            return processed_count
        except Exception as e:
            logger.error(f"Error processing signals: {e}")
            return 0
    
    def execute_signal(self, signal):
        """
        Execute a trading signal.
        
        Args:
            signal (dict): Signal details
            
        Returns:
            bool: True if execution successful, False otherwise
        """
        try:
            signal_type = signal.get('type', '').lower()
            symbol = signal.get('symbol', '')
            login = signal.get('login', 0)
            volume = signal.get('volume', 0.1)
            
            # Print signal detection to console
            print(f"\n🔔 New signal detected: {signal_type.upper()} {symbol} {volume} lots")
            
            if not symbol or not login:
                logger.error(f"Invalid signal: Missing symbol or login. Signal: {signal}")
                print(f"❌ Invalid signal: Missing symbol or login")
                return False
            
            # Get current price for the symbol
            symbol_info = self.mt4_api.get_symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Failed to get symbol info for {symbol}")
                print(f"❌ Failed to get symbol info for {symbol}")
                return False
            
            # Determine command and price based on signal type
            cmd = None
            price = 0
            sl = signal.get('sl', 0)
            tp = signal.get('tp', 0)
            
            if signal_type == 'buy':
                cmd = TradeCommand.OP_BUY
                price = symbol_info["ask"]
            elif signal_type == 'sell':
                cmd = TradeCommand.OP_SELL
                price = symbol_info["bid"]
            elif signal_type == 'buy_limit':
                cmd = TradeCommand.OP_BUY_LIMIT
                price = signal.get('price', 0)
            elif signal_type == 'sell_limit':
                cmd = TradeCommand.OP_SELL_LIMIT
                price = signal.get('price', 0)
            elif signal_type == 'buy_stop':
                cmd = TradeCommand.OP_BUY_STOP
                price = signal.get('price', 0)
            elif signal_type == 'sell_stop':
                cmd = TradeCommand.OP_SELL_STOP
                price = signal.get('price', 0)
            elif signal_type == 'close':
                # Find the order by ticket
                order_ticket = signal.get('ticket', 0)
                if order_ticket > 0:
                    return self.mt4_api.close_order(login, order_ticket)
                else:
                    logger.error(f"Invalid close signal: Missing ticket. Signal: {signal}")
                    return False
            else:
                logger.error(f"Unknown signal type: {signal_type}")
                return False
            
            # Execute the trade
            if cmd is not None:
                signal_id = signal.get('id', 'unknown')
                comment = signal.get('comment', f"Signal:{signal_id}")
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
                
                if order_ticket > 0:
                    logger.info(f"Successfully executed signal: {signal_type} {symbol} @ {price}, Ticket: {order_ticket}")
                    print(f"✅ Order executed: {signal_type.upper()} {symbol} @ {price}, Ticket: {order_ticket}")
                    if sl > 0 or tp > 0:
                        print(f"   SL: {sl}, TP: {tp}")
                    return True
                else:
                    logger.error(f"Failed to execute signal: {signal_type} {symbol} @ {price}")
                    print(f"❌ Failed to execute order: {signal_type.upper()} {symbol} @ {price}")
                    return False
            
            return False
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            print(f"❌ Error executing signal: {e}")
            return False
    
    def run(self):
        """
        Run the signal processor main loop.
        """
        if not self.connected:
            logger.error("Not connected to MT4 server")
            return
        
        try:
            # Start file monitoring
            self.start_file_monitoring()
            
            logger.info("Signal processor running, waiting for EA signals...")
            
            # Initial check for any existing signals
            self.check_signal_file()
            
            # Keep the main thread alive
            while self.connected:
                # Periodically check for signals
                self.check_signal_file()
                time.sleep(SIGNAL_CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Signal processor stopped by user")
        except Exception as e:
            logger.error(f"Error in signal processor: {e}")
        finally:
            self.stop_file_monitoring()
            self.disconnect()
            logger.info("Signal processor stopped")