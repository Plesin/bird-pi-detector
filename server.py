#!/usr/bin/env python3
"""
Bird Camera Web Viewer
View live stream and browse captured photos/videos
"""

from flask import Flask, render_template, Response, send_from_directory, request, redirect, url_for
import cv2
import os
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

from camera_config import CameraConfig, get_camera_from_env
from utils.exif import load_exif_data

# Configuration
OUTPUT_DIR = "media"

app = Flask(__name__)

TEMPLATE_NAME = "index.html"

def generate_frames():
    """Generate frames from camera for live streaming"""
    camera_config = get_camera_from_env()
    camera = camera_config.open_camera(
        width=1920,
        height=1080,
        fps=30
    )
    
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
        camera_config.close()

def extract_day_from_name(filename):
    """Extract YYYYMMDD from filenames like bird_YYYYMMDD_HHMMSS_1.jpg"""
    base = os.path.basename(filename)
    parts = base.split('_')
    if len(parts) >= 2 and len(parts[1]) == 8 and parts[1].isdigit():
        return parts[1]
    return None

def extract_time_from_name(filename):
    """Extract HH:MM:SS from filenames like bird_YYYYMMDD_HHMMSS_1.jpg or bird_YYYYMMDD_HHMMSS.mp4"""
    base = os.path.basename(filename)
    parts = base.split('_')
    if len(parts) >= 3:
        # Remove file extension from the last part
        time_part = parts[2].split('.')[0]
        if len(time_part) == 6 and time_part.isdigit():
            return f"{time_part[0:2]}:{time_part[2:4]}:{time_part[4:6]}"
    return None

def format_day_label(day_key):
    """Format day label for display"""
    if day_key == "unknown":
        return "Unknown Date"
    try:
        return datetime.strptime(day_key, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return day_key

def format_day_summary(day_key, photos):
    """Format human-readable day summary like 'Feb 2nd 2026 - 45 photos'"""
    if day_key == "unknown" or not photos:
        return None
    try:
        date_obj = datetime.strptime(day_key, "%Y%m%d")
        # Format: "Feb 2nd 2026"
        return date_obj.strftime("%b %d %Y")
    except ValueError:
        return None

def get_time_range_for_day(photos):
    """Extract first and last capture time from photos"""
    if not photos:
        return None, None
    
    times = []
    for photo in photos:
        time_label = photo.get("time_label")
        if time_label:
            times.append(time_label)
    
    if times:
        # Photos are sorted newest first, so reverse to get chronological order
        times_sorted = sorted(times)
        return times_sorted[0], times_sorted[-1]
    return None, None

def collect_media_by_day():
    """Collect media files grouped by day from subfolders or filenames"""
    days = {}
    for root, _, files in os.walk(OUTPUT_DIR):
        for filename in files:
            if not filename.endswith(('.jpg', '.mp4', '.avi', '.wav')):
                continue

            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, OUTPUT_DIR)
            parts = rel_path.split(os.sep)

            if len(parts) > 1:
                day_key = parts[0]
            else:
                day_key = extract_day_from_name(filename)

            if not day_key:
                day_key = "unknown"

            day_entry = days.setdefault(day_key, {
                "photos": [],
                "videos": [],
                "audios": []
            })

            time_label = extract_time_from_name(filename)
            media_item = {"path": rel_path, "time_label": time_label}

            if filename.endswith('.jpg'):
                # Load EXIF data from image
                exif_data = load_exif_data(os.path.join(OUTPUT_DIR, rel_path))
                media_item["exif"] = exif_data
                media_item["iso"] = exif_data.get("ISO")
                media_item["shutter_speed"] = exif_data.get("ShutterSpeed")
                day_entry["photos"].append(media_item)
            elif filename.endswith(('.mp4', '.avi')):
                day_entry["videos"].append(media_item)
            elif filename.endswith('.wav'):
                day_entry["audios"].append(rel_path)

    day_keys = sorted([k for k in days.keys() if k != "unknown"], reverse=True)
    if "unknown" in days:
        day_keys.append("unknown")

    day_list = []
    for day_key in day_keys:
        entry = days[day_key]
        entry["photos"].sort(key=lambda item: item["path"], reverse=True)
        entry["videos"].sort(key=lambda item: item["path"], reverse=True)
        entry["audios"].sort(reverse=True)
        
        photos = entry["photos"]
        first_time, last_time = get_time_range_for_day(photos)
        
        day_list.append({
            "key": day_key,
            "label": format_day_label(day_key),
            "summary": format_day_summary(day_key, photos),
            "photo_count": len(photos),
            "video_count": len(entry["videos"]),
            "first_time": first_time,
            "last_time": last_time,
            "photos": photos,
            "videos": entry["videos"],
            "audios": entry["audios"],
            "is_today": day_key == datetime.now().strftime("%Y%m%d"),
        })

    return day_list

@app.route('/')
def index():
    """Main page showing live feed and gallery"""
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    days = collect_media_by_day()
    photo_count = sum(len(day["photos"]) for day in days)
    video_count = sum(len(day["videos"]) for day in days)
    audio_set = set()
    for day in days:
        audio_set.update(day["audios"])

    return render_template(
        TEMPLATE_NAME,
        days=days,
        audio_set=audio_set,
        active_day_label=None,
        photo_count=photo_count,
        video_count=video_count,
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/day/<day_key>')
def day_view(day_key):
    """Day-specific page showing media for a single day"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    days = collect_media_by_day()
    day_entry = next((day for day in days if day["key"] == day_key), None)
    filtered_days = [day_entry] if day_entry else []
    active_day_label = format_day_label(day_key)

    photo_count = sum(len(day["photos"]) for day in filtered_days)
    video_count = sum(len(day["videos"]) for day in filtered_days)
    audio_set = set()
    for day in filtered_days:
        audio_set.update(day["audios"])

    return render_template(
        TEMPLATE_NAME,
        days=filtered_days,
        audio_set=audio_set,
        active_day_label=active_day_label,
        photo_count=photo_count,
        video_count=video_count,
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/files/<path:filename>')
def serve_file(filename):
    """Serve captured files"""
    return send_from_directory(OUTPUT_DIR, filename)

@app.route('/delete/<path:filename>', methods=['POST'])
def delete_file(filename):
    """Delete a captured file"""
    abs_output = os.path.abspath(OUTPUT_DIR)
    target_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))
    if not target_path.startswith(abs_output + os.sep):
        return "Invalid path", 400

    if os.path.isfile(target_path):
        os.remove(target_path)

    if request.headers.get("X-Requested-With") == "fetch":
        return "", 204

    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🐦 Bird Camera Web Viewer")
    print("="*50)
    print("\nStarting web server...")
    print("Open browser and go to: http://localhost:5000")
    print("Or from another device: http://[PI_IP_ADDRESS]:5000")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)