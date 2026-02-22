"""
Shared media helpers — file discovery, grouping, and formatting.
Used by both page routes and API routes.
"""

import os
from datetime import datetime

from utils.exif import load_exif_data

OUTPUT_DIR = "media"
TEMPLATE_NAME = "index.html"


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
    """Format human-readable day summary like 'Feb 02 2026'"""
    if day_key == "unknown" or not photos:
        return None
    try:
        return datetime.strptime(day_key, "%Y%m%d").strftime("%b %d %Y")
    except ValueError:
        return None


def get_time_range_for_day(photos):
    """Extract first and last capture time from photos"""
    if not photos:
        return None, None
    times = sorted(
        p["time_label"] for p in photos if p.get("time_label")
    )
    if times:
        return times[0], times[-1]
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
                "audios": [],
            })

            time_label = extract_time_from_name(filename)
            media_item = {"path": rel_path, "time_label": time_label}

            if filename.endswith('.jpg'):
                exif_data = load_exif_data(os.path.join(OUTPUT_DIR, rel_path))
                media_item["exif"] = exif_data
                media_item["iso"] = exif_data.get("ISO")
                media_item["shutter_speed"] = exif_data.get("ShutterSpeed")
                day_entry["photos"].append(media_item)
            elif filename.endswith(('.mp4', '.avi')):
                day_entry["videos"].append(media_item)
            elif filename.endswith('.wav'):
                day_entry["audios"].append(rel_path)

    day_keys = sorted([k for k in days if k != "unknown"], reverse=True)
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
