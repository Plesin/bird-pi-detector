#!/usr/bin/env python3
"""
Camera Configuration and Detection
Supports multiple camera types: Logitech C922, Pi HQ Camera, generic V4L2 cameras
"""

import cv2
import os
import subprocess
import numpy as np

# Try to import picamera2 for Pi HQ Camera support
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

class CameraType:
    """Camera type identifiers"""
    USB_WEBCAM = "usb_webcam"
    PI_HQ = "pi_hq"
    GENERIC_V4L2 = "generic_v4l2"


class PiCamera2Wrapper:
    """Wrapper for picamera2 that provides OpenCV-compatible interface"""
    
    def __init__(self, width=1920, height=1080, fps=30):
        """Initialize Pi HQ Camera with picamera2"""
        if not PICAMERA2_AVAILABLE:
            raise Exception("picamera2 not available. Install with: sudo apt install python3-picamera2")
        
        self.picam2 = None
        self.width = width
        self.height = height
        self.fps = fps
        self._open_camera()
    
    def _open_camera(self):
        """Open and configure the camera"""
        self.picam2 = Picamera2()
        
        # Create a config for video capture
        video_config = self.picam2.create_video_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"},
            controls={"FrameRate": self.fps}
        )
        self.picam2.configure(video_config)
        self.picam2.start()
        
        # Warm up the camera
        import time
        time.sleep(0.2)
        for _ in range(5):
            self.picam2.capture_array()
    
    def read(self):
        """Read a frame (OpenCV-compatible interface)"""
        try:
            frame = self.picam2.capture_array()
            # picamera2 returns RGB, convert to BGR for OpenCV compatibility
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return True, frame_bgr
        except Exception as e:
            print(f"Error reading frame: {e}")
            return False, None
    
    def release(self):
        """Release camera resources"""
        if self.picam2:
            self.picam2.stop()
    
    def set(self, property_id, value):
        """Set camera property (stub for compatibility)"""
        # picamera2 doesn't support setting properties this way
        # Properties are configured in _open_camera
        pass


class CameraType:
    """Camera type identifiers"""
    USB_WEBCAM = "usb_webcam"
    PI_HQ = "pi_hq"
    GENERIC_V4L2 = "generic_v4l2"


