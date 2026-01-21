#!/bin/bash

# Test Docker Setup
# Verifies that the dataset manager can run Docker properly

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Testing Docker Setup..."
echo "================================"

# Test 1: Check if Docker is running
echo -n "1. Checking Docker... "
if docker info &> /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Test 2: Check if image exists
echo -n "2. Checking Docker image... "
if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "moon1570/bengali-speech-pipeline:latest"; then
    echo -e "${GREEN}✓ Found${NC}"
    docker images --format "   {{.Repository}}:{{.Tag}} ({{.Size}})" | grep bengali
else
    echo -e "${RED}✗ Not found${NC}"
    echo "Please build or pull the image first"
    exit 1
fi

# Test 3: Check directories
echo -n "3. Checking directories... "
mkdir -p data/downloads data/outputs data/storage
if [[ -d "data/downloads" && -d "data/outputs" ]]; then
    echo -e "${GREEN}✓ Created${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    exit 1
fi

# Test 4: Test Docker volume mounts
echo -n "4. Testing volume mounts... "
DOWNLOADS_DIR="$(pwd)/data/downloads"
OUTPUTS_DIR="$(pwd)/data/outputs"

docker run --rm \
    -v "${DOWNLOADS_DIR}:/app/bengali-pipeline/downloads" \
    -v "${OUTPUTS_DIR}:/app/bengali-pipeline/outputs" \
    moon1570/bengali-speech-pipeline:latest \
    ls /app/bengali-pipeline &> /dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Working${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    exit 1
fi

# Test 5: Check .env configuration
echo -n "5. Checking .env file... "
if grep -q "DOCKER_IMAGE=moon1570/bengali-speech-pipeline:latest" .env; then
    echo -e "${GREEN}✓ Configured${NC}"
else
    echo -e "${YELLOW}⚠ Update needed${NC}"
    echo "   Add to .env: DOCKER_IMAGE=moon1570/bengali-speech-pipeline:latest"
fi

echo ""
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "System is ready to process videos."
echo "Start the API server with: start_dev.sh"
