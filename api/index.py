from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Configuration
API_KEY = os.environ.get('OPENROUTER_API_KEY', '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')
MODEL_NAME = os.environ.get('MODEL_NAME', 'nvidia/nemotron-3-super-120b-a12b:free')
SYSTEM_PROMPT = """You are a helpful AI assistant created by Aditya Arambam. 
Be professional, concise, and accurate in your responses."""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    
    try:
        data = request.get_json()
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
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
        
        result = response.json()
        ai_response = result['choices'][0]['message']['content']
        
        resp = jsonify({'response': ai_response})
        resp.headers.add('Access-Control-Allow-Origin', '*')
        return resp
        
    except Exception as e:
        resp = jsonify({'error': str(e)})
        resp.headers.add('Access-Control-Allow-Origin', '*')
        return resp, 500

# Vercel serverless handler
def handler(event, context):
    from werkzeug.serving import run_wsgi
    from io import BytesIO
    import json as json_lib
    
    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    headers = event.get('headers', {})
    body = event.get('body', '') or ''
    
    if isinstance(body, str):
        body = body.encode('utf-8')
    
    environ = {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': '',
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
    
    response_body = BytesIO()
    
    def start_response(status, response_headers):
        response_body.write(f"HTTP/1.1 {status}\r\n".encode())
        for header, value in response_headers:
            response_body.write(f"{header}: {value}\r\n".encode())
        response_body.write(b"\r\n")
    
    result = app(environ, start_response)
    for data in result:
        response_body.write(data)
    
    response_body.seek(0)
    raw_response = response_body.read()
    
    # Parse HTTP response
    header_end = raw_response.find(b'\r\n\r\n')
    headers_raw = raw_response[:header_end].decode('utf-8')
    body_content = raw_response[header_end + 4:]
    
    status_line = headers_raw.split('\r\n')[0]
    status_code = int(status_line.split(' ')[1])
    
    response_headers = {}
    for line in headers_raw.split('\r\n')[1:]:
        if ':' in line:
            key, value = line.split(':', 1)
            response_headers[key.strip()] = value.strip()
    
    return {
        'statusCode': status_code,
        'headers': response_headers,
        'body': body_content.decode('utf-8')
    }