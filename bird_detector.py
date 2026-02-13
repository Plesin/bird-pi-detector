#!/usr/bin/env python3
"""
Bird Detection Camera System
Detects motion and captures photos or videos with audio
"""

import cv2
import numpy as np
import time
import os
import subprocess
from datetime import datetime
from threading import Thread
import pyaudio
import wave

# ==================== CONFIGURATION ====================

# Mode: "photo" or "video"
CAPTURE_MODE = "video"

# Photo mode settings
PHOTOS_PER_DETECTION = 3
PHOTO_DELAY_SECONDS = 3

# Video mode settings
VIDEO_DURATION_SECONDS = 10
RECORD_AUDIO = True

# Detection settings
MOTION_THRESHOLD = 15000  # Lower = more sensitive (try 3000-10000)
COOLDOWN_SECONDS = 30    # Time to wait before next detection

# Camera settings
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_FPS = 30

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
        
        # Initialize camera
        print("Initializing camera...")
        self.cap = cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        
        if not self.cap.isOpened():
            raise Exception("Could not open camera!")
        
        # Test capture
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("Could not read from camera!")
        
        print(f"Camera initialized: {frame.shape[1]}x{frame.shape[0]}")
        
        # Initialize background subtractor for motion detection
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, 
            varThreshold=16, 
            detectShadows=False
        )
        
        self.last_detection_time = time.time()
        self.audio_frames = []

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
    def record_video_with_audio(self):
        """Record video with audio using ffmpeg for MP4 output"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        day_dir = self.get_day_dir(timestamp)
        video_filename = os.path.join(day_dir, f"bird_{timestamp}.mp4")
        audio_filename = os.path.join(day_dir, f"bird_{timestamp}.wav")
        
        print(f"\n🐦 Bird detected! Recording {VIDEO_DURATION_SECONDS}s video...")
        
        # Setup ffmpeg process for MP4 encoding
        # Using ultrafast preset for Raspberry Pi performance
        ffmpeg_cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-loglevel', 'error',  # Reduce logging
            '-f', 'rawvideo',
            '-pixel_format', 'bgr24',
            '-video_size', f'{CAMERA_WIDTH}x{CAMERA_HEIGHT}',
            '-framerate', str(CAMERA_FPS),
            '-i', 'pipe:',
            '-c:v', 'libx264',  # H.264 codec
            '-preset', 'ultrafast',  # Fastest encoding for Pi
            '-crf', '28',  # Lower quality for faster encoding
            video_filename
        ]
        
        try:
            ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except FileNotFoundError:
            print("  ❌ ffmpeg not found. Install with: apt install ffmpeg")
            return
        
        # Setup audio recording if enabled
        audio_stream = None
        p = None
        audio_enabled = RECORD_AUDIO
        if audio_enabled:
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
                print(f"  ⚠️  Audio recording skipped (no audio hardware): {type(e).__name__}")
                audio_enabled = False
                audio_stream = None
                if p:
                    p.terminate()
                    p = None
        
        # Record video
        start_time = time.time()
        frame_count = 0
        
        print(f"  📹 Capturing {VIDEO_DURATION_SECONDS}s of video...")
        try:
            while time.time() - start_time < VIDEO_DURATION_SECONDS:
                ret, frame = self.cap.read()
                if ret:
                    try:
                        ffmpeg_process.stdin.write(frame.tobytes())
                        ffmpeg_process.stdin.flush()  # Flush after each frame
                        frame_count += 1
                    except BrokenPipeError:
                        print("  ❌ ffmpeg pipe broken")
                        break
                else:
                    print("  ❌ Failed to read frame from camera")
                    break
        except KeyboardInterrupt:
            print("  ⏹️  Recording interrupted")
        
        # Close ffmpeg pipe - wait for encoding to complete
        try:
            ffmpeg_process.stdin.close()
            # Wait up to 120 seconds for encoding to complete
            stdout, stderr = ffmpeg_process.communicate(timeout=120)
            if stderr:
                print(f"  ⚠️  ffmpeg: {stderr.decode()}")
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  ffmpeg timeout after 120s - killing process")
            ffmpeg_process.kill()
            stdout, stderr = ffmpeg_process.communicate()
        except Exception as e:
            print(f"  ⚠️  Error closing ffmpeg: {e}")
        
        # Stop audio recording
        if audio_stream:
            audio_stream.stop_stream()
            audio_stream.close()
            
            if audio_enabled and self.audio_frames:
                # Save audio file
                try:
                    wf = wave.open(audio_filename, 'wb')
                    wf.setnchannels(AUDIO_CHANNELS)
                    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(AUDIO_RATE)
                    wf.writeframes(b''.join(self.audio_frames))
                    wf.close()
                    print(f"  🎤 Saved audio: {audio_filename}")
                except Exception as e:
                    print(f"  ⚠️  Failed to save audio: {type(e).__name__}")
        
        if p:
            p.terminate()
        
        print(f"  🎥 Saved video: {video_filename} ({frame_count} frames)")
    
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
            self.cap.release()
            cv2.destroyAllWindows()
            print("✅ Camera released. Goodbye!")

if __name__ == "__main__":
    detector = BirdDetector()
    detector.run()