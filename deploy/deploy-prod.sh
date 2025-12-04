#!/bin/bash
#
# Deploy Trip Tools to production droplet
#
# Prerequisites:
#   - Docker running locally
#   - Docker image built (make docker-build)
#   - Docker image saved (make docker-push)
#   - SSH access to production droplet configured
#

set -e  # Exit on first error

# Configuration
DEPLOY_HOST="root@triptools.net"
DEPLOY_PATH="/opt/triptools"
TT_VERSION=$(cat TT_VERSION)
IMAGE_FILE="/tmp/tt-docker-image-${TT_VERSION}.tar.gz"

echo "=== Deploying Trip Tools ${TT_VERSION} to production ==="

# Pre-flight checks
echo "Checking prerequisites..."

if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker and try again."
    exit 1
fi

if [ ! -f "$IMAGE_FILE" ]; then
    echo "ERROR: Docker image not found at ${IMAGE_FILE}"
    echo "       Run 'make docker-push' first."
    exit 1
fi

if [ ! -f ".private/env/docker-compose.production.env" ]; then
    echo "ERROR: Production environment file not found."
    exit 1
fi

# Copy deployment files to droplet
echo "Copying deployment files to droplet..."
scp .private/env/docker-compose.production.env "${DEPLOY_HOST}:${DEPLOY_PATH}/triptools.env"
scp .private/env/production.sh "${DEPLOY_HOST}:${DEPLOY_PATH}/triptools.sh"
scp deploy/docker-compose.production.yml "${DEPLOY_HOST}:${DEPLOY_PATH}/docker-compose.yml"

# Copy Docker image to droplet
echo "Copying Docker image to droplet (this may take a minute)..."
scp "$IMAGE_FILE" "${DEPLOY_HOST}:/tmp/"

# Load image and restart services on droplet
echo "Loading image and restarting services on droplet..."
ssh "$DEPLOY_HOST" "
    set -e
    gunzip -c /tmp/tt-docker-image-${TT_VERSION}.tar.gz | docker load
    cd ${DEPLOY_PATH}
    TT_VERSION=${TT_VERSION} docker-compose --env-file triptools.env down || true
    TT_VERSION=${TT_VERSION} docker-compose --env-file triptools.env up -d
    rm /tmp/tt-docker-image-${TT_VERSION}.tar.gz
"

echo ""
echo "=== Deployment complete! ==="
echo ""
echo "Verify the deployment:"
echo "  curl -I https://triptools.net"
echo "  ssh ${DEPLOY_HOST} 'docker ps'"
echo ""

# Prompt to clean up local temp file
IMAGE_SIZE=$(du -h "$IMAGE_FILE" | cut -f1)
read -p "Remove local image file ${IMAGE_FILE} (${IMAGE_SIZE})? [y/N] " -n 1 -r || true
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm "$IMAGE_FILE"
    echo "Removed."
else
    echo "Keeping ${IMAGE_FILE}"
fi
