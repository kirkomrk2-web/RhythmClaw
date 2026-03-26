# RhythmClaw — DDJ-FLX4 MIDI Commands Reference

Complete reference of every MIDI command exposed by `midi_server.py`.
All hex values follow the **Pioneer DDJ-FLX4 MIDI Message List**.

---

## Transport

| Command | API Endpoint | MIDI Message | Channel | Note/CC | Description |
|---|---|---|---|---|---|
| Play / Pause (Deck 1) | `POST /api/v1/deck/1/play` | Note On → Off | Ch 1 (0x90) | Note 0x0B | Toggle playback on Deck 1 |
| Play / Pause (Deck 2) | `POST /api/v1/deck/2/play` | Note On → Off | Ch 2 (0x91) | Note 0x0B | Toggle playback on Deck 2 |
| Cue (Deck 1) | `POST /api/v1/deck/1/cue` | Note On → Off | Ch 1 (0x90) | Note 0x0C | Cue button on Deck 1 |
| Cue (Deck 2) | `POST /api/v1/deck/2/cue` | Note On → Off | Ch 2 (0x91) | Note 0x0C | Cue button on Deck 2 |
| Beat Sync (Deck 1) | `POST /api/v1/deck/1/sync` | Note On → Off | Ch 1 (0x90) | Note 0x58 | Beat-sync on Deck 1 |
| Beat Sync (Deck 2) | `POST /api/v1/deck/2/sync` | Note On → Off | Ch 2 (0x91) | Note 0x58 | Beat-sync on Deck 2 |
| Load Track (Deck 1) | `POST /api/v1/deck/1/load` | Note On → Off | Ch 1 (0x90) | Note 0x46 | Load selected track to Deck 1 |
| Load Track (Deck 2) | `POST /api/v1/deck/2/load` | Note On → Off | Ch 2 (0x91) | Note 0x46 | Load selected track to Deck 2 |
| **Slip Toggle (Deck 1)** | `POST /api/v1/deck/1/slip/toggle` | Note On→Off / Note Off | Ch 1 (0x90/0x80) | Note 0x40 | Toggle slip mode ON (note_trigger) or OFF (explicit note_off). Fixes bug where slip kept playing after button unclick. |
| **Slip Toggle (Deck 2)** | `POST /api/v1/deck/2/slip/toggle` | Note On→Off / Note Off | Ch 2 (0x91/0x81) | Note 0x40 | Same fix for Deck 2. |
| **Slip State (Deck 1)** | `GET /api/v1/deck/1/slip` | — | — | — | Returns `{"deck":1,"slip":true/false}` |
| **Slip State (Deck 2)** | `GET /api/v1/deck/2/slip` | — | — | — | Returns `{"deck":2,"slip":true/false}` |
| Tempo (Deck 1) | `POST /api/v1/deck/1/tempo` | CC | Ch 1 (0xB0) | CC 0x00 | Set tempo slider (0-127) |
| Tempo (Deck 2) | `POST /api/v1/deck/2/tempo` | CC | Ch 2 (0xB1) | CC 0x00 | Set tempo slider (0-127) |
| Jog Nudge (Deck 1) | `POST /api/v1/deck/1/jog` | CC | Ch 1 (0xB0) | CC 0x22 | Jog-wheel nudge (0-127) |
| Jog Nudge (Deck 2) | `POST /api/v1/deck/2/jog` | CC | Ch 2 (0xB1) | CC 0x22 | Jog-wheel nudge (0-127) |

## Performance Pads — Hot Cue