class CameraConfig:
    """Manages camera configuration and auto-detection"""
    
    def __init__(self, camera_index=None, camera_type=None, camera_path=None):
        """
        Initialize camera configuration
        
        Args:
            camera_index: int or None (0, 1, 2, etc.) - OpenCV camera index
            camera_type: str or None - Camera type identifier
            camera_path: str or None - Path to camera device (/dev/video0, etc.)
        """
        self.camera_index = camera_index
        self.camera_type = camera_type
        self.camera_path = camera_path
        self.camera = None
        self._detected_cameras = None
        
    def detect_available_cameras(self):
        """
        Detect all available cameras on the system
        
        Returns:
            List of dicts with camera info:
            {
                'index': int,
                'path': str,
                'type': str,
                'name': str,
                'is_available': bool
            }
        """
        if self._detected_cameras is not None:
            return self._detected_cameras
        
        cameras = []
        
        # Try V4L2 device detection (Linux/Raspberry Pi)
        if os.path.exists('/dev'):
            try:
                # Get all /dev/video* devices (including high numbers from libcamera)
                result = subprocess.run(
                    'ls /dev/video* 2>/dev/null || true',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                device_paths = set()
                for line in result.stdout.strip().split('\n'):
                    if line and '/dev/video' in line:
                        device_paths.add(line.strip())
                
                for i, path in enumerate(sorted(device_paths)):
                    if path and os.path.exists(path):
                        camera_info = self._get_camera_info(path, i)
                        cameras.append(camera_info)
            except Exception as e:
                print(f"Warning: Could not detect V4L2 devices: {e}")
        
        self._detected_cameras = cameras
        return cameras
    
    def _get_camera_info(self, device_path, index):
        """Get camera information from device path"""
        camera_type = self._identify_camera_type(device_path)
        
        camera_info = {
            'index': index,
            'path': device_path,
            'type': camera_type,
            'name': self._get_camera_name(device_path),
            'is_available': self._is_camera_available(device_path)
        }
        
        # For Pi HQ Camera (libcamera), don't try to test open it
        # Just skip resolution detection since it won't work with V4L2
        if camera_type == CameraType.PI_HQ:
            camera_info['resolution'] = None
            return camera_info
        
        # Try to get resolution via OpenCV for USB cameras
        if camera_info['is_available']:
            try:
                cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        camera_info['resolution'] = (frame.shape[1], frame.shape[0])
                    cap.release()
            except Exception:
                pass
        
        return camera_info
    
    def _identify_camera_type(self, device_path):
        """Identify camera type from device path or name"""
        try:
            # Check for libcamera devices (Pi HQ Camera creates /dev/video10+)
            try:
                video_num = int(device_path.split('video')[-1])
                if video_num >= 10:
                    # High numbered video devices are typically from libcamera (Pi HQ)
                    return CameraType.PI_HQ
            except (ValueError, IndexError):
                pass
            
            # Try to get device name
            result = subprocess.run(
                ['udevadm', 'info', '--query=property', '--name=' + device_path],
                capture_output=True,
                text=True,
                timeout=2
            )
            info = result.stdout.lower()
            
            if 'arducam' in info or 'ov5647' in info or 'imx219' in info or 'imx477' in info:
                return CameraType.PI_HQ
            
            # Check device name
            name = self._get_camera_name(device_path)
            if 'hq' in name.lower() or 'arducam' in name.lower() or 'imx' in name.lower():
                return CameraType.PI_HQ
            if 'csi' in name.lower() or 'mipi' in name.lower():
                return CameraType.PI_HQ
            
            # Default USB cameras to usb_webcam
            if '/dev/video' in device_path:
                return CameraType.USB_WEBCAM
                
            return CameraType.GENERIC_V4L2
        except Exception:
            return CameraType.GENERIC_V4L2
    
    def _get_camera_name(self, device_path):
        """Get human-readable camera name"""
        try:
            result = subprocess.run(
                ['udevadm', 'info', '--query=property', '--name=' + device_path],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'ID_MODEL=' in line:
                    return line.split('=')[1].strip()
        except Exception:
            pass
        
        return os.path.basename(device_path)
    
    def _is_camera_available(self, device_path):
        """Check if camera device is accessible"""
        return os.path.exists(device_path) and os.access(device_path, os.R_OK)
    
    def _find_camera_quick(self, camera_type):
        """
        Quick camera search optimized for fast startup
        Only checks common paths for the given camera type
        
        Returns:
            Camera info dict or None if not found
        """
        if camera_type == CameraType.PI_HQ:
            # Pi HQ Camera is on /dev/video10 (or higher numbered devices)
            # Just use the first one we find
            for video_num in range(10, 32):
                device_path = f"/dev/video{video_num}"
                if os.path.exists(device_path):
                    return {
                        'index': video_num,
                        'path': device_path,
                        'type': CameraType.PI_HQ,
                        'name': 'Pi HQ Camera',
                        'is_available': True,
                        'resolution': None
                    }
        
        elif camera_type == CameraType.USB_WEBCAM:
            # USB cameras are typically /dev/video0-3
            for index in range(4):
                device_path = f"/dev/video{index}"
                if os.path.exists(device_path):
                    return {
                        'index': index,
                        'path': device_path,
                        'type': CameraType.USB_WEBCAM,
                        'name': f'USB Camera {index}',
                        'is_available': True,
                        'resolution': None
                    }
        
        return None
    
    def select_camera(self):
        """
        Select camera based on explicit configuration
        
        Requires CAMERA_TYPE to be set - no auto-detection fallback
        
        Returns:
            Selected camera info or raises exception if configuration/camera not found
        """
        # Camera type is REQUIRED
        if not self.camera_type:
            raise Exception(
                "❌ CAMERA_TYPE not configured!\n"
                "You must set CAMERA_TYPE in .env to either:\n"
                "  - CAMERA_TYPE=usb_webcam\n"
                "  - CAMERA_TYPE=pi_hq\n"
            )
        
        # Fast camera lookup for configured type (no detection)
        matching_camera = self._find_camera_quick(self.camera_type)
        
        if not matching_camera:
            raise Exception(
                f"❌ Configured camera type '{self.camera_type}' not found!\n"
                f"Expected camera path not accessible:\n"
                f"  - pi_hq: /dev/video10+ (libcamera devices)\n"
                f"  - usb_webcam: /dev/video0-3\n"
                f"\nPlease check your camera is properly connected."
            )
        
        return matching_camera
    
    def _format_camera_list(self, cameras):
        """Format camera list for display"""
        lines = []
        for cam in cameras:
            status = "✅" if cam['is_available'] else "❌"
            name = cam.get('name', 'Unknown')
            cam_type = cam.get('type', 'unknown')
            path = cam.get('path', f"index {cam.get('index', '?')}")
            lines.append(f"  {status} {name} (Type: {cam_type}, Path: {path})")
        return "\n".join(lines)
    
    def _warn_camera_mismatch(self, cameras, configured_type):
        """Warn if other cameras are available that don't match configured type"""
        other_cameras = [cam for cam in cameras if cam['type'] != configured_type and cam['is_available']]
        if other_cameras:
            print("\n⚠️  WARNING: Other cameras detected that were NOT configured:")
            for cam in other_cameras:
                print(f"  - {cam.get('name', 'Unknown')} (Type: {cam['type']})")
            print(f"Using configured camera type: {configured_type}\n")
    
    def open_camera(self, width=1920, height=1080, fps=30, camera_backend=None):
        """
        Open and configure camera for capture
        
        Args:
            width: Capture width
            height: Capture height
            fps: Frames per second
            camera_backend: cv2.CAP_* backend to use (ignored for Pi HQ)
        
        Returns:
            Camera object (OpenCV VideoCapture or PiCamera2Wrapper)
        """
        cam_info = self.select_camera()
        self.camera_info = cam_info
        
        print(f"Opening camera: {cam_info['name']} ({cam_info['type']})")
        
        # For Pi HQ Camera, use picamera2
        if cam_info['type'] == CameraType.PI_HQ:
            try:
                self.camera = PiCamera2Wrapper(width=width, height=height, fps=fps)
                print(f"Camera ready: {width}x{height} @ {fps} FPS")
                return self.camera
            except Exception as e:
                raise Exception(f"Could not open Pi HQ Camera: {e}")
        
        # For USB cameras, use OpenCV with V4L2
        else:
            if camera_backend is None:
                camera_backend = cv2.CAP_V4L2
            
            if cam_info['path']:
                self.camera = cv2.VideoCapture(cam_info['path'], camera_backend)
            else:
                self.camera = cv2.VideoCapture(cam_info['index'], camera_backend)
        
        if not self.camera.isOpened():
            raise Exception(f"Could not open camera: {cam_info['name']}")
        
        # Configure camera properties
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.camera.set(cv2.CAP_PROP_FPS, fps)
        
        # Camera-specific optimizations
        self._optimize_camera_settings(cam_info)
        
        # Test capture
        ret, frame = self.camera.read()
        if not ret:
            raise Exception(f"Could not read from camera: {cam_info['name']}")
        
        actual_width = frame.shape[1]
        actual_height = frame.shape[0]
        print(f"Camera ready: {actual_width}x{actual_height} @ {fps} FPS")
        
        return self.camera
    
    def _optimize_camera_settings(self, cam_info):
        """Apply camera-specific optimizations"""
        camera_type = cam_info['type']
        
        if camera_type == CameraType.USB_WEBCAM:
            # USB webcam specific settings
            try:
                self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            except:
                pass  # Not all USB cameras support autofocus
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
            print("  → Applied USB webcam optimizations")
        
        elif camera_type == CameraType.PI_HQ:
            # Pi HQ Camera - optimizations already applied in picamera2 config
            print("  → Pi HQ Camera using picamera2 backend")
    
    def print_available_cameras(self):
        """Print all detected cameras"""
        cameras = self.detect_available_cameras()
        
        print("\n" + "="*60)
        print("Available Cameras:")
        print("="*60)
        
        if not cameras:
            print("No cameras detected!")
            return
        
        for i, cam in enumerate(cameras, 1):
            status = "✅ Available" if cam['is_available'] else "❌ Not available"
            
            details = [
                f"#{i}",
                cam['name'],
                f"Type: {cam['type']}",
                status
            ]
            
            if cam['path']:
                details.append(f"Path: {cam['path']}")
            else:
                details.append(f"Index: {cam['index']}")
            
            if 'resolution' in cam and cam['resolution']:
                details.append(f"Resolution: {cam['resolution'][0]}x{cam['resolution'][1]}")
            
            print(" | ".join(details))
        
        print("="*60 + "\n")
    
    def close(self):
        """Release camera resources"""
        if self.camera:
            if isinstance(self.camera, PiCamera2Wrapper):
                self.camera.release()
            elif hasattr(self.camera, 'release'):
                self.camera.release()
            self.camera = None


def get_camera_from_env():
    """
    Create CameraConfig from environment variables
    
    Environment variables:
        CAMERA_INDEX: int (0, 1, etc.)
        CAMERA_TYPE: logitech_c922, pi_hq_camera, pi_legacy_csi, generic_usb, generic_v4l2
        CAMERA_PATH: /dev/video0, /dev/video1, etc.
    
    Returns:
        CameraConfig object
    """
    import os
    
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv not installed, use system environment variables
    
    camera_index = os.getenv('CAMERA_INDEX')
    if camera_index is not None:
        camera_index = int(camera_index)
    
    camera_type = os.getenv('CAMERA_TYPE')
    camera_path = os.getenv('CAMERA_PATH')
    
    return CameraConfig(
        camera_index=camera_index,
        camera_type=camera_type,
        camera_path=camera_path
    )


if __name__ == "__main__":
    # Detect and list all cameras
    config = CameraConfig()
    config.print_available_cameras()
