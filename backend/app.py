from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# ============================================
# CONFIGURATION
# ============================================

API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")
MODEL_NAME = "nvidia/nemotron-3-super-120b-a12b:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

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
            messages.append(msg)
        
        if not history or history[-1].get('content') != user_message:
            messages.append({'role': 'user', 'content': user_message})
        
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://adichat.vercel.app',
            'X-Title': 'AdiChat'
        }
        
        payload = {
            'model': MODEL_NAME,
            'messages': messages,
            'temperature': 0.7,
            'max_tokens': 1000,
            'top_p': 0.95
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            return jsonify({'response': ai_response})
        else:
            print(f"API Error: {response.status_code}")
            return jsonify({'error': 'AI service unavailable', 'response': 'I apologize, but I am currently unable to process your request. Please try again later.'}), 500
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout', 'response': 'The request took too long. Please try again.'}), 504
    except Exception as e:
        print(f"Server Error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'response': 'An unexpected error occurred.'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'AdiChat API'})

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'service': 'AdiChat API',
        'version': '1.0.0',
        'designer': 'Aditya Arambam'
    })

# ============================================
# VERCEL HANDLER
# ============================================

def handler(request, response):
    return app(request, response)

if __name__ == '__main__':
    print("=" * 50)
    print("AdiChat Backend Server")
    print("Designed by Aditya Arambam")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)