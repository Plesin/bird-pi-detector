"""
API routes — data endpoints consumed by the frontend JS.
"""

import os

from flask import Blueprint, redirect, render_template, request, send_from_directory, url_for

from utils.media import OUTPUT_DIR, THUMB_CACHE_DIR, THUMB_SIZES, collect_media_by_day, generate_thumb

api = Blueprint('api', __name__)


@api.route('/thumbs/<size>/<path:filename>')
def serve_thumb(size, filename):
    """Serve a cached thumbnail, generating it on first request."""
    if size not in THUMB_SIZES:
        return '', 400
    cache_path = generate_thumb(filename, size)
    if cache_path is None:
        return '', 404
    cache_dir = os.path.abspath(os.path.join(THUMB_CACHE_DIR, size))
    return send_from_directory(cache_dir, filename)


@api.route('/day/<day_key>/thumbs')
def day_thumbs(day_key):
    """Return rendered thumbnail cards for a single day (used for lazy loading)"""
    media_type = request.args.get('type', 'photos')
    days = collect_media_by_day()
    day_entry = next((day for day in days if day["key"] == day_key), None)
    if not day_entry:
        return '', 404
    audio_set = set()
    for day in days:
        audio_set.update(day["audios"])
    return render_template('_thumbs.html', day=day_entry, media_type=media_type, audio_set=audio_set)


@api.route('/delete/<path:filename>', methods=['POST'])
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

    return redirect(request.referrer or url_for('pages.index'))
