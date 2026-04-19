from app import app

# Vercel Python entry point

def handler(request, response):
    return app(request, response)