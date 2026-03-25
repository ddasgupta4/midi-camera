#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# MIDI Camera — Install Script
# Turns your webcam into a MIDI chord controller.
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/ddasgupta4/midi-camera/master/install.sh | bash
#
# Or clone first, then run:
#   git clone https://github.com/ddasgupta4/midi-camera.git
#   cd midi-camera && bash install.sh
# ─────────────────────────────────────────────────────────────────────

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       🎹 MIDI Camera Installer       ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# ── Check macOS ──
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}[!] MIDI Camera only runs on macOS.${NC}"
    exit 1
fi

# ── Install dir ──
INSTALL_DIR="$HOME/midi-camera"

if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo -e "${GREEN}[✓] Found existing install at $INSTALL_DIR${NC}"
    cd "$INSTALL_DIR"
    echo -e "${YELLOW}[*] Pulling latest changes...${NC}"
    git pull --ff-only || { echo -e "${RED}[!] Git pull failed. Try: cd $INSTALL_DIR && git stash && git pull${NC}"; exit 1; }
elif [[ -f "app.py" && -f "menubar.py" ]]; then
    # Already inside the repo (cloned manually)
    INSTALL_DIR="$(pwd)"
    echo -e "${GREEN}[✓] Running from existing repo: $INSTALL_DIR${NC}"
else
    echo -e "${YELLOW}[*] Cloning MIDI Camera to $INSTALL_DIR ...${NC}"
    git clone https://github.com/ddasgupta4/midi-camera.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ── Homebrew ──
if ! command -v brew &>/dev/null; then
    echo -e "${YELLOW}[*] Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for this session
    eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || eval "$(/usr/local/bin/brew shellenv)" 2>/dev/null
fi

# ── Python 3.12 ──
PYTHON=""
for p in python3.12 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
    if command -v "$p" &>/dev/null; then
        PYTHON="$p"
        break
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo -e "${YELLOW}[*] Installing Python 3.12 via Homebrew...${NC}"
    brew install python@3.12
    PYTHON="/opt/homebrew/bin/python3.12"
fi

echo -e "${GREEN}[✓] Python: $($PYTHON --version)${NC}"

# ── Virtual environment ──
if [[ ! -d ".venv" ]]; then
    echo -e "${YELLOW}[*] Creating virtual environment...${NC}"
    "$PYTHON" -m venv .venv
fi

source .venv/bin/activate
echo -e "${GREEN}[✓] Virtual environment activated${NC}"

# ── Dependencies ──
echo -e "${YELLOW}[*] Installing Python dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}[✓] Dependencies installed${NC}"

# ── Model files ──
mkdir -p models
HAND_MODEL="models/hand_landmarker.task"
FACE_MODEL="models/face_landmarker.task"

if [[ ! -f "$HAND_MODEL" ]]; then
    echo -e "${YELLOW}[*] Downloading hand tracking model...${NC}"
    curl -sL -o "$HAND_MODEL" \
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
fi

if [[ ! -f "$FACE_MODEL" ]]; then
    echo -e "${YELLOW}[*] Downloading face tracking model...${NC}"
    curl -sL -o "$FACE_MODEL" \
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
fi

echo -e "${GREEN}[✓] Models ready${NC}"

# ── IAC Driver check ──
echo ""
echo -e "${YELLOW}[!] IMPORTANT: You need to enable IAC Driver for MIDI output.${NC}"
echo -e "    Open ${CYAN}Audio MIDI Setup${NC} (search in Spotlight)"
echo -e "    Go to ${CYAN}Window > Show MIDI Studio${NC}"
echo -e "    Double-click ${CYAN}IAC Driver${NC}, check ${CYAN}'Device is online'${NC}"
echo ""

# ── Desktop shortcut ──
SHORTCUT="$HOME/Desktop/MIDI Camera.command"
cat > "$SHORTCUT" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source .venv/bin/activate
python menubar.py
EOF
chmod +x "$SHORTCUT"
echo -e "${GREEN}[✓] Desktop shortcut created: MIDI Camera.command${NC}"

# ── Done ──
echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Installation complete!        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "  To launch: Double-click ${CYAN}'MIDI Camera'${NC} on your Desktop"
echo -e "  Or run:    ${CYAN}cd $INSTALL_DIR && source .venv/bin/activate && python menubar.py${NC}"
echo ""
echo -e "  To update: ${CYAN}cd $INSTALL_DIR && bash update.sh${NC}"
echo -e "             Or use the Update button in the menu bar app."
echo ""
