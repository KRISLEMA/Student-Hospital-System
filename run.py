import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app import app

if __name__ == '__main__':
    #  Correct - binds to all interfaces so Render can detect it
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)