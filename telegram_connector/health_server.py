#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Health check server for SoloTrend X Telegram Connector.
Provides endpoints for system health monitoring and debugging.
"""

import os
import logging
import json
from flask import Flask, request, jsonify
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the Flask application
app = Flask(__name__)

@app.route('/health')
def health_check():
    """
    Health check endpoint
    Returns system health status
    """
    logger.info("Health check request received")
    return jsonify({
        'status': 'ok',
        'service': 'telegram_connector'
    })

@app.route('/webhook', methods=['POST'])
def webhook_debug():
    """
    Debug endpoint for testing webhook functionality
    Logs the received payload for debugging
    """
    try:
        data = request.json
        logger.info(f"Webhook debug request received: {data}")
        
        # For debugging, simply acknowledge receipt
        return jsonify({
            'status': 'received',
            'message': 'Webhook data received for debugging',
            'data_summary': {
                'keys': list(data.keys()) if isinstance(data, dict) else None,
                'type': type(data).__name__
            }
        })
    except Exception as e:
        logger.error(f"Error in webhook debug endpoint: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error processing webhook: {str(e)}'
        }), 500

def run_server(port=None):
    """
    Run the health check server
    
    Args:
        port (int, optional): Port to run the server on. Defaults to 5001.
    """
    server_port = port or int(os.environ.get('HEALTH_PORT', 5001))
    
    logger.info(f"Starting Telegram Connector health server on port {server_port}")
    app.run(host='0.0.0.0', port=server_port, debug=False)

if __name__ == '__main__':
    run_server()