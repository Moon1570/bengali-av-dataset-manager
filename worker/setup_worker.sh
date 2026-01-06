#!/bin/bash

# Worker setup script for students
# Run this once to configure a new worker

echo "========================================="
echo "Bengali Dataset Worker Setup"
echo "========================================="
echo ""

# Check if running in project directory
if [ ! -f "process_video.py" ]; then
    echo "ERROR: Run this script from the worker/ directory"
    exit 1
fi

# Install system dependencies
echo "Step 1: Checking system dependencies..."
MISSING=""

if ! command -v python3 &> /dev/null; then
    MISSING="$MISSING python3"
fi

if ! command -v docker &> /dev/null; then
    MISSING="$MISSING docker"
fi

if ! command -v yt-dlp &> /dev/null; then
    MISSING="$MISSING yt-dlp"
fi

if ! command -v rsync &> /dev/null; then
    MISSING="$MISSING rsync"
fi

if [ -n "$MISSING" ]; then
    echo "Missing dependencies:$MISSING"
    echo ""
    echo "Install with:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install python3 python3-pip docker.io rsync"
    echo "  sudo pip3 install yt-dlp"
    exit 1
fi

echo "✓ All dependencies installed"
echo ""

# Install Python packages
echo "Step 2: Installing Python packages..."
pip3 install -r requirements.txt

echo "✓ Python packages installed"
echo ""

# Get worker configuration
echo "Step 3: Worker Configuration"
echo ""

read -p "Enter your worker ID (e.g., student_001): " WORKER_ID
read -p "Enter API URL (e.g., http://server-ip:5000): " API_URL
read -p "Enter pipeline directory path: " PIPELINE_DIR
read -p "Enter storage base path (e.g., /mnt/dataset_storage): " STORAGE_BASE

# Validate inputs
if [ -z "$WORKER_ID" ]; then
    echo "ERROR: Worker ID is required"
    exit 1
fi

if [ -z "$API_URL" ]; then
    echo "ERROR: API URL is required"
    exit 1
fi

if [ -z "$PIPELINE_DIR" ]; then
    echo "ERROR: Pipeline directory is required"
    exit 1
fi

if [ ! -d "$PIPELINE_DIR" ]; then
    echo "ERROR: Pipeline directory does not exist: $PIPELINE_DIR"
    exit 1
fi

# Create .env file
echo ""
echo "Step 4: Creating configuration file..."

cat > .env << EOF
# Worker Configuration
WORKER_ID=$WORKER_ID
API_URL=$API_URL

# Paths
PIPELINE_DIR=$PIPELINE_DIR
DOWNLOADS_DIR=./downloads
STORAGE_BASE=$STORAGE_BASE

# Processing settings
SYNC_PRESET=medium
FILTER_FACES=true
TRANSCRIPTION_MODEL=google

# Video download settings
VIDEO_QUALITY=bestvideo[height<=720]+bestaudio/best[height<=720]

# Timeouts (seconds)
DOWNLOAD_TIMEOUT=600
PROCESSING_TIMEOUT=3600
EOF

echo "✓ Configuration saved to .env"
echo ""

# Create directories
mkdir -p downloads
mkdir -p logs

# Pull Docker image
echo "Step 5: Pulling Docker image..."
cd "$PIPELINE_DIR"
docker pull moon1570/bengali-speech-pipeline:latest

if [ $? -ne 0 ]; then
    echo "WARNING: Failed to pull Docker image"
    echo "You may need to build it manually"
fi

cd - > /dev/null

echo ""
echo "========================================="
echo "Worker Setup Complete!"
echo "========================================="
echo ""
echo "Configuration:"
echo "  Worker ID: $WORKER_ID"
echo "  API URL: $API_URL"
echo "  Pipeline: $PIPELINE_DIR"
echo "  Storage: $STORAGE_BASE"
echo ""
echo "To start processing:"
echo "  python3 process_video.py"
echo ""
echo "To run continuously:"
echo "  while true; do python3 process_video.py; sleep 10; done"
echo ""
echo "To run in background:"
echo "  nohup bash -c 'while true; do python3 process_video.py; sleep 10; done' &"
echo ""