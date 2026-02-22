#!/usr/bin/env python3
"""
Bird Camera Web Viewer
View live stream and browse captured photos/videos
"""

from flask import Flask

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

from routes.pages import pages
from routes.api import api

app = Flask(__name__)
app.register_blueprint(pages)
app.register_blueprint(api)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🐦 Bird Camera Web Viewer")
    print("="*50)
    print("\nStarting web server...")
    print("Open browser and go to: http://localhost:5000")
    print("Or from another device: http://[PI_IP_ADDRESS]:5000")
    print("\nPress Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)