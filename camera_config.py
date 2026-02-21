#!/usr/bin/env python3
"""
Pi HQ Camera Configuration
Supports Raspberry Pi HQ Camera (libcamera) only
"""

import os

# Try to import picamera2 for Pi HQ Camera support
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False


class WhiteBalanceMode:
    """White Balance Mode options for Pi HQ Camera (libcamera)"""
    OFF = 0  # Manual, no white balance correction
    AUTO = 1  # Automatic detection
    INCANDESCENT = 2  # Warmest (indoor tungsten bulbs)
    TUNGSTEN = 3  # Warm lighting
    INDOOR = 5  # Neutral indoor lighting
    DAYLIGHT = 6  # Bright daylight (cooler)
    CLOUDY = 7  # Overcast skies (adds warmth)
    
    @classmethod
    def description(cls, mode):
        """Get description for a white balance mode"""
        modes = {
            0: "Off (manual, no correction)",
            1: "Auto (automatic detection)",
            2: "Incandescent (warmest, tungsten bulbs)",
            3: "Tungsten (warm lighting)",
            5: "Indoor (neutral)",
            6: "Daylight (bright, cooler)",
            7: "Cloudy (overcast, adds warmth)"
        }
        return modes.get(mode, "Unknown mode")


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
        self.last_metadata = None  # Store last captured metadata
        
        # Get white balance mode from environment or use default (Cloudy)
        awb_mode_env = os.getenv('CAMERA_AWB_MODE')
        if awb_mode_env is not None:
            try:
                self.awb_mode = int(awb_mode_env)
            except ValueError:
                self.awb_mode = WhiteBalanceMode.CLOUDY
        else:
            self.awb_mode = WhiteBalanceMode.CLOUDY
        
        self._open_camera()
    
    def _open_camera(self):
        """Open and configure the Pi HQ Camera"""
        self.picam2 = Picamera2()
        
        # Create a config for video capture
        video_config = self.picam2.create_video_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"},
            controls={
                "FrameRate": self.fps,
                "AwbMode": self.awb_mode
            }
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
            # Capture with metadata
            request = self.picam2.capture_request()
            frame = request.make_array("main")
            
            # Get metadata dict (picamera2 API)
            metadata = request.get_metadata()
            
            # Store metadata for later retrieval
            self.last_metadata = {
                "ExposureTime": metadata.get("ExposureTime"),  # in microseconds
                "AnalogueGain": metadata.get("AnalogueGain"),
                "DigitalGain": metadata.get("DigitalGain"),
                "Lux": metadata.get("Lux"),
                "ColourTemperature": metadata.get("ColourTemperature"),
                "ColourGains": metadata.get("ColourGains"),  # (r_gain, b_gain) white balance
                "AwbMode": self.awb_mode,  # camera white balance setting
                "FocusLength": metadata.get("FocusLength"),
                "FocusDistance": metadata.get("FocusDistance"),
                "SensorTemperature": metadata.get("SensorTemperature"),
            }
            
            # Release the request
            request.release()
            
            # Return RGB frame as-is
            return True, frame
        except Exception as e:
            print(f"Error reading frame: {e}")
            return False, None
    
    def get_metadata(self):
        """Get the last captured metadata"""
        return self.last_metadata
    
    def release(self):
        """Release camera resources"""
        if self.picam2:
            self.picam2.stop()
    
    def set(self, property_id, value):
        """Set camera property (stub for compatibility)"""
        # Properties are configured in _open_camera
        pass


class CameraConfig:
    """Manages Pi HQ Camera configuration"""
    
    def __init__(self, camera_type=None):
        """
        Initialize camera configuration
        
        Args:
            camera_type: str - Should be "pi_hq" (required)
        """
        self.camera_type = camera_type
        self.camera = None
    
    def select_camera(self):
        """
        Select camera based on configuration
        
        Returns:
            Selected camera info or raises exception if not found
        """
        # Camera type is REQUIRED
        if not self.camera_type or self.camera_type != "pi_hq":
            raise Exception(
                "❌ CAMERA_TYPE not configured or invalid!\n"
                "You must set CAMERA_TYPE in .env to:\n"
                "  - CAMERA_TYPE=pi_hq\n"
            )
        
        # Look for Pi HQ Camera on /dev/video10+
        for video_num in range(10, 32):
            device_path = f"/dev/video{video_num}"
            if os.path.exists(device_path):
                return {
                    'index': video_num,
                    'path': device_path,
                    'type': 'pi_hq',
                    'name': 'Pi HQ Camera',
                    'is_available': True,
                    'resolution': None
                }
        
        raise Exception(
            "❌ Pi HQ Camera not found!\n"
            "Expected camera at /dev/video10+ (libcamera devices)\n"
            "Please check:\n"
            "  - Camera is properly connected to CSI port\n"
            "  - libcamera is installed: sudo apt install -y libcamera-apps\n"
            "  - picamera2 is installed: sudo apt install -y python3-picamera2\n"
        )
    
    def open_camera(self, width=1920, height=1080, fps=30):
        """
        Open and configure Pi HQ Camera
        
        Args:
            width: Capture width
            height: Capture height
            fps: Frames per second
        
        Returns:
            Camera object (PiCamera2Wrapper)
        """
        cam_info = self.select_camera()
        self.camera_info = cam_info
        
        print(f"Opening camera: {cam_info['name']}")
        
        try:
            self.camera = PiCamera2Wrapper(width=width, height=height, fps=fps)            
            return self.camera
        except Exception as e:
            raise Exception(f"Could not open Pi HQ Camera: {e}")
    
    def close(self):
        """Release camera resources"""
        if self.camera:
            if isinstance(self.camera, PiCamera2Wrapper):
                self.camera.release()
            self.camera = None


def get_camera_from_env():
    """
    Create CameraConfig from environment variables
    
    Environment variables:
        CAMERA_TYPE: Must be "pi_hq"
        CAMERA_AWB_MODE: Optional white balance mode (0-7, default 7)
    
    Returns:
        CameraConfig object
    """
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv not installed, use system environment variables
    
    camera_type = os.getenv('CAMERA_TYPE')
    
    return CameraConfig(camera_type=camera_type)


if __name__ == "__main__":
    # Quick test - check if camera is accessible
    config = CameraConfig(camera_type="pi_hq")
    try:
        cam_info = config.select_camera()
        print(f"\n✅ Pi HQ Camera found at {cam_info['path']}")
    except Exception as e:
        print(f"\n{e}")
