# Bird Rapsberry Pi4 Detector

Bird detector with Raspberry Pi4 - AI coded and supervised

## HW used

- Raspberry Pi 4 Model B - 4GB RAM
- Pi HQ Camera with 16 mm telephoto lens

## Camera Support

- **Raspberry Pi HQ Camera** (libcamera)
- Any V4L2-compatible camera

See [CAMERA_SETUP.md](CAMERA_SETUP.md) for detailed camera configuration and multi-camera setup.

## Setup (One-time)

```bash
./setup.sh
```

See [setup.sh](setup.sh) for dependencies details.

### Running the Bird Detector

```bash
./start.sh
```

## Local Development on MacOs

```
brew install fswatch
./dev.sh
```

`dev.sh` watches for local file changes and runs rsync to the Pi based on `.env` values
