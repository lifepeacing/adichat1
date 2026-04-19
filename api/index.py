from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)

# Enable CORS for all origins with proper settings
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False
    }
})

# Configuration
API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
MODEL_NAME = os.environ.get('MODEL_NAME', 'nvidia/nemotron-3-super-120b-a12b:free')
SYSTEM_PROMPT = """You are a helpful AI assistant created by Aditya Arambam. 
Be professional, concise, and accurate in your responses."""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Max-Age', '86400')
        return response
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        if not API_KEY:
            return jsonify({'error': 'API key not configured'}), 500
        
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
            ]
        }
        
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            error_text = response.text[:200]
            return jsonify({'error': f'API Error {response.status_code}: {error_text}'}), 500
        
        result = response.json()
        ai_response = result['choices'][0]['message']['content']
        
        resp = jsonify({'response': ai_response})
        resp.headers.add('Access-Control-Allow-Origin', '*')
        return resp
        
    except requests.exceptions.Timeout:
        resp = jsonify({'error': 'Request timed out'})
        resp.headers.add('Access-Control-Allow-Origin', '*')
        return resp, 504
    except requests.exceptions.RequestException as e:
        resp = jsonify({'error': f'Network error: {str(e)}'})
        resp.headers.add('Access-Control-Allow-Origin', '*')
        return resp, 500
    except Exception as e:
        resp = jsonify({'error': f'Server error: {str(e)}'})
        resp.headers.add('Access-Control-Allow-Origin', '*')
        return resp, 500

@app.route('/api/health', methods=['GET'])
def health():
    resp = jsonify({'status': 'ok', 'model': MODEL_NAME})
    resp.headers.add('Access-Control-Allow-Origin', '*')
    return resp

# Vercel serverless handler
def handler(event, context):
    from werkzeug.serving import run_wsgi
    from io import BytesIO
    
    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    body = event.get('body', '') or ''
    
    if isinstance(body, str):
        body = body.encode('utf-8')
    
    environ = {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': event.get('queryStringParameters', '') or '',
        'SERVER_NAME': 'vercel',
        'SERVER_PORT': '443',
        'HTTP_HOST': headers.get('host', 'vercel.com'),
        'CONTENT_TYPE': headers.get('content-type', ''),
        'CONTENT_LENGTH': str(len(body)),
        'wsgi.input': BytesIO(body),
        'wsgi.errors': BytesIO(),
        'wsgi.url_scheme': 'https',
        'wsgi.version': (1, 0),
        'wsgi.run_once': True,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
    }
    
    # Add other HTTP headers
    for key, value in headers.items():
        if key not in ['content-type', 'content-length', 'host']:
            environ[f'HTTP_{key.upper().replace("-", "_")}'] = value
    
    response_body = BytesIO()
    response_started = []
    
    def start_response(status, response_headers):
        response_started.append((status, response_headers))
        return lambda x: None
    
    result = app(environ, start_response)
    for data in result:
        response_body.write(data)
    
    status, response_headers = response_started[0]
    status_code = int(status.split(' ')[0])
    
    response_headers_dict = {k: v for k, v in response_headers}
    
    return {
        'statusCode': status_code,
        'headers': response_headers_dict,
        'body': response_body.getvalue().decode('utf-8')
    }