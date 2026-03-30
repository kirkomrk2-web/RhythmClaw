#!/bin/bash
# ============================================================
#  RhythmClaw DJ Controller — Auto-Setup for macOS
#  Usage: bash ~/Downloads/rhythmclaw-setup.sh
# ============================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

clear
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo -e "  ${BOLD}🎧 RhythmClaw DJ Controller — Auto Setup${NC}"
echo -e "  Pioneer DDJ-FLX4 + Telegram + AI Mixing"
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo ""

ok()   { echo -e "${GREEN}  ✓ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
info() { echo -e "${CYAN}  → $1${NC}"; }
step() { echo ""; echo -e "${BOLD}[$1/8] $2${NC}"; }

# 1
step 1 "macOS"
echo "  $(sw_vers -productVersion) ($(uname -m))"
[[ "$(uname -m)" == "arm64" ]] && ok "Apple Silicon" || warn "Intel"

# 2
step 2 "Homebrew"
if command -v brew &>/dev/null; then ok "Homebrew installed"
else info "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  [[ "$(uname -m)" == "arm64" ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
  ok "Homebrew installed"
fi

# 3
step 3 "Python"
if command -v python3 &>/dev/null; then ok "Python $(python3 --version 2>&1 | awk '{print $2}')"
else info "Installing Python..."; brew install python@3.12; ok "Python installed"; fi

# 4
step 4 "Node.js"
if command -v node &>/dev/null; then ok "Node.js $(node --version)"
else info "Installing Node.js..."; brew install node; ok "Node.js installed"; fi

# 5
step 5 "Git"
if command -v git &>/dev/null; then ok "Git $(git --version | awk '{print $3}')"
else info "Installing Git..."; brew install git; ok "Git installed"; fi

# 6
step 6 "Audio & MIDI deps"
for pkg in portaudio ffmpeg libsndfile; do
  if brew list $pkg &>/dev/null 2>&1; then ok "$pkg"
  else info "Installing $pkg..."; brew install $pkg; ok "$pkg installed"; fi
done

# 7 — Fixed for zsh compatibility (no associative arrays)
step 7 "Python DJ libraries"
LIBS="python-rtmidi librosa aubio numpy scipy sounddevice soundfile"
LIBS2="python-telegram-bot supabase SpeechRecognition"

echo "  Installing core DJ libs..."
pip3 install --quiet $LIBS 2>/dev/null && ok "Core: rtmidi, librosa, aubio, numpy, scipy, sounddevice, soundfile" || warn "Some core libs failed — run manually: pip3 install $LIBS"

echo "  Installing bot & cloud libs..."
pip3 install --quiet $LIBS2 2>/dev/null && ok "Bot: telegram-bot, supabase, SpeechRecognition" || warn "Some bot libs failed — run manually: pip3 install $LIBS2"

# 8
step 8 "MIDI Controller"
python3 -c "
import rtmidi
ports = rtmidi.MidiIn().get_ports()
if not ports:
    print('  \033[1;33m⚠ No MIDI devices found. Connect DDJ-FLX4 via USB-C.\033[0m')
else:
    for p in ports:
        tag = '✓' if any(x in p.lower() for x in ['ddj','pioneer','flx']) else '·'
        print(f'  \033[0;32m{tag} {p}\033[0m')
" 2>/dev/null || warn "MIDI check failed — python-rtmidi may need manual install"

echo ""
echo -e "${GREEN}${BOLD}  ✓ Setup Complete!${NC}"
echo -e "  1. Connect DDJ-FLX4 via USB-C"
echo -e "  2. Open Chrome → Allow MIDI access"
echo -e "  3. Send /start to @RhythmClaw_bot"
echo ""
