# bird-pi-detector

Bird webcamera detector with Rapsberry Pi4

## HW used

- Raspberry Pi 4 Model B - 4GB RAM
- Logitech C922 webcam (or Pi HQ Camera)
- Support for multiple cameras with automatic detection

## Camera Support

This project now supports multiple cameras:

- **Logitech C922** USB webcam
- **Raspberry Pi HQ Camera** (libcamera)
- Any V4L2-compatible camera

See [CAMERA_SETUP.md](CAMERA_SETUP.md) for detailed camera configuration and multi-camera setup.

## Local Development on MacOs

```
brew install fswatch
./dev.sh
```

`dev.sh` watches for local file changes and runs rsync to the Pi based on `.env` values
