from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json
import sys

app = Flask(__name__)

# Enable CORS for all origins
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": False
    }
})

# Configuration
API_KEY = os.environ.get('OPENROUTER_API_KEY', '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')
MODEL_NAME = os.environ.get('MODEL_NAME', 'nvidia/nemotron-3-super-120b-a12b:free')
SYSTEM_PROMPT = """You are a helpful AI assistant created by Aditya Arambam. 
Be professional, concise, and accurate in your responses."""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Accept')
        response.headers.add('Access-Control-Max-Age', '86400')
        return response, 200
    
    try:
        # Log request for debugging
        print(f"Received request: {request.method}", file=sys.stderr)
        
        # Check if we have API key
        if not API_KEY:
            print("ERROR: No API key configured", file=sys.stderr)
            response = jsonify({'error': 'Server configuration error: API key missing'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500
        
        # Parse JSON body
        try:
            data = request.get_json(force=True, silent=True) or {}
        except Exception as e:
            print(f"JSON parse error: {e}", file=sys.stderr)
            data = {}
        
        user_message = data.get('message', '').strip()
        
        if not user_message:
            response = jsonify({'error': 'No message provided'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        print(f"Processing message: {user_message[:50]}...", file=sys.stderr)
        
        # Prepare API request
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": request.headers.get('Origin', 'https://adichat.vercel.app'),
            "X-Title": "AdiChat AI"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Make request to OpenRouter
        try:
            api_response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
        except requests.exceptions.Timeout:
            print("API request timed out", file=sys.stderr)
            response = jsonify({'error': 'AI service is taking too long. Please try again.'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 504
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {e}", file=sys.stderr)
            response = jsonify({'error': 'Cannot connect to AI service. Check your internet.'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 502
        
        # Check API response status
        if api_response.status_code != 200:
            error_detail = api_response.text[:200]
            print(f"API error {api_response.status_code}: {error_detail}", file=sys.stderr)
            response = jsonify({'error': f'AI service error ({api_response.status_code}). Please try again.'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 502
        
        # Parse response
        try:
            result = api_response.json()
            ai_response = result['choices'][0]['message']['content']
            
            if not ai_response or not ai_response.strip():
                response = jsonify({'error': 'AI returned empty response'})
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 500
            
            print(f"Success: Got response length {len(ai_response)}", file=sys.stderr)
            
            response = jsonify({'response': ai_response.strip()})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
            
        except (KeyError, IndexError) as e:
            print(f"Response parsing error: {e}", file=sys.stderr)
            response = jsonify({'error': 'Invalid response from AI service'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500
            
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        response = jsonify({'error': f'Server error: {str(e)}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    response = jsonify({
        'status': 'ok',
        'model': MODEL_NAME,
        'api_key_configured': bool(API_KEY)
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# Vercel handler
def handler(event, context):
    from io import BytesIO
    from urllib.parse import urlencode
    
    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    query_params = event.get('queryStringParameters') or {}
    body = event.get('body') or ''
    
    # Decode base64 body if needed
    if event.get('isBase64Encoded'):
        import base64
        body = base64.b64decode(body)
    elif isinstance(body, str):
        body = body.encode('utf-8')
    
    # Build query string
    query_string = urlencode(query_params) if query_params else ''
    
    # Create WSGI environ
    environ = {
        'REQUEST_METHOD': method,
        'SCRIPT_NAME': '',
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'SERVER_NAME': headers.get('host', 'vercel.com'),
        'SERVER_PORT': '443',
        'HTTP_HOST': headers.get('host', 'vercel.com'),
        'CONTENT_TYPE': headers.get('content-type', ''),
        'CONTENT_LENGTH': str(len(body)),
        'wsgi.input': BytesIO(body),
        'wsgi.errors': sys.stderr,
        'wsgi.url_scheme': 'https',
        'wsgi.version': (1, 0),
        'wsgi.run_once': True,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
    }
    
    # Add headers
    for key, value in headers.items():
        if key not in ['content-type', 'content-length', 'host']:
            environ[f'HTTP_{key.upper().replace("-", "_")}'] = value
    
    # Capture response
    response_status = [None]
    response_headers = [None]
    response_body = BytesIO()
    
    def start_response(status, headers):
        response_status[0] = status
        response_headers[0] = headers
        return lambda x: None
    
    # Execute Flask app
    try:
        result = app(environ, start_response)
        for data in result:
            if data:
                response_body.write(data)
    except Exception as e:
        print(f"WSGI error: {e}", file=sys.stderr)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Internal server error'})
        }
    
    # Parse status
    status_code = int(response_status[0].split(' ')[0])
    
    # Convert headers to dict
    headers_dict = {}
    for key, value in response_headers[0]:
        headers_dict[key] = value
    
    # Ensure CORS header is present
    if 'Access-Control-Allow-Origin' not in headers_dict:
        headers_dict['Access-Control-Allow-Origin'] = '*'
    
    return {
        'statusCode': status_code,
        'headers': headers_dict,
        'body': response_body.getvalue().decode('utf-8')
    }