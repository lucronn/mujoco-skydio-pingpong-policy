#!/usr/bin/env bash
# progression sync daemon: automatically detects new runs, converts gifs, indexes, and pushes to git.
# Runs in the background (nohup / setsid).

REPO_DIR="/mnt/openfoam/pingpong-venv/progression/mujoco-skydio-pingpong-policy"
WORKSPACE_DIR="/mnt/openfoam/pingpong-venv/progression"

echo "Sync daemon started: checking for new runs every 10 minutes..."

while true; do
  echo "Checking for updates at $(date)..."
  
  # 1. Copy new runs
  for run in "$WORKSPACE_DIR"/202*; do
    if [ -d "$run" ]; then
      name=$(basename "$run")
      if [ ! -d "$REPO_DIR/data/$name" ]; then
        echo "Found new run directory: $name. Copying to repo..."
        cp -r "$run" "$REPO_DIR/data/"
      fi
    fi
  done
  
  # 2. Copy new staging directories
  if [ -d "$WORKSPACE_DIR/_staging" ]; then
    mkdir -p "$REPO_DIR/data/_staging"
    for stage in "$WORKSPACE_DIR"/_staging/202*; do
      if [ -d "$stage" ]; then
        name=$(basename "$stage")
        if [ ! -d "$REPO_DIR/data/_staging/$name" ]; then
          echo "Found new staging directory: $name. Copying to repo..."
          cp -r "$stage" "$REPO_DIR/data/_staging/"
        fi
      fi
    done
  fi
  
  # 3. Copy overnight logs
  if [ -d "$WORKSPACE_DIR/overnight_log" ]; then
    mkdir -p "$REPO_DIR/data/overnight_log"
    cp "$WORKSPACE_DIR"/overnight_log/evolve_continuous.log "$WORKSPACE_DIR"/overnight_log/evolve_volley_last.json "$WORKSPACE_DIR"/overnight_log/progression_write.log "$WORKSPACE_DIR"/overnight_log/STATUS.md "$WORKSPACE_DIR"/overnight_log/WHERE_WE_ARE.md "$WORKSPACE_DIR"/overnight_log/best.json "$REPO_DIR/data/overnight_log/" 2>/dev/null || true
  fi
  
  # 4. Run GIF converter, indexer, and git push
  cd "$REPO_DIR"
  
  # Run GIF converter and indexer
  python3 convert_all_to_gif.py
  python3 process_data.py
  
  # Check if git has changes
  if [ -n "$(git status --porcelain)" ]; then
    echo "Changes detected. Committing and pushing..."
    git add .
    git commit -m "Auto-sync: publish latest progression runs and training logs"
    git push origin main
    echo "Push complete."
  else
    echo "No new changes to push."
  fi
  
  echo "Sleeping for 10 minutes..."
  sleep 600
done
