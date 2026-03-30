# 🎧 RhythmClaw — AI DJ Controller

Pioneer DDJ-FLX4 meets AI automation. Real-time beat analysis, crossfading, and smart track recommendations via Telegram Mini App.

## Quick Setup (Mac)

```bash
bash setup.sh
```

Or one-liner:
```bash
curl -sL https://raw.githubusercontent.com/kirkomrk2-web/RhythmClaw/main/setup.sh | bash
```

## Features

- 🎛️ Dual vinyl turntables with touch scratch (Web Audio API)
- 🎚️ Crossfader, BPM display, waveform visualization
- 🪄 Automix mode (AI-powered track selection & mixing)
- 🎧 FX panel (Gate, Flanger, Echo, Reverb)
- 🎹 8 color-coded sample pads
- 📡 DDJ-FLX4 auto-detection via Web MIDI API
- 🤖 Telegram Bot control (@RhythmClaw_bot)
- 🗃️ Supabase backend for tracks, play history, favorites
- 🎙️ Voice commands via Telegram (Whisper transcription)

## Tech Stack

- Frontend: HTML/CSS/JS (no frameworks)
- Backend: Express 5 + Supabase
- Audio: Web Audio API
- MIDI: Web MIDI API
- Bot: Telegram Bot API
- Analysis: librosa, aubio, python-rtmidi

## Part of the [Wallestars](https://github.com/Wallesters-org) ecosystem
