#!/bin/bash
# Daily sync script wrapper for scheduled tasks

LOG_DIR="$HOME/.a-share-sync-logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/sync-$(date +%Y%m%d-%H%M%S).log"

CONDA_BASE="$HOME/miniconda3"
SYNC_SCRIPT="$(cd "$(dirname "$0")" && pwd)/sync.py"

echo "=== Sync started at $(date) ===" | tee "$LOG"

# Activate conda and run
source "$CONDA_BASE/bin/activate" akshare 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate conda env 'akshare'" | tee -a "$LOG"
    exit 1
fi

python -u "$SYNC_SCRIPT" 2>&1 | tee -a "$LOG"

echo "=== Sync finished at $(date) ===" | tee -a "$LOG"

# Cleanup logs older than 30 days
find "$LOG_DIR" -name "sync-*.log" -mtime +30 -delete
