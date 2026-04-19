#!/bin/bash
# Deploy Monty to VPS
# Usage: ./deploy/deploy.sh [--purge]
#
# Prerequisites on VPS (one-time):
#   1. Docker + Docker Compose installed
#   2. Run the setup script first: ./deploy/vps-setup.sh

set -e

VPS="indrayudd@64.62.164.6"
REMOTE_DIR="/home/indrayudd/monty"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

PURGE_FLAG=""
if [ "$1" = "--purge" ]; then
    PURGE_FLAG="1"
    echo "⚠  Will purge all data on restart"
fi

echo "=== Building Docker image locally (linux/amd64) ==="
docker build --platform linux/amd64 -t monty:latest .

echo "=== Saving image (~1.5GB compressed) ==="
docker save monty:latest | gzip > /tmp/monty-image.tar.gz
echo "    Size: $(du -h /tmp/monty-image.tar.gz | cut -f1)"

echo "=== Creating remote directories ==="
ssh $VPS "mkdir -p $REMOTE_DIR/data $REMOTE_DIR/wiki"

echo "=== Uploading image to VPS ==="
scp /tmp/monty-image.tar.gz $VPS:/tmp/

echo "=== Uploading config files ==="
scp docker-compose.yml $VPS:$REMOTE_DIR/
scp .env $VPS:$REMOTE_DIR/.env

echo "=== Uploading wiki/ (initial seed) ==="
# Only sync wiki if remote wiki is empty (first deploy)
WIKI_COUNT=$(ssh $VPS "find $REMOTE_DIR/wiki -name '*.md' 2>/dev/null | wc -l")
if [ "$WIKI_COUNT" -lt 5 ] || [ -n "$PURGE_FLAG" ]; then
    echo "    Syncing wiki/ to VPS (first deploy or purge)..."
    rsync -az --delete wiki/ $VPS:$REMOTE_DIR/wiki/
else
    echo "    Wiki already populated ($WIKI_COUNT files), skipping sync"
fi

echo "=== Loading Docker image on VPS ==="
ssh $VPS "docker load < /tmp/monty-image.tar.gz && rm /tmp/monty-image.tar.gz"

echo "=== Stopping old container ==="
ssh $VPS "cd $REMOTE_DIR && docker compose down 2>/dev/null || true"

echo "=== Starting Monty ==="
if [ -n "$PURGE_FLAG" ]; then
    ssh $VPS "cd $REMOTE_DIR && MONTY_PURGE=1 docker compose up -d"
else
    ssh $VPS "cd $REMOTE_DIR && docker compose up -d"
fi

echo "=== Waiting for startup ==="
sleep 8
ssh $VPS "docker logs monty --tail 15"

echo ""
echo "============================================"
echo "  Deployed!"
echo "  https://montyops.duckdns.org"
echo "============================================"

# Cleanup
rm -f /tmp/monty-image.tar.gz
