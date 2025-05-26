#!/usr/bin/env python3
"""
MT4 Pumping Mode Example
Demonstrates how to use pumping mode for real-time data streaming
"""

import os
import sys
import asyncio
import logging
import signal
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mt4_real_api import get_mt4_api
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pumping_mode_example.log')
    ]
)

logger = logging.getLogger(__name__)

class PumpingModeExample:
    """Example implementation of pumping mode usage"""
    
    def __init__(self):
        self.api = get_mt4_api()
        self.running = True
        self.quote_count = 0
        self.trade_count = 0
        
    async def quote_callback(self, quote):
        """Callback for quote updates"""
        self.quote_count += 1
        logger.info(f"Quote #{self.quote_count}: {quote.symbol} "
                   f"Bid: {quote.bid} Ask: {quote.ask} "
                   f"Spread: {quote.spread}")
        
    async def trade_callback(self, trade):
        """Callback for trade updates"""
        self.trade_count += 1
        logger.info(f"Trade Update: Order #{trade.order} "
                   f"{trade.symbol} {trade.state} "
                   f"P/L: {trade.profit}")
    
    async def run(self):
        """Main run loop"""
        # Connect to MT4
        logger.info("Connecting to MT4 server...")
        connected = self.api.connect(
            Config.MT4_SERVER,
            Config.MT4_PORT,
            Config.MT4_LOGIN,
            Config.MT4_PASSWORD
        )
        
        if not connected:
            logger.error("Failed to connect to MT4 server")
            return
            
        logger.info("Connected successfully!")
        
        # Start pumping mode
        logger.info("Starting pumping mode...")
        success = await self.api.start_pumping_mode(
            websocket_host='localhost',
            websocket_port=8765
        )
        
        if not success:
            logger.error("Failed to start pumping mode")
            self.api.disconnect()
            return
            
        logger.info("Pumping mode started!")
        logger.info("WebSocket server running on ws://localhost:8765")
        
        # Subscribe to specific symbols
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        for symbol in symbols:
            self.api.subscribe_quotes(symbol, self.quote_callback)
            logger.info(f"Subscribed to {symbol} quotes")
        
        # Subscribe to all trades for a specific login
        if Config.MT4_LOGIN:
            self.api.subscribe_trades(Config.MT4_LOGIN, self.trade_callback)
            logger.info(f"Subscribed to trades for login {Config.MT4_LOGIN}")
        
        # Run until interrupted
        logger.info("Streaming real-time data. Press Ctrl+C to stop...")
        
        try:
            while self.running:
                # Print statistics every 10 seconds
                await asyncio.sleep(10)
                stats = self.api.get_pumping_stats()
                
                logger.info("=== Pumping Statistics ===")
                logger.info(f"Quotes received: {self.quote_count}")
                logger.info(f"Trade updates: {self.trade_count}")
                
                if 'pumping' in stats:
                    pumping_stats = stats['pumping']
                    logger.info(f"Pumping events: {pumping_stats.get('events_received', 0)}")
                    logger.info(f"Pumping errors: {pumping_stats.get('errors', 0)}")
                    
                if 'websocket' in stats:
                    ws_stats = stats['websocket']
                    logger.info(f"WebSocket clients: {ws_stats.get('connected_clients', 0)}")
                    logger.info(f"Messages sent: {ws_stats.get('messages_sent', 0)}")
                    
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            # Clean shutdown
            self.api.stop_pumping_mode()
            self.api.disconnect()
            logger.info("Disconnected from MT4 server")
    
    def stop(self):
        """Stop the example"""
        self.running = False

async def main():
    """Main entry point"""
    example = PumpingModeExample()
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        example.stop()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the example
    await example.run()

if __name__ == "__main__":
    # Run with asyncio
    asyncio.run(main())