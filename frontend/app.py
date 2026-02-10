from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import os
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development

# Version for cache busting
APP_VERSION = "3.1.0"

# API base URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

@app.after_request
def add_header(response):
    """Add headers to prevent caching during development"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    response.headers['X-App-Version'] = APP_VERSION
    return response

@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Prevent 404 errors for favicon requests"""
    return '', 204

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({"error": "Only Excel files (.xlsx, .xls) are supported"}), 400
    
    try:
        # Send to API
        files = {'file': (file.filename, file.stream, file.content_type)}
        response = requests.post(f"{API_URL}/api/statements/upload", files=files)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/statements')
def statements():
    """List all statements"""
    try:
        response = requests.get(f"{API_URL}/api/statements/")
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/query', methods=['POST'])
def query():
    """Natural language query with enhanced error handling and logging"""
    data = request.json
    
    # Validate request data
    if not data or 'message' not in data:
        return jsonify({
            "success": False,
            "error": {
                "code": "QUERY_1000",
                "message": "Query message is required",
                "suggestion": "Please provide a query message"
            }
        }), 400
    
    message = data.get('message', '').strip()
    
    # Client-side validation
    if not message:
        return jsonify({
            "success": False,
            "error": {
                "code": "QUERY_1000",
                "message": "Query cannot be empty",
                "suggestion": "Please enter a question about your bank statements"
            }
        }), 400
    
    if len(message) > 500:
        return jsonify({
            "success": False,
            "error": {
                "code": "QUERY_1001",
                "message": "Query is too long",
                "suggestion": "Please shorten your query to less than 500 characters"
            }
        }), 400
    
    # Log request for debugging
    print(f"[QUERY] Received: {message[:100]}...")
    print(f"[QUERY] Account Filter: {data.get('account', 'NONE')}")
    print(f"[QUERY] Statement ID: {data.get('statement_id', 'NONE')}")
    
    try:
        # Set timeout for API request
        timeout_seconds = 30
        
        response = requests.post(
            f"{API_URL}/api/statements/query",
            json={
                "message": message,
                "thread_id": data.get('thread_id'),
                "account": data.get('account'),
                "statement_id": data.get('statement_id')
            },
            timeout=timeout_seconds
        )
        
        # Parse response
        try:
            result = response.json()
        except ValueError:
            print(f"[QUERY] Failed to parse JSON response: {response.text[:200]}")
            return jsonify({
                "success": False,
                "error": {
                    "code": "INTERNAL_5000",
                    "message": "Invalid response from server",
                    "suggestion": "Please try again"
                }
            }), 500
        
        # Log response for debugging
        if result.get('success'):
            txn_count = len(result.get('transactions', []))
            print(f"[QUERY] Response: {txn_count} transactions")
            if result.get('filters_used'):
                print(f"[QUERY] Filters Applied: {result.get('filters_used')}")
            if result.get('metadata', {}).get('fallback_used'):
                print(f"[QUERY] ⚠️ Fallback mode used")
        else:
            error_info = result.get('error', {})
            print(f"[QUERY] Error: {error_info.get('code', 'UNKNOWN')} - {error_info.get('message', 'No message')}")
        
        # Pass through status code
        return jsonify(result), response.status_code
        
    except requests.exceptions.Timeout:
        print(f"[QUERY] Timeout after {timeout_seconds}s")
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVICE_3004",
                "message": "Query took too long to process",
                "suggestion": "Try a simpler query or narrow your search criteria"
            }
        }), 504
        
    except requests.exceptions.ConnectionError as e:
        print(f"[QUERY] Connection Error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVICE_3001",
                "message": "Cannot connect to backend server",
                "suggestion": "Please ensure the backend server is running at " + API_URL
            }
        }), 503
        
    except Exception as e:
        print(f"[QUERY] Error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_5002",
                "message": "An unexpected error occurred",
                "suggestion": "Please try again",
                "details": str(e)
            }
        }), 500

@app.route('/search')
def search():
    """Search transactions"""
    params = request.args.to_dict()
    
    try:
        response = requests.get(f"{API_URL}/api/statements/transactions/search", params=params)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analytics')
def analytics():
    """Get analytics for current account/statement"""
    try:
        # Get current account and statement from session
        account = session.get('currentAccount')
        statement_id = session.get('currentStatementId')
        
        # Build query params
        params = {}
        if statement_id:
            params['statement_id'] = statement_id
        elif account:
            params['account'] = account
        
        # Fetch analytics with filters
        response = requests.get(
            f"{API_URL}/api/statements/analytics/summary",
            params=params
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)
