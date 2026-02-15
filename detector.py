#!/usr/bin/env python3
"""
Bird Detection Camera System
Detects motion and captures photos or videos with audio
"""

import cv2
import numpy as np
import time
import os
from datetime import datetime
from threading import Thread
from collections import deque
import pyaudio
import wave

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

from camera_config import CameraConfig, get_camera_from_env

# ==================== CONFIGURATION ====================

# Mode: "photo" or "video"
CAPTURE_MODE = "photo"

# Photo mode settings
PHOTOS_PER_DETECTION = 3
PHOTO_DELAY_SECONDS = 2

# Video mode settings
VIDEO_DURATION_SECONDS = 5
RECORD_AUDIO = False

# Detection settings
MOTION_THRESHOLD = 20000  # Lower = more sensitive (try 3000-10000)
COOLDOWN_SECONDS = 30    # Time to wait before next detection

# Camera settings
CAMERA_WIDTH = 2560 # 2560 | 4056
CAMERA_HEIGHT = 1440 # 1440 | 3040
CAMERA_FPS = 30

# Use lower resolution for video mode to reduce CPU load
if CAPTURE_MODE == "video":
    CAMERA_WIDTH = 1920
    CAMERA_HEIGHT = 1080

# Storage settings
OUTPUT_DIR = "media"

# Audio settings (if recording video with audio)
AUDIO_RATE = 44100
AUDIO_CHANNELS = 1
AUDIO_CHUNK = 1024

# ======================================================

