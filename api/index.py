from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import sys
import json  # This was missing!

app = Flask(__name__)

# Enable CORS for all origins
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
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
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    
    try:
        if not API_KEY:
            response = jsonify({'error': 'API key not configured'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500
        
        data = request.get_json(force=True, silent=True) or {}
        user_message = data.get('message', '').strip()
        
        if not user_message:
            response = jsonify({'error': 'No message provided'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
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
        
        api_response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if api_response.status_code != 200:
            response = jsonify({'error': f'AI service error: {api_response.status_code}'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 502
        
        result = api_response.json()
        ai_response = result['choices'][0]['message']['content']
        
        response = jsonify({'response': ai_response.strip()})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except requests.exceptions.Timeout:
        response = jsonify({'error': 'Request timed out'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 504
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/api/health', methods=['GET'])
def health():
    response = jsonify({
        'status': 'ok',
        'model': MODEL_NAME,
        'api_configured': bool(API_KEY)
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# For Vercel serverless
def handler(event, context):
    from io import BytesIO
    import urllib.parse
    
    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    body = event.get('body') or ''
    
    if event.get('isBase64Encoded'):
        import base64
        body = base64.b64decode(body)
    elif isinstance(body, str):
        body = body.encode('utf-8')
    
    # Build query string
    query_params = event.get('queryStringParameters') or {}
    query_string = urllib.parse.urlencode(query_params)
    
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
    
    for key, value in headers.items():
        if key not in ['content-type', 'content-length', 'host']:
            environ[f'HTTP_{key.upper().replace("-", "_")}'] = value
    
    response_body = BytesIO()
    response_started = []
    
    def start_response(status, response_headers):
        response_started.append((status, response_headers))
        return lambda x: None
    
    try:
        result = app(environ, start_response)
        for data in result:
            if data:
                response_body.write(data)
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})  # Now json is defined!
        }
    
    status_code = int(response_started[0][0].split(' ')[0])
    headers_dict = {k: v for k, v in response_started[0][1]}
    
    return {
        'statusCode': status_code,
        'headers': headers_dict,
        'body': response_body.getvalue().decode('utf-8')
    }