| Command | API Endpoint | MIDI Message | Channel | Note/CC | Description |
|---|---|---|---|---|---|
| Hot Cue 1 | `POST /api/v1/deck/{deck}/hotcue/1` | Note On → Off | Ch 1/2 | Note 0x00 | Trigger Hot Cue point 1 |
| Hot Cue 2 | `POST /api/v1/deck/{deck}/hotcue/2` | Note On → Off | Ch 1/2 | Note 0x01 | Trigger Hot Cue point 2 |
| Hot Cue 3 | `POST /api/v1/deck/{deck}/hotcue/3` | Note On → Off | Ch 1/2 | Note 0x02 | Trigger Hot Cue point 3 |
| Hot Cue 4 | `POST /api/v1/deck/{deck}/hotcue/4` | Note On → Off | Ch 1/2 | Note 0x03 | Trigger Hot Cue point 4 |
| Hot Cue 5 | `POST /api/v1/deck/{deck}/hotcue/5` | Note On → Off | Ch 1/2 | Note 0x04 | Trigger Hot Cue point 5 |
| Hot Cue 6 | `POST /api/v1/deck/{deck}/hotcue/6` | Note On → Off | Ch 1/2 | Note 0x05 | Trigger Hot Cue point 6 |
| Hot Cue 7 | `POST /api/v1/deck/{deck}/hotcue/7` | Note On → Off | Ch 1/2 | Note 0x06 | Trigger Hot Cue point 7 |
| Hot Cue 8 | `POST /api/v1/deck/{deck}/hotcue/8` | Note On → Off | Ch 1/2 | Note 0x07 | Trigger Hot Cue point 8 |

## Performance Pads — Beat Jump

| Command | API Endpoint | MIDI Message | Channel | Note/CC | Description |
|---|---|---|---|---|---|
| Beat Jump Fwd 2 bars | `POST /api/v1/deck/{deck}/beatjump/fwd/2` | Note On → Off | Ch 1/2 | Note 0x20 | Jump forward 2 bars |
| Beat Jump Fwd 4 bars | `POST /api/v1/deck/{deck}/beatjump/fwd/4` | Note On → Off | Ch 1/2 | Note 0x21 | Jump forward 4 bars |
| Beat Jump Fwd 8 bars | `POST /api/v1/deck/{deck}/beatjump/fwd/8` | Note On → Off | Ch 1/2 | Note 0x22 | Jump forward 8 bars |
| Beat Jump Fwd 16 bars | `POST /api/v1/deck/{deck}/beatjump/fwd/16` | Note On → Off | Ch 1/2 | Note 0x23 | Jump forward 16 bars |
| Beat Jump Bwd 2 bars | `POST /api/v1/deck/{deck}/beatjump/bwd/2` | Note On → Off | Ch 1/2 | Note 0x24 | Jump backward 2 bars |
| Beat Jump Bwd 4 bars | `POST /api/v1/deck/{deck}/beatjump/bwd/4` | Note On → Off | Ch 1/2 | Note 0x25 | Jump backward 4 bars |
| Beat Jump Bwd 8 bars | `POST /api/v1/deck/{deck}/beatjump/bwd/8` | Note On → Off | Ch 1/2 | Note 0x26 | Jump backward 8 bars |
| Beat Jump Bwd 16 bars | `POST /api/v1/deck/{deck}/beatjump/bwd/16` | Note On → Off | Ch 1/2 | Note 0x27 | Jump backward 16 bars |

## Performance Pads — Beat Loop

| Command | API Endpoint | MIDI Message | Channel | Note/CC | Description |
|---|---|---|---|---|---|
| Beat Loop 1/2 bar | `POST /api/v1/deck/{deck}/beatloop/0.5` | Note On → Off | Ch 1/2 | Note 0x10 | Loop 1/2 bar |
| Beat Loop 1 bar | `POST /api/v1/deck/{deck}/beatloop/1` | Note On → Off | Ch 1/2 | Note 0x11 | Loop 1 bar |
| Beat Loop 2 bars | `POST /api/v1/deck/{deck}/beatloop/2` | Note On → Off | Ch 1/2 | Note 0x12 | Loop 2 bars |
| Beat Loop 4 bars | `POST /api/v1/deck/{deck}/beatloop/4` | Note On → Off | Ch 1/2 | Note 0x13 | Loop 4 bars |

## Performance Pads — Sampler