class BirdDetector:
    def __init__(self):
        # Create output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Initialize camera using camera configuration
        camera_config = get_camera_from_env()
        
        print("Initializing camera...")
        self.cap = camera_config.open_camera(
            width=CAMERA_WIDTH,
            height=CAMERA_HEIGHT,
            fps=CAMERA_FPS
        )
        self.camera_config = camera_config
        
        # Initialize background subtractor for motion detection
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, 
            varThreshold=16, 
            detectShadows=False
        )
        
        self.last_detection_time = time.time()
        self.audio_frames = []
        
        # Frame buffer for threaded recording
        self.frame_buffer = deque(maxlen=300)  # Buffer up to 300 frames
        self.stop_reading = False

    def get_day_dir(self, timestamp):
        """Create and return daily output directory"""
        day_key = timestamp.split('_')[0]
        day_dir = os.path.join(OUTPUT_DIR, day_key)
        os.makedirs(day_dir, exist_ok=True)
        return day_dir
        
    def is_bird_like(self, contour):
        """Filter contours by shape to reduce false positives"""
        area = cv2.contourArea(contour)
        if area < MOTION_THRESHOLD:
            return False
        
        # Get bounding box
        x, y, w, h = cv2.boundingRect(contour)
        
        # Avoid division by zero
        if h == 0:
            return False
        
        aspect_ratio = float(w) / h
        
        # Bird-like shapes are roughly 0.4 to 2.5 ratio
        # (not ultra-thin shadows or ultra-wide clouds)
        if 0.4 < aspect_ratio < 2.5:
            return True
        
        return False
    
    def detect_motion(self, frame):
        """Detect motion in frame using background subtraction"""
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Find contours in the mask
        contours, _ = cv2.findContours(
            fg_mask, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Check if any contour is bird-like and large enough
        for contour in contours:
            if self.is_bird_like(contour):
                return True
        
        return False
    
    def capture_photos(self):
        """Capture multiple photos"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        day_dir = self.get_day_dir(timestamp)
        print(f"\n🐦 Bird detected! Taking {PHOTOS_PER_DETECTION} photos...")
        
        for i in range(PHOTOS_PER_DETECTION):
            ret, frame = self.cap.read()
            if ret:
                filename = os.path.join(
                    day_dir,
                    f"bird_{timestamp}_{i+1}.jpg"
                )
                cv2.imwrite(filename, frame)
                print(f"  📸 Saved: {filename}")
                time.sleep(PHOTO_DELAY_SECONDS)
            else:
                print(f"  ❌ Failed to capture photo {i+1}")
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio recording"""
        self.audio_frames.append(in_data)
        return (in_data, pyaudio.paContinue)
    
    def continuous_frame_reader(self, duration_seconds):
        """Read frames continuously into buffer for specified duration"""
        start_time = time.time()
        self.frame_buffer.clear()
        self.stop_reading = False
        frame_times = []
        
        while time.time() - start_time < duration_seconds and not self.stop_reading:
            frame_start = time.time()
            ret, frame = self.cap.read()
            frame_time = time.time() - frame_start
            
            if ret:
                self.frame_buffer.append(frame)
                frame_times.append(frame_time)
            else:
                print("  ❌ Failed to read frame from camera")
                break
        
        # Calculate actual FPS
        if frame_times:
            avg_frame_time = sum(frame_times) / len(frame_times)
            actual_fps = 1.0 / avg_frame_time
            print(f"  📊 Camera FPS analysis:")
            print(f"     Avg frame read time: {avg_frame_time*1000:.1f}ms")
            print(f"     Actual camera FPS: {actual_fps:.1f}")
                
    def record_video_with_audio(self):
        global RECORD_AUDIO
        """Record video with audio using threaded frame reading"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        day_dir = self.get_day_dir(timestamp)
        video_filename = os.path.join(day_dir, f"bird_{timestamp}.mp4")
        audio_filename = os.path.join(day_dir, f"bird_{timestamp}.wav")
        
        print(f"\n🐦 Bird detected! Recording {VIDEO_DURATION_SECONDS}s video...")
        
        # Start frame reading thread
        reader_thread = Thread(target=self.continuous_frame_reader, args=(VIDEO_DURATION_SECONDS,))
        reader_thread.daemon = True
        reader_thread.start()
        
        # Wait a moment for frames to start buffering
        time.sleep(0.1)
        
        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(
            video_filename, 
            fourcc, 
            CAMERA_FPS, 
            (CAMERA_WIDTH, CAMERA_HEIGHT)
        )
        
        # Setup audio recording if enabled
        audio_stream = None
        p = None
        if RECORD_AUDIO:
            try:
                p = pyaudio.PyAudio()
                self.audio_frames = []
                audio_stream = p.open(
                    format=pyaudio.paInt16,
                    channels=AUDIO_CHANNELS,
                    rate=AUDIO_RATE,
                    input=True,
                    frames_per_buffer=AUDIO_CHUNK,
                    stream_callback=self.audio_callback
                )
                audio_stream.start_stream()
                print("  🎤 Audio recording started")
            except Exception as e:
                print(f"  ⚠️  Audio recording failed: {e}")
                RECORD_AUDIO = False
        
        # Wait for reader thread to finish and write all frames
        reader_thread.join()
        
        frame_count = 0
        while self.frame_buffer:
            frame = self.frame_buffer.popleft()
            out.write(frame)
            frame_count += 1
        
        # Stop audio recording
        if audio_stream:
            audio_stream.stop_stream()
            audio_stream.close()
            
            # Save audio file
            wf = wave.open(audio_filename, 'wb')
            wf.setnchannels(AUDIO_CHANNELS)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(AUDIO_RATE)
            wf.writeframes(b''.join(self.audio_frames))
            wf.close()
            print(f"  🎤 Saved audio: {audio_filename}")
        
        if p:
            p.terminate()
        
        out.release()
        expected_frames = VIDEO_DURATION_SECONDS * CAMERA_FPS
        print(f"  🎥 Saved video: {video_filename}")
        print(f"     Recorded {frame_count} frames (expected {expected_frames})")
        if frame_count < expected_frames * 0.8:
            print(f"     ⚠️  Warning: Only {frame_count/expected_frames*100:.0f}% of expected frames recorded")
    
    def run(self):
        """Main detection loop"""
        print("\n" + "="*50)
        print(f"🐦 Bird Detection System Started")
        print(f"Mode: {CAPTURE_MODE.upper()}")
        print(f"Motion threshold: {MOTION_THRESHOLD}")
        print(f"Output directory: {OUTPUT_DIR}")
        print(f"Press Ctrl+C to stop")
        print("="*50 + "\n")
        
        try:
            frame_count = 0
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to read frame")
                    break
                
                frame_count += 1
                
                # Check for motion every few frames
                if frame_count % 5 == 0:
                    motion_detected = self.detect_motion(frame)

                    # DEBUG: Show what's being detected
                    if frame_count % 30 == 0:  # Print every 30 frames
                        fg_mask = self.bg_subtractor.apply(frame)
                        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        # Show stats on largest contours
                        stats = []
                        for c in contours:
                            area = cv2.contourArea(c)
                            if area > MOTION_THRESHOLD / 2:  # Only show significant contours
                                x, y, w, h = cv2.boundingRect(c)
                                aspect = float(w) / h if h > 0 else 0
                                bird_like = self.is_bird_like(c)
                                stats.append(f"area={int(area)}, aspect={aspect:.2f}, bird-like={bird_like}")
                        
                        print(f"Frame {frame_count}: Motion={motion_detected}, Threshold={MOTION_THRESHOLD}")
                        if stats:
                            for stat in stats:
                                print(f"  └─ {stat}")
                    
                    # Check cooldown period
                    current_time = time.time()
                    if motion_detected and (current_time - self.last_detection_time) > COOLDOWN_SECONDS:
                        self.last_detection_time = current_time
                        
                        if CAPTURE_MODE == "photo":
                            self.capture_photos()
                        elif CAPTURE_MODE == "video":
                            self.record_video_with_audio()
                        
                        print(f"\n⏳ Cooldown for {COOLDOWN_SECONDS}s...")
                
                # Small delay to reduce CPU usage
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping bird detection system...")
        finally:
            self.camera_config.close()
            cv2.destroyAllWindows()
            print("✅ Camera released. Goodbye!")

if __name__ == "__main__":
    detector = BirdDetector()
    detector.run()