#!/bin/bash
# ============================================================
#  RhythmClaw DJ Controller — Auto-Setup for macOS
#  Compatible with: Mac Mini M4, MacBook Air M4, any Apple Silicon
#
#  USAGE (copy-paste this ONE line in Terminal):
#  curl -sL https://raw.githubusercontent.com/kirkomrk2-web/RhythmClaw/main/setup.sh | bash
#
#  OR if you downloaded this file:
#  bash ~/Downloads/rhythmclaw-setup.sh
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

clear
echo ""
echo "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo "${CYAN}║${NC}  ${BOLD}🎧 RhythmClaw DJ Controller — Auto Setup${NC}                 ${CYAN}║${NC}"
echo "${CYAN}║${NC}     Pioneer DDJ-FLX4 + Telegram + AI Mixing              ${CYAN}║${NC}"
echo "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

check_mark() { echo -e "${GREEN}  ✓ $1${NC}"; }
warning()    { echo -e "${YELLOW}  ⚠ $1${NC}"; }
installing() { echo -e "${CYAN}  → Installing $1...${NC}"; }
step()       { echo ""; echo -e "${BOLD}[$1/8] $2${NC}"; echo "  ────────────────────────────"; }

# 1. Check macOS
step 1 "Checking macOS compatibility"
SW_VERSION=$(sw_vers -productVersion 2>/dev/null || echo "unknown")
ARCH=$(uname -m)
echo "  macOS $SW_VERSION ($ARCH)"
if [[ "$ARCH" == "arm64" ]]; then
  check_mark "Apple Silicon detected"
else
  warning "Intel Mac detected"
fi

# 2. Homebrew
step 2 "Homebrew package manager"
if command -v brew &>/dev/null; then
  check_mark "Homebrew already installed"
else
  installing "Homebrew"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ "$ARCH" == "arm64" ]]; then
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
  check_mark "Homebrew installed"
fi

# 3. Python
step 3 "Python 3.12+"
if command -v python3 &>/dev/null; then
  PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
  check_mark "Python $PY_VERSION"
else
  installing "Python 3.12"
  brew install python@3.12
  check_mark "Python installed"
fi

# 4. Node.js
step 4 "Node.js"
if command -v node &>/dev/null; then
  check_mark "Node.js $(node --version)"
else
  installing "Node.js"
  brew install node
  check_mark "Node.js installed"
fi

# 5. Git
step 5 "Git"
if command -v git &>/dev/null; then
  check_mark "Git $(git --version | awk '{print $3}')"
else
  installing "Git"
  brew install git
  check_mark "Git installed"
fi

# 6. System audio deps
step 6 "Audio & MIDI dependencies"
for pkg in portaudio ffmpeg libsndfile; do
  if brew list $pkg &>/dev/null 2>&1; then
    check_mark "$pkg"
  else
    installing "$pkg"
    brew install $pkg
    check_mark "$pkg installed"
  fi
done

# 7. Python libraries
step 7 "Python DJ & MIDI libraries"
pip3 install --quiet --upgrade pip 2>/dev/null

declare -A LIBS=(
  ["python-rtmidi"]="MIDI I/O"
  ["librosa"]="BPM & key detection"
  ["aubio"]="Real-time beat tracking"
  ["numpy"]="Scientific computing"
  ["scipy"]="Signal processing"
  ["sounddevice"]="Audio playback"
  ["soundfile"]="Audio file I/O"
  ["python-telegram-bot"]="Telegram Bot API"
  ["supabase"]="Database client"
  ["SpeechRecognition"]="Voice commands"
)

for lib in "${!LIBS[@]}"; do
  if pip3 install --quiet "$lib" 2>/dev/null; then
    check_mark "$lib (${LIBS[$lib]})"
  else
    warning "$lib failed — try manually: pip3 install $lib"
  fi
done

# 8. Check MIDI
step 8 "Checking MIDI controller"
python3 -c "
import rtmidi
midi_in = rtmidi.MidiIn()
ports = midi_in.get_ports()
if not ports:
    print('  \033[1;33m⚠ No MIDI devices found. Connect DDJ-FLX4 via USB-C.\033[0m')
else:
    for p in ports:
        icon = '✓' if any(x in p.lower() for x in ['ddj','pioneer','flx']) else '·'
        print(f'  \033[0;32m{icon} {p}\033[0m')
" 2>/dev/null || warning "python-rtmidi not available for MIDI check"

# Summary
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}${BOLD}✓ RhythmClaw Setup Complete!${NC}                             ${CYAN}║${NC}"
echo -e "${CYAN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  1. Connect DDJ-FLX4 via USB-C                            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  2. Open Chrome → rhythmclaw.dev → Allow MIDI             ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  3. Send /start to @RhythmClaw_bot in Telegram            ${CYAN}║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
