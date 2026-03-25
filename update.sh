#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# MIDI Camera — Update Script
# Pulls latest code and reinstalls any new dependencies.
# ─────────────────────────────────────────────────────────────────────

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Find install dir
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f "app.py" ]]; then
    echo -e "${RED}[!] Run this from the midi-camera directory.${NC}"
    exit 1
fi

echo -e "${CYAN}[*] Updating MIDI Camera...${NC}"

# Pull latest
git pull --ff-only || {
    echo -e "${RED}[!] Git pull failed. You may have local changes.${NC}"
    echo -e "${YELLOW}    Try: git stash && git pull && git stash pop${NC}"
    exit 1
}

# Reinstall deps (in case requirements.txt changed)
source .venv/bin/activate
pip install -r requirements.txt -q

# Re-download models if missing
mkdir -p models
[[ ! -f "models/hand_landmarker.task" ]] && curl -sL -o "models/hand_landmarker.task" \
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
[[ ! -f "models/face_landmarker.task" ]] && curl -sL -o "models/face_landmarker.task" \
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

echo -e "${GREEN}[✓] MIDI Camera updated to latest version!${NC}"
echo -e "    Restart the app to use the new version."
