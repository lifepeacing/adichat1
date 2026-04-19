from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# ============================================
# CONFIGURATION - GROQ (FREE)
# ============================================

API_KEY = "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"
MODEL_NAME = "llama-3.3-70b-versatile"
API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are AdiChat, a professional and helpful AI assistant created by Aditya Arambam.
Your responses should be clear, concise, professional, and helpful.
Maintain a courteous tone at all times. Do not use emojis.
If you don't know something, be honest and suggest where the user might find the answer."""

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        history = data.get('history', [])
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        
        for msg in history[-10:]:
            messages.append({'role': msg.get('role', 'user'), 'content': msg.get('content', '')})
        
        messages.append({'role': 'user', 'content': user_message})
        
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': MODEL_NAME,
            'messages': messages,
            'temperature': 0.7,
            'max_completion_tokens': 1000,
            'top_p': 0.95
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            return jsonify({'response': ai_response})
        else:
            print(f"API Error {response.status_code}: {response.text}")
            return jsonify({
                'error': 'AI service unavailable', 
                'response': 'I apologize, but I am currently unable to process your request. Please try again later.'
            }), 500
            
    except Exception as e:
        print(f"Server Error: {str(e)}")
        return jsonify({
            'error': 'Internal server error', 
            'response': 'An unexpected error occurred.'
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'AdiChat API'})

@app.route('/api/test', methods=['GET'])
def test():
    try:
        headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
        payload = {
            'model': MODEL_NAME,
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'Say "OK"'}
            ],
            'max_completion_tokens': 10
        }
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'status': response.status_code,
                'model': MODEL_NAME,
                'response': result['choices'][0]['message']['content']
            })
        else:
            return jsonify({'status': response.status_code, 'error': response.text})
    except Exception as e:
        return jsonify({'error': str(e)})

def handler(request, response):
    return app(request, response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)