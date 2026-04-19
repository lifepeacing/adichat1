from http.server import BaseHTTPRequestHandler
import json
import requests
import os

# Configuration - Set these in Vercel Environment Variables
API_KEY = os.environ.get('OPENROUTER_API_KEY', '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')
MODEL_NAME = os.environ.get('MODEL_NAME', 'nvidia/nemotron-3-super-120b-a12b:free')
SYSTEM_PROMPT = """You are a helpful AI assistant created by Aditya Arambam. 
Be professional, concise, and accurate in your responses."""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            user_message = data.get('message', '').strip()
            
            if not user_message:
                self.send_error_response(400, 'No message provided')
                return
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://adichat.vercel.app",
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
                self.send_error_response(500, f'API Error: {response.status_code}')
                return
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            self.send_json_response(200, {'response': ai_response})
            
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_error_response(self, status_code, message):
        self.send_json_response(status_code, {'error': message})