| Command | API Endpoint | MIDI Message | Channel | Note/CC | Description |
|---|---|---|---|---|---|
| Sampler 1 | `POST /api/v1/deck/{deck}/sampler/1` | Note On → Off | Ch 1/2 | Note 0x30 | Trigger Sampler slot 1 |
| Sampler 2 | `POST /api/v1/deck/{deck}/sampler/2` | Note On → Off | Ch 1/2 | Note 0x31 | Trigger Sampler slot 2 |
| Sampler 3 | `POST /api/v1/deck/{deck}/sampler/3` | Note On → Off | Ch 1/2 | Note 0x32 | Trigger Sampler slot 3 |
| Sampler 4 | `POST /api/v1/deck/{deck}/sampler/4` | Note On → Off | Ch 1/2 | Note 0x33 | Trigger Sampler slot 4 |
| Sampler 5 | `POST /api/v1/deck/{deck}/sampler/5` | Note On → Off | Ch 1/2 | Note 0x34 | Trigger Sampler slot 5 |
| Sampler 6 | `POST /api/v1/deck/{deck}/sampler/6` | Note On → Off | Ch 1/2 | Note 0x35 | Trigger Sampler slot 6 |
| Sampler 7 | `POST /api/v1/deck/{deck}/sampler/7` | Note On → Off | Ch 1/2 | Note 0x36 | Trigger Sampler slot 7 |
| Sampler 8 | `POST /api/v1/deck/{deck}/sampler/8` | Note On → Off | Ch 1/2 | Note 0x37 | Trigger Sampler slot 8 |

## FX

| Command | API Endpoint | MIDI Message | Channel | Note/CC | Description |
|---|---|---|---|---|---|
| FX 1 Toggle | `POST /api/v1/fx/1/toggle` | Note On → Off | Ch 5 (0x94) | Note 0x47 | Toggle FX unit 1 on/off |
| FX 2 Toggle | `POST /api/v1/fx/2/toggle` | Note On → Off | Ch 5 (0x94) | Note 0x48 | Toggle FX unit 2 on/off |

## Mixer

| Command | API Endpoint | MIDI Message | Channel | Note/CC | Description |
|---|---|---|---|---|---|
| Crossfader | `POST /api/v1/mixer/crossfader` | CC | Ch 3 (0xB2) | CC 0x1F | Set crossfader position (0 = Deck 1, 127 = Deck 2) |

## Queue Management

| Command | API Endpoint | MIDI Message | Channel | Note/CC | Description |
|---|---|---|---|---|---|
| Add to Queue | `POST /api/v1/queue/add` | — | — | — | Add a track to the playback queue |
| Remove from Queue | `DELETE /api/v1/queue/{track_id}` | — | — | — | Remove a track by ID |
| Reorder Queue | `PUT /api/v1/queue/reorder` | — | — | — | Reorder the entire queue |
| Get Queue | `GET /api/v1/queue` | — | — | — | Return the current queue |
| Start Auto-Queue | `POST /api/v1/autoqueue/start` | — | — | — | Start background auto-queue monitor |
| Stop Auto-Queue | `POST /api/v1/autoqueue/stop` | — | — | — | Stop background auto-queue monitor |
| Controller Status | `GET /api/v1/status` | — | — | — | MIDI connection & queue status |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MIDI_PORT_NAME` | `DDJ-FLX4` | Substring-matched against available MIDI outputs |
| `SUPABASE_URL` | *(empty)* | Supabase project URL |
| `SUPABASE_KEY` | *(empty)* | Supabase anon/service key |
| `AUTOQUEUE_LOOKAHEAD_SECONDS` | `30` | Seconds before track end to trigger auto-queue |
| `CROSSFADE_BEATS` | `8` | Duration of auto-crossfade in beats |
| `PORT` | `8000` | HTTP server listen port |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python Scripts/midi_server.py

# Or with uvicorn directly
uvicorn Scripts.midi_server:app --host 0.0.0.0 --port 8000
```

API docs available at `http://localhost:8000/docs` (Swagger UI).
