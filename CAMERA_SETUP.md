# Pi HQ Camera Setup Guide

The bird detector requires explicit camera configuration. This project uses the **Raspberry Pi HQ Camera** with libcamera.

## Quick Start

Set this in `.env`:

```bash
CAMERA_TYPE=pi_hq
```

That's it! The detector will automatically find and use your Pi HQ Camera.

## Configuration

### Basic Setup

```bash
# .env - Required
CAMERA_TYPE=pi_hq
```

### White Balance Mode (`CAMERA_AWB_MODE`)

Controls how the camera adjusts color temperature. Default is **7 (Cloudy)**, which provides realistic colors outdoors for bird watching.

```bash
# .env - Optional
CAMERA_AWB_MODE=7  # See options below
```

**Available Modes:**

| Mode         | Value | Description                         | Best For                        |
| ------------ | ----- | ----------------------------------- | ------------------------------- |
| Off          | 0     | Manual, no white balance correction | Custom color grading            |
| Auto         | 1     | Automatic detection                 | Varying light conditions        |
| Incandescent | 2     | Warmest (for tungsten bulbs)        | Indoor warm lighting            |
| Tungsten     | 3     | Warm lighting                       | Incandescent bulbs              |
| Indoor       | 5     | Neutral indoor lighting             | Indoor cameras                  |
| Daylight     | 6     | Bright daylight (cooler)            | Bright sunny days               |
| Cloudy       | **7** | Overcast skies (adds warmth)        | Outdoor bird watching (DEFAULT) |

**Examples:**

```bash
# Bright sunny conditions
CAMERA_AWB_MODE=6

# Indoor tungsten lighting
CAMERA_AWB_MODE=2

# Cloudy/overcast (default - most realistic for bird watching)
CAMERA_AWB_MODE=7
```

## Pi HQ Camera Hardware

- **Sensor**: IMX477 (12.3 MP)
- **Interface**: CSI-2 (Ribbon cable to CSI port)
- **Resolution**: Up to 4056x3040 (12.3 MP)
- **Controls**: Manual focus via lens adjustment ring
- **Focus Range**: 19cm to infinity

### Hardware Setup

1. Ensure the camera ribbon cable is correctly connected to **CSI0 or CSI1** port (not the DSI port)
2. Enable camera through `raspi-config`:
   ```bash
   sudo raspi-config
   # Navigate: Interfacing Options > Camera > Enable
   ```
3. Reboot: `sudo reboot`

### Verify Camera is Working

```bash
# Test with libcamera tools
rpicam-still -o test.jpg -t 1000

# Should create test.jpg in 1 second
ls -lah test.jpg
```

## Resolution Configuration

The detector uses different resolutions for different purposes:

- **Detection (detector.py)**: Configurable, defaults to 1024x768
- **Web Viewer (server.py)**: 1024x768 (recommended for smooth streaming)
- **Photo Capture**: Full resolution (4056x3040) for high-quality archives

You can modify resolution in the source code or via configuration.

## Troubleshooting

### Camera Not Found

```bash
# Check if camera is detected
libcamera-hello

# Check V4L2 devices
ls -la /dev/video*

# Should show /dev/video10 and possibly /dev/video11+ (libcamera devices)
```

### No Image or Black Screen

1. **Check cable connection**: Ensure ribbon cable is fully seated in CSI port
2. **Check CSI port**: Some Raspberry Pi boards have multiple CSI ports - try CSI0 or CSI1
3. **Reboot and retry**: `sudo reboot`
4. **Check permissions**: Your user should be in the video group
   ```bash
   groups
   # If 'video' not listed:
   sudo usermod -aG video $USER
   # Then log out and back in
   ```

### Blue or Incorrect Color Tint

This is usually a white balance issue:

1. Try different white balance modes in `.env`:
   ```bash
   CAMERA_AWB_MODE=6  # Daylight
   CAMERA_AWB_MODE=7  # Cloudy (default, usually best)
   ```
2. Restart the detector: `python3 detector.py`

### Camera in Use by Another Application

```bash
# Check what's using the camera
lsof /dev/video*

# Kill the process using the camera
kill -9 <PID>

# Or restart:
sudo systemctl restart libcamera-daemon 2>/dev/null || true
```
