# Docker Setup Guide

## Overview
This system uses a Docker container to process videos. The pipeline is completely self-contained in the Docker image - you don't need the pipeline source code to run this system.

## Prerequisites
- Docker installed and running
- Docker image built or pulled

## Option 1: Build Docker Image (if you have pipeline source)

If you have the Bengali pipeline source code:

```bash
# Navigate to the pipeline repository
cd /path/to/bengali-speech-audio-visual-dataset

# Build the Docker image
docker build -t bengali-pipeline:latest .
```

## Option 2: Pull Pre-built Image (recommended for users)

```bash
# Pull from Docker registry (when available)
docker pull your-registry/bengali-pipeline:latest
```

## Verify Installation

```bash
# Check if image exists
docker images | grep bengali-pipeline

# Expected output:
# bengali-pipeline    latest    abc123def456    2 hours ago    2.5GB
```

## How It Works

The dataset manager runs Docker with volume mounts:

```bash
docker run --rm \
  -v /path/to/downloads:/workspace/downloads \
  -v /path/to/outputs:/workspace/outputs \
  bengali-pipeline:latest \
  process VIDEO_ID --preset medium --transcription-model google
```

**No PIPELINE_DIR needed!** Everything runs through Docker with local directories.

## Directory Structure

```
bengali-av-dataset-manager/
├── data/
│   ├── downloads/     ← Input videos go here
│   ├── outputs/       ← Processed results appear here
│   └── storage/       ← Final approved chunks
```

## Troubleshooting

### Image not found
```bash
# Check what images you have
docker images

# If bengali-pipeline is missing, build or pull it
```

### Permission denied
```bash
# Ensure Docker has access to the data directories
# On Mac: Docker Desktop → Settings → Resources → File Sharing
```

### Container fails immediately
```bash
# Check Docker logs
docker logs <container-id>

# Test image manually
docker run --rm bengali-pipeline:latest --help
```

## Configuration

Update `.env` file:

```bash
# Docker image name (must match what you built/pulled)
DOCKER_IMAGE=bengali-pipeline:latest

# Local directories (relative to project root)
DOWNLOADS_DIR=./data/downloads
OUTPUTS_DIR=./data/outputs
STORAGE_BASE=./data/storage
```

## What Changed?

**OLD (complex):**
- Required separate pipeline repository
- Copied files between repos
- Ran scripts from external directory
- Path configuration nightmare

**NEW (simple):**
- Self-contained Docker image
- Direct volume mounts
- No external dependencies
- Works on any machine with Docker
