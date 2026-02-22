"""
Page routes — HTML views served to the browser.
"""

import cv2
import os
from datetime import datetime

from flask import Blueprint, Response, render_template, send_from_directory

from camera_config import get_camera_from_env
from utils.media import OUTPUT_DIR, TEMPLATE_NAME, collect_media_by_day, format_day_label

pages = Blueprint('pages', __name__)


def generate_frames():
    """Generate frames from camera for live streaming"""
    camera_config = get_camera_from_env()
    camera = camera_config.open_camera(width=1920, height=1080, fps=30)
    try:
        while True:
            success, frame = camera.read()
            if not success:
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        camera_config.close()


@pages.route('/')
def index():
    """Main page showing live feed and gallery"""
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
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )


@pages.route('/day/<day_key>')
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
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )


@pages.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
    )


@pages.route('/files/<path:filename>')
def serve_file(filename):
    """Serve captured files"""
    return send_from_directory(OUTPUT_DIR, filename)
