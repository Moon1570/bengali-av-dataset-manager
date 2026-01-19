#!/bin/bash

# Docker Runner Script for Bengali Speech Pipeline
# Simplifies running the complete pipeline in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CONTAINER_NAME="bengali-pipeline"
IMAGE_NAME="${IMAGE_NAME:-moon1570/bengali-speech-pipeline:latest}"  # Use Docker Hub image by default
USE_GPU=false  # Default to CPU mode

# Function to print colored messages
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"
}

# Function to check if nvidia-docker is available
check_nvidia_docker() {
    if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        print_success "NVIDIA Docker support detected"
        return 0
    else
        print_warning "NVIDIA Docker support not detected. GPU acceleration will not be available."
        return 1
    fi
}

# Function to build Docker image
build_image() {
    print_info "Building Docker image..."
    docker build -t "$IMAGE_NAME" .
    print_success "Docker image built successfully"
}

# Function to start container
start_container() {
    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Container exists. Starting..."
        docker start "$CONTAINER_NAME"
        print_success "Container started"
        return 0
    fi
    
    print_info "Starting container..."
    
    # Use GPU if flag is set and available
    if [ "$USE_GPU" = true ]; then
        if check_nvidia_docker 2>/dev/null; then
            print_info "Starting with GPU support via docker-compose..."
            docker-compose up -d
            print_success "Container started with GPU support"
            return 0
        else
            print_error "GPU requested but NVIDIA Docker not available"
            print_info "Falling back to CPU mode..."
        fi
    fi
    
    # CPU mode (default)
    print_info "Starting in CPU-only mode"
    docker run -d --name "$CONTAINER_NAME" \
        -v "$(pwd)/downloads:/app/bengali-pipeline/downloads" \
        -v "$(pwd)/outputs:/app/bengali-pipeline/outputs" \
        -v "$(pwd)/logs:/app/bengali-pipeline/logs" \
        -v "$(pwd)/experiments:/app/bengali-pipeline/experiments" \
        -e SYNCNET_REPO=/app/syncnet_python \
        -e CURRENT_REPO=/app/bengali-pipeline \
        -e PYTHONUNBUFFERED=1 \
        -w /app/bengali-pipeline \
        "$IMAGE_NAME" \
        tail -f /dev/null
    print_success "Container started"
}

# Function to stop container
stop_container() {
    print_info "Stopping container..."
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker stop "$CONTAINER_NAME"
        print_success "Container stopped"
    else
        print_warning "Container not running"
    fi
}

# Function to run pipeline
run_pipeline() {
    local VIDEO_ID="$1"
    shift  # Remove first argument
    local ADDITIONAL_ARGS="$@"
    
    if [ -z "$VIDEO_ID" ]; then
        print_error "Video ID is required"
        echo "Usage: ./run_docker.sh run <VIDEO_ID> [additional flags]"
        exit 1
    fi
    
    print_info "Running pipeline for video: $VIDEO_ID"
    print_info "Additional arguments: $ADDITIONAL_ARGS"
    
    # Use -i instead of -it to avoid TTY requirement when called from scripts
    docker exec -i "$CONTAINER_NAME" bash -c "
        cd /app/bengali-pipeline && \
        ./complete_pipeline.sh $VIDEO_ID --syncnet-repo /app/syncnet_python $ADDITIONAL_ARGS
    "
    
    print_success "Pipeline execution completed"
}

# Function to enter container shell
enter_shell() {
    print_info "Entering container shell..."
    docker exec -it "$CONTAINER_NAME" bash
}

# Function to show logs
show_logs() {
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker logs -f "$CONTAINER_NAME"
    else
        print_error "Container not running"
    fi
}

# Function to clean up
cleanup() {
    print_info "Cleaning up..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    docker volume rm bengali-pipeline-syncnet-data bengali-pipeline-syncnet-results 2>/dev/null || true
    print_success "Cleanup completed"
}

# Function to show status
show_status() {
    print_info "Container status:"
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker ps -a --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}"
    else
        print_warning "Container does not exist"
    fi
    echo ""
    print_info "Disk usage:"
    docker system df
}

# Function to show help
show_help() {
    cat << EOF
${BLUE}Bengali Speech Pipeline - Docker Runner${NC}

${GREEN}Usage:${NC}
  ./run_docker.sh [--gpu] <command> [options]

${GREEN}Global Flags:${NC}
  ${YELLOW}--gpu${NC}            Enable GPU support (requires nvidia-docker, default: CPU mode)

${GREEN}Commands:${NC}
  ${YELLOW}build${NC}           Build the Docker image
  ${YELLOW}start${NC}           Start the Docker container
  ${YELLOW}stop${NC}            Stop the Docker container
  ${YELLOW}run${NC}             Run the pipeline for a video
  ${YELLOW}shell${NC}           Enter container shell
  ${YELLOW}logs${NC}            Show container logs
  ${YELLOW}status${NC}          Show container status
  ${YELLOW}cleanup${NC}         Stop container and remove volumes
  ${YELLOW}help${NC}            Show this help message

${GREEN}Examples:${NC}
  # Build and start (CPU mode - default)
  ./run_docker.sh build
  ./run_docker.sh start

  # Start with GPU support
  ./run_docker.sh --gpu start

  # Run pipeline with default settings (CPU mode)
  ./run_docker.sh run SSYouTubeonline

  # Run with GPU support
  ./run_docker.sh --gpu run SSYouTubeonline

${GREEN}Available Pipeline Flags:${NC}
  --silence-preset <PRESET>          Choose: very_sensitive, sensitive, balanced, conservative, very_conservative
  --custom-silence-thresh <FLOAT>    Custom silence threshold in dBFS (e.g., -35.0)
  --custom-min-silence <INT>         Custom minimum silence length in ms (e.g., 600)
  --reduce-noise                     Enable noise reduction (disabled by default)
  --transcription-model <MODEL>      Choose: google, whisper, both (default: google)
  --skip-step1                       Skip audio chunking
  --skip-step2                       Skip SyncNet filtering
  --skip-step3                       Skip directory organization
  --skip-step4                       Skip transcription

${GREEN}Requirements:${NC}
  - Docker installed
  - Docker Compose installed (optional, for GPU mode)
  - NVIDIA Docker (optional, for GPU acceleration with --gpu flag)
  - At least 10GB free disk space

${GREEN}Note:${NC}
  - Default mode is CPU-only (works on all platforms including macOS)
  - Use --gpu flag to enable GPU acceleration (requires nvidia-docker on Linux)

${GREEN}Directory Structure:${NC}
  - downloads/         Place your input videos here
  - outputs/           Processed results
  - experiments/       Experiment data
  - logs/              Pipeline logs

For more information, see README.md or PIPELINE_README.md
EOF
}

# Main script logic
main() {
    check_docker
    
    # Parse global flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --gpu)
                USE_GPU=true
                shift
                ;;
            build|start|stop|run|shell|logs|status|cleanup|help|--help|-h)
                # Command found, process it
                break
                ;;
            *)
                # Unknown flag or command
                break
                ;;
        esac
    done
    
    case "${1:-help}" in
        build)
            build_image
            ;;
        start)
            start_container
            ;;
        stop)
            stop_container
            ;;
        run)
            shift
            run_pipeline "$@"
            ;;
        shell)
            enter_shell
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
