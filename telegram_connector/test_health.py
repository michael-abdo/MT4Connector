"""
Standalone test server for debugging
"""
from flask import Flask

app = Flask(__name__)

@app.route('/health')
def health():
    return {
        'status': 'ok',
        'service': 'test_server'
    }

@app.route('/webhook', methods=['POST'])
def webhook():
    return {
        'status': 'received',
        'message': 'Test webhook server received the signal'
    }

if __name__ == '__main__':
    print("Starting test server on port 5001...")
    app.run(host='0.0.0.0', port=5001)