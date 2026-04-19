#!/bin/bash
set -e

# Handle --purge flag
if [ "$1" = "--purge" ] || [ "$MONTY_PURGE" = "1" ]; then
    echo "[monty] Purging all data..."
    rm -f data/monty.db data/monty.db-wal data/monty.db-shm
    # Wipe wiki generated content (keep personas + skeleton)
    find wiki/behavioral -name "*.md" ! -name "_index.md" -delete 2>/dev/null || true
    find wiki/behavioral/_edges -name "*.md" -delete 2>/dev/null || true
    find wiki/students -name "*.md" -delete 2>/dev/null || true
    find wiki/sources/openalex -name "*.md" -delete 2>/dev/null || true
    echo "[monty] Purge complete. Starting fresh."
    shift 2>/dev/null || true
fi

# Ensure data dirs exist
mkdir -p data wiki/behavioral/_edges wiki/students wiki/sources/openalex wiki/personas

echo "[monty] Starting all services..."
exec "$@"
