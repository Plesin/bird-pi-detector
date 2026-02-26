#!/bin/bash

# Bird Pi Detector - Setup Script
# Creates virtual environment and installs all dependencies
# 
# This script will:
# 1. Install opencv system-wide via apt (pre-compiled, no waiting):
#    - python3-opencv: Computer vision for motion detection and image processing
# 2. Create a Python virtual environment with access to system packages
# 3. Install remaining dependencies via pip:
#    - piexif: EXIF data support for embedding photo metadata into images
#    - numpy: Numerical computing library (required by OpenCV)
#    - pyaudio: Audio recording support for video capture
#    - watchdog: OS-level filesystem event monitoring for instant SSE push
#
# Note: opencv is installed via apt because Python 3.13 has no pre-built
# pip wheels yet, and compiling from source takes 30-40 minutes on Pi4

echo "🐦 Setting up Bird Pi Detector..."
echo ""

# Install opencv system-wide via apt (pre-compiled for Pi4, no waiting)
echo "📦 Installing opencv via apt..."
sudo apt install -y python3-opencv

if [ $? -ne 0 ]; then
    echo "❌ Failed to install opencv"
    exit 1
fi

# Create virtual environment with access to system packages (for opencv)
echo "📦 Creating virtual environment..."
python3 -m venv --system-site-packages venv

if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo "✅ Virtual environment created"
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install remaining dependencies via pip
echo "⬇️  Installing dependencies..."
pip install piexif numpy pyaudio watchdog

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the bird detector, run:"
echo "  ./start.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python3 detector.py"
