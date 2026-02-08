#!/usr/bin/env bash
set -eu

# Load configuration from .env file (default to .env in same directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$SCRIPT_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env file not found at $ENV_FILE"
  echo "Create a .env file by copying .env.example and updating values"
  exit 1
fi

source "$ENV_FILE"

# Validate required variables
for var in PI_HOST PI_PATH LOCAL_PATH PYTHON_CMD; do
  if [[ -z "${!var:-}" ]]; then
    echo "Error: $var not set in $ENV_FILE"
    exit 1
  fi
done

sync_and_restart() {
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📡 Syncing to Pi..."
  
  # Build rsync command with exclusions
  local rsync_cmd="rsync -avz"
  for exclude in $EXCLUDES; do
    rsync_cmd="$rsync_cmd --exclude '$exclude'"
  done
  rsync_cmd="$rsync_cmd \"$LOCAL_PATH/\" \"$PI_HOST:$PI_PATH/\""
  
  eval "$rsync_cmd" || {
    echo "❌ rsync failed"
    return 1
  }
  
  echo "🔄 Restarting bird_viewer.py on Pi..."
  ssh "$PI_HOST" "pkill -f bird_viewer.py || true; sleep 1" || true
  ssh -f "$PI_HOST" "cd '$PI_PATH' && python3 bird_viewer.py > /tmp/bird_viewer.log 2>&1" || true
  sleep 2
  
  echo "✅ Synced and restarted at $(date +'%Y-%m-%d %H:%M:%S')"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

echo "🐦 Bird Pi Detector - Sync Watcher"
echo "Watching: $LOCAL_PATH"
echo "Target: $PI_HOST:$PI_PATH"
echo "Press Ctrl+C to stop"
echo ""

# Initial sync
sync_and_restart

echo ""
echo "👀 Watching for file changes (this should stay running)..."
echo ""

# Watch for changes
fswatch -o "$LOCAL_PATH" | while read -r _; do
  sync_and_restart
done

echo "⚠️  Watch loop ended (this shouldn't happen)"
