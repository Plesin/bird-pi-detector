# bird-pi-detector

Bird webcamera detector with Rapsberry Pi4

## HW used

- Raspberry Pi 4 Model B - 4GB RAM
- Logitech C922 webcam

## Local Development on MacOs

```
brew install fswatch
./dev.sh
```

`dev.sh` watches for local file changes and runs rsync to the Pi based on `.env` values
