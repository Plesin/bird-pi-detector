# Multi-Camera Support Guide

The bird detector requires explicit camera configuration. You must specify which camera to use.

## Camera Detection & Configuration

### Quick Start

You must configure which camera to use. Set one of these in `.env`:

```bash
# Set camera by type (required)
CAMERA_TYPE=pi_hq             # Use Pi HQ Camera
CAMERA_TYPE=usb_webcam       # Use USB camera
```

### Supported Camera Types

- **`usb_webcam`** - USB webcam (any standard USB camera)
- **`pihq`** - Raspberry Pi HQ Camera (with libcamera support)

## Detecting Available Cameras

To see all detected cameras on your Raspberry Pi:

```bash
python3 camera_config.py
```

This will display:

```
============================================================
Available Cameras:
============================================================
#1 | USB Camera | Type: usb_webcam | ✅ Available | Path: /dev/video0 | Resolution: 1920x1080
#2 | imx477 | Type: pi_hq | ✅ Available | Path: /dev/video1 | Resolution: 4056x3040
============================================================
```

## Configuration Examples

### Example 1: Use USB camera

```
# .env
CAMERA_TYPE=usb_webcam
```

### Example 2: Use Pi HQ Camera

```
# .env
CAMERA_TYPE=pi_hq
```

## How It Works

1. **Camera Detection**: On startup, the system scans available cameras:
   - `/dev/video*` devices (V4L2 cameras)
   - Identifies camera types by hardware
2. **Camera Selection**: Uses the `CAMERA_TYPE` setting in `.env` to select which camera to use

3. **Validation & Warnings**:
   - If `CAMERA_TYPE` is not configured, the system will exit with an error
   - If the configured camera type is not found, the system will exit with an error listing available cameras
   - If other camera types are available that don't match your configuration, a warning is shown
   - Example: You configured `usb_webcam` but a Pi HQ camera is also connected

4. **Camera-Specific Optimizations**:
   - **USB webcam**: Autofocus enabled (if supported), buffer size optimized
   - **Pi HQ**: Buffer size optimized for low latency

## Troubleshooting

### Camera not detected

```bash
# Check devices on Linux/Pi
ls -la /dev/video*

# Check USB cameras
lsusb

# Check camera permissions
# Make sure user is in video group:
groups
# If not listed:
sudo usermod -aG video $USER
```

### Camera detected but not opening

- Ensure the camera isn't already in use by another application
- Check camera permissions: `ls -la /dev/video*`
- Make sure your user is in the video group: `groups`
- Verify `CAMERA_TYPE` in `.env` matches your connected camera

## Configuration Notes

- **`CAMERA_TYPE` is required** - You must set this in `.env`
- If the configured camera type is not detected, the system will exit with an error
- If a different camera type is detected than configured, a warning will be shown

## Using Multiple Cameras with Bird Detection

The `bird_detector.py` and `bird_viewer.py` scripts now use the camera configuration system. You can run them with different cameras:

```bash
# Use Pi HQ Camera for detection
export CAMERA_TYPE=pi_hq
python3 bird_detector.py

# Use USB camera for web viewer (in another terminal)
export CAMERA_TYPE=usb_webcam
python3 bird_viewer.py
```

Or set them permanently in your `.env` file.
