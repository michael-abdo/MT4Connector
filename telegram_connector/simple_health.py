"""
Simple standalone health server for Telegram Connector
This server only provides a health check endpoint and doesn't initialize the telegram bot
"""
from flask import Flask, jsonify, request
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    logger.info("Health check endpoint called")
    return jsonify({
        'status': 'ok',
        'service': 'telegram_connector'
    })

@app.route('/webhook', methods=['POST'])
def webhook_proxy():
    """Just to acknowledge webhook requests during testing"""
    import json
    request_data = request.get_json(silent=True) or {}
    logger.info(f"Webhook endpoint called with data: {json.dumps(request_data)}")
    
    return jsonify({
        'status': 'success',
        'message': 'Signal received by health server proxy',
        'data': request_data
    })

if __name__ == '__main__':
    print("Starting Telegram Connector health server on port 5001...")
    logger.info("Starting health server on port 5001")
    
    # Print environment variables for debugging
    import os
    logger.info(f"Environment variables:")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        print(f"Error starting server: {e}")
        import sys
        sys.exit(1)