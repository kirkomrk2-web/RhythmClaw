#!/bin/bash
# ════════════════════════════════════════════════════════════
#  RhythmClaw DJ Controller — Auto-Setup v3.0 for macOS
#  Tested on: Mac Mini M4 (macOS 26.2, arm64, Python 3.14)
#
#  Usage:  bash ~/Downloads/setup.sh
#  Or:     bash <(curl -sL https://raw.githubusercontent.com/kirkomrk2-web/RhythmClaw/main/setup.sh)
# ════════════════════════════════════════════════════════════
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'

ok()   { echo -e "${GREEN}  ✓ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
info() { echo -e "${CYAN}  → $1${NC}"; }
fail() { echo -e "${RED}  ✗ $1${NC}"; }
step() { echo ""; echo -e "${BOLD}[$1/8] $2${NC}"; }

clear
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo -e "  ${BOLD}🎧 RhythmClaw DJ Controller — Setup v3.0${NC}"
echo -e "  Pioneer DDJ-FLX4 + Telegram + AI Mixing"
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"

# ── 1. macOS ──
step 1 "macOS compatibility"
OS_VER=$(sw_vers -productVersion 2>/dev/null || echo "unknown")
ARCH=$(uname -m)
echo "  macOS $OS_VER ($ARCH)"
[[ "$ARCH" == "arm64" ]] && ok "Apple Silicon" || warn "Intel Mac"

# ── 2. Homebrew ──
step 2 "Homebrew"
if command -v brew &>/dev/null; then
  ok "Homebrew $(brew --version 2>/dev/null | head -1 | awk '{print $2}')"
else
  info "Installing Homebrew (requires password)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  [[ "$ARCH" == "arm64" ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
  ok "Homebrew installed"
fi

# ── 3. Python ──
step 3 "Python 3.12+"
if command -v python3 &>/dev/null; then
  ok "Python $(python3 --version 2>&1 | awk '{print $2}')"
else
  info "Installing Python..."; brew install python@3.12; ok "Python installed"
fi

# ── 4. Node.js ──
step 4 "Node.js"
if command -v node &>/dev/null; then
  ok "Node.js $(node --version)"
else
  info "Installing Node.js..."; brew install node; ok "Node.js installed"
fi

# ── 5. Git ──
step 5 "Git"
if command -v git &>/dev/null; then
  ok "Git $(git --version | awk '{print $3}')"
else
  info "Installing Git..."; brew install git; ok "Git installed"
fi

# ── 6. System audio & MIDI dependencies ──
step 6 "Audio & MIDI dependencies"
BREW_NEED=""
for pkg in portaudio ffmpeg libsndfile; do
  if brew list "$pkg" &>/dev/null 2>&1; then
    ok "$pkg"
  else
    BREW_NEED="$BREW_NEED $pkg"
  fi
done
if [ -n "$BREW_NEED" ]; then
  info "Installing:$BREW_NEED"
  brew install $BREW_NEED
  ok "All audio dependencies installed"
fi

# ── 7. Python venv + DJ libraries ──
step 7 "Python virtual environment + DJ libraries"
VENV="$HOME/rhythmclaw-env"

# Create venv if missing
if [ ! -d "$VENV" ]; then
  info "Creating virtual environment at $VENV"
  python3 -m venv "$VENV"
  ok "venv created"
else
  ok "venv exists at $VENV"
fi

# Activate
source "$VENV/bin/activate"
ok "Activated ($(python3 --version 2>&1))"

# Upgrade pip silently
pip install --quiet --upgrade pip 2>/dev/null

# Install libs one by one for clear status
PACKAGES=(
  "python-rtmidi:MIDI controller I/O"
  "numpy:Scientific computing"
  "scipy:Signal processing"
  "librosa:BPM & key detection"
  "sounddevice:Audio playback"
  "soundfile:Audio file I/O"
  "python-telegram-bot:Telegram Bot API"
  "supabase:Database client"
  "SpeechRecognition:Voice commands"
)

FAILED=0
for entry in "${PACKAGES[@]}"; do
  PKG="${entry%%:*}"
  DESC="${entry##*:}"
  if pip show "$PKG" &>/dev/null 2>&1; then
    ok "$PKG ($DESC)"
  else
    info "Installing $PKG..."
    if pip install "$PKG" 2>/dev/null; then
      ok "$PKG ($DESC)"
    else
      fail "$PKG — run manually: pip install $PKG"
      FAILED=$((FAILED + 1))
    fi
  fi
done

if [ $FAILED -gt 0 ]; then
  warn "$FAILED packages failed — check internet and retry"
else
  ok "All Python libraries installed"
fi

# ── 8. MIDI controller check ──
step 8 "MIDI controller detection"
python3 << 'PYCHECK' 2>/dev/null
import rtmidi
ports = rtmidi.MidiIn().get_ports()
if not ports:
    print('  \033[1;33m⚠ No MIDI devices. Connect DDJ-FLX4 via USB-C and re-run.\033[0m')
else:
    for p in ports:
        if any(x in p.lower() for x in ['ddj','pioneer','flx']):
            print(f'  \033[0;32m✓ {p} — Connected!\033[0m')
        else:
            print(f'  \033[0;36m· {p}\033[0m')
PYCHECK
if [ $? -ne 0 ]; then warn "MIDI check skipped — python-rtmidi not available"; fi

# ── Auto-activate venv in new terminals (safe, conditional) ──
ZSHRC="$HOME/.zshrc"
MARKER="# RhythmClaw venv auto-activate"
if ! grep -q "$MARKER" "$ZSHRC" 2>/dev/null; then
  echo "" >> "$ZSHRC"
  echo "$MARKER" >> "$ZSHRC"
  echo '[ -d "$HOME/rhythmclaw-env" ] && source "$HOME/rhythmclaw-env/bin/activate" 2>/dev/null' >> "$ZSHRC"
  ok "Added venv auto-activate to .zshrc (safe — only activates if venv exists)"
else
  ok "venv auto-activate already in .zshrc"
fi

# ── Summary ──
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}${BOLD}✓ RhythmClaw Setup Complete!${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo -e "  1. DDJ-FLX4 should show as connected above"
echo -e "  2. Open Chrome/Safari → go to the DJ web app"
echo -e "  3. Allow MIDI access when browser prompts"
echo -e "  4. Send ${BOLD}/start${NC} to ${BOLD}@RhythmClaw_bot${NC} in Telegram"
echo ""
echo -e "  ${CYAN}Telegram:${NC} https://t.me/RhythmClaw_bot"
echo -e "  ${CYAN}GitHub:${NC}   https://github.com/kirkomrk2-web/RhythmClaw"
echo -e "  ${CYAN}venv:${NC}     source ~/rhythmclaw-env/bin/activate"
echo ""
