#!/usr/bin/env python3
"""
Bird Camera Web Viewer
View live stream and browse captured photos/videos
"""

from flask import Flask, render_template_string, Response, send_from_directory
import cv2
import os
from datetime import datetime

# Configuration
OUTPUT_DIR = "media"
CAMERA_INDEX = 0

app = Flask(__name__)

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bird Camera Viewer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f0f0f0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .live-feed {
            width: 100%;
            max-width: 800px;
            border: 2px solid #ddd;
            border-radius: 5px;
            margin: 20px 0;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .gallery-item {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            background: #fafafa;
        }
        .gallery-item img {
            width: 100%;
            border-radius: 5px;
            cursor: pointer;
        }
        .gallery-item img:hover {
            opacity: 0.8;
        }
        .filename {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            word-break: break-all;
        }
        .stats {
            background: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .stats p {
            margin: 5px 0;
            color: #2e7d32;
        }
        .refresh-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .refresh-btn:hover {
            background: #45a049;
        }
        video {
            width: 100%;
            max-width: 400px;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐦 Bird Camera Viewer</h1>
        
        <div class="stats">
            <p><strong>📊 Statistics</strong></p>
            <p>Total Photos: {{ photo_count }}</p>
            <p>Total Videos: {{ video_count }}</p>
            <p>Last Update: {{ current_time }}</p>
        </div>
        
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Gallery</button>
        
        <h2>📹 Live Stream</h2>
        <img src="{{ url_for('video_feed') }}" class="live-feed" alt="Live Camera Feed">
        
        <h2>📸 Captured Photos</h2>
        {% if photos %}
        <div class="gallery">
            {% for photo in photos %}
            <div class="gallery-item">
                <a href="{{ url_for('serve_file', filename=photo) }}" target="_blank">
                    <img src="{{ url_for('serve_file', filename=photo) }}" alt="{{ photo }}">
                </a>
                <div class="filename">{{ photo }}</div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p>No photos captured yet. Wait for birds to be detected!</p>
        {% endif %}
        
        <h2>🎥 Captured Videos</h2>
        {% if videos %}
        <div class="gallery">
            {% for video in videos %}
            <div class="gallery-item">
                <video controls>
                    <source src="{{ url_for('serve_file', filename=video) }}" type="video/x-msvideo">
                    Your browser doesn't support video playback.
                </video>
                <div class="filename">{{ video }}</div>
                {% if audios and video.replace('.avi', '.wav') in audios %}
                <audio controls style="width: 100%; margin-top: 10px;">
                    <source src="{{ url_for('serve_file', filename=video.replace('.avi', '.wav')) }}" type="audio/wav">
                </audio>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p>No videos captured yet.</p>
        {% endif %}
    </div>
</body>
</html>
"""

def generate_frames():
    """Generate frames from camera for live streaming"""
    camera = cv2.VideoCapture(CAMERA_INDEX)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    try:
        while True:
            success, frame = camera.read()
            if not success:
                break
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            # Yield frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        camera.release()

@app.route('/')
def index():
    """Main page showing live feed and gallery"""
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get all files from output directory
    files = os.listdir(OUTPUT_DIR)
    
    # Separate photos and videos
    photos = sorted([f for f in files if f.endswith('.jpg')], reverse=True)
    videos = sorted([f for f in files if f.endswith('.avi')], reverse=True)
    audios = [f for f in files if f.endswith('.wav')]
    
    return render_template_string(
        HTML_TEMPLATE,
        photos=photos,
        videos=videos,
        audios=audios,
        photo_count=len(photos),
        video_count=len(videos),
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/files/<filename>')
def serve_file(filename):
    """Serve captured files"""
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🐦 Bird Camera Web Viewer")
    print("="*50)
    print("\nStarting web server...")
    print("Open browser and go to: http://localhost:5000")
    print("Or from another device: http://[PI_IP_ADDRESS]:5000")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)