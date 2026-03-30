"""
RhythmClaw MIDI Server — FastAPI application for Pioneer DDJ-FLX4 control.

Provides HTTP endpoints that translate REST calls into MIDI messages
for the Pioneer DDJ-FLX4 DJ controller. Supports transport controls,
performance pads, FX, mixer, and an auto-queue system backed by Supabase.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from enum import IntEnum
from typing import Any, Optional

import mido
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import Client as SupabaseClient
from supabase import create_client

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rhythmclaw.midi")

# ---------------------------------------------------------------------------
# Environment / configuration
# ---------------------------------------------------------------------------

MIDI_PORT_NAME: str = os.getenv("MIDI_PORT_NAME", "DDJ-FLX4")
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
AUTOQUEUE_LOOKAHEAD_SECONDS: int = int(os.getenv("AUTOQUEUE_LOOKAHEAD_SECONDS", "30"))
CROSSFADE_BEATS: int = int(os.getenv("CROSSFADE_BEATS", "8"))

# ---------------------------------------------------------------------------
# MIDI constants — Pioneer DDJ-FLX4 message list
# ---------------------------------------------------------------------------


class MidiStatus(IntEnum):
    """MIDI status-byte helpers (upper nibble)."""

    NOTE_ON_CH1 = 0x90
    NOTE_OFF_CH1 = 0x80
    CC_CH1 = 0xB0
    NOTE_ON_CH2 = 0x91
    NOTE_OFF_CH2 = 0x81
    CC_CH2 = 0xB1
    CC_CH3 = 0xB2
    NOTE_ON_CH5 = 0x94
    NOTE_OFF_CH5 = 0x84
    CC_CH5 = 0xB4
    NOTE_ON_CH6 = 0x95
    NOTE_OFF_CH6 = 0x85
    CC_CH6 = 0xB5


# Note numbers
NOTE_PLAY_PAUSE = 0x0B
NOTE_CUE = 0x0C
NOTE_SYNC = 0x58
NOTE_LOAD = 0x46
NOTE_FX1 = 0x47
NOTE_FX2 = 0x48

# Hot Cue pads 1-8  (Performance Pad mode)
HOTCUE_NOTES: list[int] = [0x00 + i for i in range(8)]

# Beat Jump pads (fwd 2/4/8/16 then bwd 2/4/8/16)
BEATJUMP_NOTES: list[int] = [0x20 + i for i in range(8)]
BEATJUMP_FWD_MAP: dict[int, int] = {2: 0x20, 4: 0x21, 8: 0x22, 16: 0x23}
BEATJUMP_BWD_MAP: dict[int, int] = {2: 0x24, 4: 0x25, 8: 0x26, 16: 0x27}

# Beat Loop pads (1/2, 1, 2, 4 bars)
BEATLOOP_NOTES: list[int] = [0x10 + i for i in range(8)]
BEATLOOP_MAP: dict[float, int] = {0.5: 0x10, 1: 0x11, 2: 0x12, 4: 0x13}

# Sampler pads 1-8
SAMPLER_NOTES: list[int] = [0x30 + i for i in range(8)]

# CC numbers
CC_TEMPO = 0x00
CC_CROSSFADER = 0x1F
CC_JOG_NUDGE = 0x22

VELOCITY_ON = 0x7F
VELOCITY_OFF = 0x00

# Default BPM assumption for crossfade timing (until BPM-aware integration)
DEFAULT_BPM: int = int(os.getenv("DEFAULT_BPM", "120"))


def _deck_note_on(deck: int) -> int:
    """Return NOTE ON status byte for the given deck (1 or 2)."""
    return MidiStatus.NOTE_ON_CH1 if deck == 1 else MidiStatus.NOTE_ON_CH2


def _deck_note_off(deck: int) -> int:
    """Return NOTE OFF status byte for the given deck (1 or 2)."""
    return MidiStatus.NOTE_OFF_CH1 if deck == 1 else MidiStatus.NOTE_OFF_CH2


def _deck_cc(deck: int) -> int:
    """Return CC status byte for the given deck (1 or 2)."""
    return MidiStatus.CC_CH1 if deck == 1 else MidiStatus.CC_CH2


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ValueBody(BaseModel):
    """Body for endpoints that accept a single 0-127 MIDI value."""

    value: int = Field(..., ge=0, le=127, description="MIDI value (0-127)")


class QueueAddBody(BaseModel):
    """Body for adding a track to the queue."""

    track_id: str = Field(..., description="Unique track identifier")
    track_name: str = Field(..., description="Human-readable track name")
    deck: Optional[int] = Field(None, ge=1, le=2, description="Target deck (1 or 2)")


class QueueReorderBody(BaseModel):
    """Body for reordering the queue."""

    track_ids: list[str] = Field(..., description="Ordered list of track IDs")


class MidiMessageResponse(BaseModel):
    """Standard response after sending a MIDI message."""

    ok: bool
    message: str
    midi: dict[str, Any] = Field(default_factory=dict)


class QueueItem(BaseModel):
    """A single item in the playback queue."""

    track_id: str
    track_name: str
    deck: Optional[int] = None
    added_at: float = Field(default_factory=time.time)


class QueueResponse(BaseModel):
    """Response containing the current queue."""

    queue: list[QueueItem]


class NowPlayingResponse(BaseModel):
    """Current now-playing information."""

    track_id: str
    track_name: str
    deck: int
    bpm: int
    is_playing: bool


class HistoryResponse(BaseModel):
    """Playback history."""

    tracks: list[str]


class StatusResponse(BaseModel):
    """Current controller status."""

    midi_connected: bool
    midi_port: str
    autoqueue_running: bool
    queue_length: int
    decks: dict[str, Any]
    # Additional fields for Mini App polling
    track: Optional[dict[str, Any]] = None
    is_playing: bool = False
    crossfader: int = 64
    fx: Optional[dict[str, bool]] = None


# ---------------------------------------------------------------------------
# MIDI controller wrapper
# ---------------------------------------------------------------------------


class MidiController:
    """Thin wrapper around ``mido.open_output`` for the DDJ-FLX4."""

    def __init__(self) -> None:
        self.port: Optional[mido.ports.BaseOutput] = None
        self.port_name: str = MIDI_PORT_NAME
        self.connected: bool = False

    # -- lifecycle -----------------------------------------------------------

    def connect(self) -> None:
        """Try to open the configured MIDI output port."""
        available = mido.get_output_names()
        logger.info("Available MIDI outputs: %s", available)

        matched = [p for p in available if self.port_name in p]
        if matched:
            self.port = mido.open_output(matched[0])
            self.connected = True
            logger.info("Connected to MIDI port: %s", matched[0])
        else:
            logger.warning(
                "MIDI port '%s' not found — running in dry-run mode",
                self.port_name,
            )
            self.connected = False

    def disconnect(self) -> None:
        """Close the MIDI port if open."""
        if self.port and not self.port.closed:
            self.port.close()
            logger.info("MIDI port closed.")
        self.connected = False

    # -- low-level send ------------------------------------------------------

    def send(self, data: list[int]) -> dict[str, Any]:
        """Send raw MIDI bytes and return a log dict."""
        msg = mido.Message.from_bytes(data)
        hex_str = " ".join(f"0x{b:02X}" for b in data)
        if self.port and self.connected:
            self.port.send(msg)
            logger.info("MIDI TX: %s", hex_str)
        else:
            logger.info("MIDI TX (dry-run): %s", hex_str)
        return {"bytes": hex_str, "connected": self.connected}

    # -- note helpers --------------------------------------------------------

    def note_on(self, channel_status: int, note: int) -> dict[str, Any]:
        """Send a Note On message with full velocity."""
        return self.send([channel_status, note, VELOCITY_ON])

    def note_off(self, channel_status: int, note: int) -> dict[str, Any]:
        """Send a Note Off (velocity 0) message."""
        return self.send([channel_status, note, VELOCITY_OFF])

    def note_trigger(self, channel_on: int, note: int) -> dict[str, Any]:
        """Send Note On followed by Note Off (button press)."""
        result = self.note_on(channel_on, note)
        channel_off = (channel_on & 0x0F) | 0x80
        self.note_off(channel_off, note)
        return result

    # -- CC helper -----------------------------------------------------------

    def cc(self, channel_status: int, control: int, value: int) -> dict[str, Any]:
        """Send a Control Change message."""
        return self.send([channel_status, control, value & 0x7F])


# ---------------------------------------------------------------------------
# Auto-queue manager
# ---------------------------------------------------------------------------


class AutoQueueManager:
    """Background task that monitors decks and auto-loads the next track."""

    def __init__(
        self,
        midi: MidiController,
        supabase: Optional[SupabaseClient],
    ) -> None:
        self.midi = midi
        self.supabase = supabase
        self.running: bool = False
        self._task: Optional[asyncio.Task[None]] = None
        self.queue: list[QueueItem] = []
        self.decks: dict[int, dict[str, Any]] = {
            1: {"playing": False, "remaining_seconds": None, "track_id": None, "track_name": "", "bpm": DEFAULT_BPM},
            2: {"playing": False, "remaining_seconds": None, "track_id": None, "track_name": "", "bpm": DEFAULT_BPM},
        }
        self.active_deck: int = 1
        self.crossfader_value: int = 64
        self.fx_state: dict[str, bool] = {"fx1": False, "fx2": False}
        self.history: list[str] = []  # last played track names (max 20)

    # -- queue manipulation --------------------------------------------------

    def add_track(self, item: QueueItem) -> None:
        self.queue.append(item)
        logger.info("Queue +1: %s (total %d)", item.track_name, len(self.queue))

    def remove_track(self, track_id: str) -> bool:
        before = len(self.queue)
        self.queue = [q for q in self.queue if q.track_id != track_id]
        removed = len(self.queue) < before
        if removed:
            logger.info("Queue -1: %s (total %d)", track_id, len(self.queue))
        return removed

    def reorder(self, track_ids: list[str]) -> None:
        index = {item.track_id: item for item in self.queue}
        self.queue = [index[tid] for tid in track_ids if tid in index]
        logger.info("Queue reordered (%d items)", len(self.queue))

    # -- auto-queue lifecycle ------------------------------------------------

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Auto-queue started.")

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Auto-queue stopped.")

    # -- internal loop -------------------------------------------------------

    async def _loop(self) -> None:
        """Poll deck state and trigger crossfade when a track nears its end."""
        while self.running:
            try:
                await self._check_decks()
            except Exception:
                logger.exception("Auto-queue loop error")
            await asyncio.sleep(1)

    async def _check_decks(self) -> None:
        for deck_num in (1, 2):
            state = self.decks[deck_num]
            remaining = state.get("remaining_seconds")
            if (
                state.get("playing")
                and remaining is not None
                and remaining <= AUTOQUEUE_LOOKAHEAD_SECONDS
            ):
                opposing = 2 if deck_num == 1 else 1
                await self._load_next(opposing)
                await self._crossfade(deck_num, opposing)

    async def _load_next(self, target_deck: int) -> None:
        """Load the next queued track onto *target_deck*."""
        if self.queue:
            track = self.queue.pop(0)
            logger.info(
                "Auto-loading '%s' onto deck %d", track.track_name, target_deck
            )
            self.midi.note_trigger(_deck_note_on(target_deck), NOTE_LOAD)
            return

        # Fallback: pull from Supabase auto-playlist
        if self.supabase:
            try:
                resp = (
                    self.supabase.table("auto_playlist")
                    .select("*")
                    .limit(1)
                    .execute()
                )
                if resp.data:
                    row = resp.data[0]
                    logger.info(
                        "Auto-playlist fallback: '%s' onto deck %d",
                        row.get("track_name", "unknown"),
                        target_deck,
                    )
                    self.midi.note_trigger(_deck_note_on(target_deck), NOTE_LOAD)
            except Exception:
                logger.exception("Supabase auto-playlist fetch failed")

    async def _crossfade(self, from_deck: int, to_deck: int) -> None:
        """Smoothly slide the crossfader from *from_deck* to *to_deck*."""
        start_val = 0 if from_deck == 1 else 127
        end_val = 127 if from_deck == 1 else 0
        steps = 32
        # Use configurable DEFAULT_BPM for crossfade timing.
        # TODO: Integrate with deck BPM metadata for BPM-aware crossfades.
        seconds_per_beat = 60.0 / DEFAULT_BPM
        step_delay = (CROSSFADE_BEATS * seconds_per_beat) / steps

        # Start playing the target deck
        self.midi.note_trigger(_deck_note_on(to_deck), NOTE_PLAY_PAUSE)

        for i in range(steps + 1):
            ratio = i / steps
            val = int(start_val + (end_val - start_val) * ratio)
            self.midi.cc(MidiStatus.CC_CH3, CC_CROSSFADER, val)
            await asyncio.sleep(step_delay)

        logger.info("Crossfade complete: deck %d → deck %d", from_deck, to_deck)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

midi_controller = MidiController()
supabase_client: Optional[SupabaseClient] = None
autoqueue: Optional[AutoQueueManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the MIDI server."""
    global supabase_client, autoqueue

    # -- startup --
    midi_controller.connect()

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialised.")
        except Exception:
            logger.exception("Failed to initialise Supabase client")

    autoqueue = AutoQueueManager(midi_controller, supabase_client)
    logger.info("RhythmClaw MIDI server ready.")

    yield

    # -- shutdown --
    if autoqueue and autoqueue.running:
        await autoqueue.stop()
    midi_controller.disconnect()
    logger.info("RhythmClaw MIDI server shut down.")


app = FastAPI(
    title="RhythmClaw MIDI Server",
    description="HTTP → MIDI bridge for the Pioneer DDJ-FLX4",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_deck(deck: int) -> None:
    if deck not in (1, 2):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Deck must be 1 or 2.",
        )


def _ok(message: str, midi_info: dict[str, Any] | None = None) -> MidiMessageResponse:
    return MidiMessageResponse(ok=True, message=message, midi=midi_info or {})


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Transport endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/deck/{deck}/play",
    response_model=MidiMessageResponse,
    tags=["Transport"],
)
async def deck_play(deck: int) -> MidiMessageResponse:
    """Toggle Play / Pause on the specified deck."""
    _validate_deck(deck)
    midi_info = midi_controller.note_trigger(_deck_note_on(deck), NOTE_PLAY_PAUSE)
    return _ok(f"Deck {deck} play/pause toggled", midi_info)


@app.post(
    "/api/v1/deck/{deck}/cue",
    response_model=MidiMessageResponse,
    tags=["Transport"],
)
async def deck_cue(deck: int) -> MidiMessageResponse:
    """Press the Cue button on the specified deck."""
    _validate_deck(deck)
    midi_info = midi_controller.note_trigger(_deck_note_on(deck), NOTE_CUE)
    return _ok(f"Deck {deck} cue triggered", midi_info)


@app.post(
    "/api/v1/deck/{deck}/sync",
    response_model=MidiMessageResponse,
    tags=["Transport"],
)
async def deck_sync(deck: int) -> MidiMessageResponse:
    """Activate Beat Sync on the specified deck."""
    _validate_deck(deck)
    midi_info = midi_controller.note_trigger(_deck_note_on(deck), NOTE_SYNC)
    return _ok(f"Deck {deck} beat-sync toggled", midi_info)


@app.post(
    "/api/v1/deck/{deck}/load",
    response_model=MidiMessageResponse,
    tags=["Transport"],
)
async def deck_load(deck: int) -> MidiMessageResponse:
    """Load the selected track onto the specified deck."""
    _validate_deck(deck)
    midi_info = midi_controller.note_trigger(_deck_note_on(deck), NOTE_LOAD)
    return _ok(f"Track loaded to deck {deck}", midi_info)


@app.post(
    "/api/v1/deck/{deck}/tempo",
    response_model=MidiMessageResponse,
    tags=["Transport"],
)
async def deck_tempo(deck: int, body: ValueBody) -> MidiMessageResponse:
    """Set the tempo slider position for the specified deck (0-127)."""
    _validate_deck(deck)
    midi_info = midi_controller.cc(_deck_cc(deck), CC_TEMPO, body.value)
    return _ok(f"Deck {deck} tempo set to {body.value}", midi_info)


@app.post(
    "/api/v1/deck/{deck}/jog",
    response_model=MidiMessageResponse,
    tags=["Transport"],
)
async def deck_jog(deck: int, body: ValueBody) -> MidiMessageResponse:
    """Send a jog-dial nudge to the specified deck (0-127)."""
    _validate_deck(deck)
    midi_info = midi_controller.cc(_deck_cc(deck), CC_JOG_NUDGE, body.value)
    return _ok(f"Deck {deck} jog nudge {body.value}", midi_info)


# ---------------------------------------------------------------------------
# Performance Pad endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/deck/{deck}/hotcue/{pad}",
    response_model=MidiMessageResponse,
    tags=["Performance Pads"],
)
async def deck_hotcue(deck: int, pad: int) -> MidiMessageResponse:
    """Trigger Hot Cue pad (1-8) on the specified deck."""
    _validate_deck(deck)
    if pad < 1 or pad > 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hot-cue pad must be 1-8.",
        )
    note = HOTCUE_NOTES[pad - 1]
    midi_info = midi_controller.note_trigger(_deck_note_on(deck), note)
    return _ok(f"Deck {deck} hot-cue {pad} triggered", midi_info)


@app.post(
    "/api/v1/deck/{deck}/beatjump/{direction}/{bars}",
    response_model=MidiMessageResponse,
    tags=["Performance Pads"],
)
async def deck_beatjump(deck: int, direction: str, bars: int) -> MidiMessageResponse:
    """Trigger a Beat Jump on the specified deck.

    *direction*: ``fwd`` or ``bwd``
    *bars*: ``2``, ``4``, ``8``, or ``16``
    """
    _validate_deck(deck)
    direction = direction.lower()
    if direction not in ("fwd", "bwd"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Direction must be 'fwd' or 'bwd'.",
        )
    lookup = BEATJUMP_FWD_MAP if direction == "fwd" else BEATJUMP_BWD_MAP
    note = lookup.get(bars)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bars must be 2, 4, 8, or 16.",
        )
    midi_info = midi_controller.note_trigger(_deck_note_on(deck), note)
    return _ok(f"Deck {deck} beat-jump {direction} {bars} bars", midi_info)


@app.post(
    "/api/v1/deck/{deck}/beatloop/{bars}",
    response_model=MidiMessageResponse,
    tags=["Performance Pads"],
)
async def deck_beatloop(deck: int, bars: float) -> MidiMessageResponse:
    """Activate a Beat Loop on the specified deck.

    *bars*: ``0.5``, ``1``, ``2``, or ``4``
    """
    _validate_deck(deck)
    note = BEATLOOP_MAP.get(bars)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bars must be 0.5, 1, 2, or 4.",
        )
    midi_info = midi_controller.note_trigger(_deck_note_on(deck), note)
    return _ok(f"Deck {deck} beat-loop {bars} bars", midi_info)


@app.post(
    "/api/v1/deck/{deck}/sampler/{pad}",
    response_model=MidiMessageResponse,
    tags=["Performance Pads"],
)
async def deck_sampler(deck: int, pad: int) -> MidiMessageResponse:
    """Trigger Sampler pad (1-8) on the specified deck."""
    _validate_deck(deck)
    if pad < 1 or pad > 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sampler pad must be 1-8.",
        )
    note = SAMPLER_NOTES[pad - 1]
    midi_info = midi_controller.note_trigger(_deck_note_on(deck), note)
    return _ok(f"Deck {deck} sampler {pad} triggered", midi_info)


# ---------------------------------------------------------------------------
# FX endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/fx/{unit}/toggle",
    response_model=MidiMessageResponse,
    tags=["FX"],
)
async def fx_toggle(unit: int) -> MidiMessageResponse:
    """Toggle FX unit on/off (unit 1 or 2)."""
    if unit not in (1, 2):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="FX unit must be 1 or 2.",
        )
    note = NOTE_FX1 if unit == 1 else NOTE_FX2
    midi_info = midi_controller.note_trigger(MidiStatus.NOTE_ON_CH5, note)
    return _ok(f"FX {unit} toggled", midi_info)


# ---------------------------------------------------------------------------
# Mixer endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/mixer/crossfader",
    response_model=MidiMessageResponse,
    tags=["Mixer"],
)
async def mixer_crossfader(body: ValueBody) -> MidiMessageResponse:
    """Set the crossfader position (0 = full left / Deck 1, 127 = full right / Deck 2)."""
    midi_info = midi_controller.cc(MidiStatus.CC_CH3, CC_CROSSFADER, body.value)
    return _ok(f"Crossfader set to {body.value}", midi_info)


# ---------------------------------------------------------------------------
# Auto-queue endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/autoqueue/start",
    response_model=MidiMessageResponse,
    tags=["Auto-Queue"],
)
async def autoqueue_start() -> MidiMessageResponse:
    """Start the auto-queue background monitor."""
    if autoqueue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-queue manager not initialised.",
        )
    await autoqueue.start()
    return _ok("Auto-queue started")


@app.post(
    "/api/v1/autoqueue/stop",
    response_model=MidiMessageResponse,
    tags=["Auto-Queue"],
)
async def autoqueue_stop() -> MidiMessageResponse:
    """Stop the auto-queue background monitor."""
    if autoqueue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-queue manager not initialised.",
        )
    await autoqueue.stop()
    return _ok("Auto-queue stopped")


# ---------------------------------------------------------------------------
# Queue management endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/queue/add",
    response_model=MidiMessageResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Queue"],
)
async def queue_add(body: QueueAddBody) -> MidiMessageResponse:
    """Add a track to the playback queue."""
    if autoqueue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-queue manager not initialised.",
        )
    item = QueueItem(
        track_id=body.track_id,
        track_name=body.track_name,
        deck=body.deck,
    )
    autoqueue.add_track(item)
    return _ok(f"'{body.track_name}' added to queue")


@app.delete(
    "/api/v1/queue/{track_id}",
    response_model=MidiMessageResponse,
    tags=["Queue"],
)
async def queue_remove(track_id: str) -> MidiMessageResponse:
    """Remove a track from the queue by its ID."""
    if autoqueue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-queue manager not initialised.",
        )
    removed = autoqueue.remove_track(track_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track '{track_id}' not found in queue.",
        )
    return _ok(f"Track '{track_id}' removed from queue")


@app.put(
    "/api/v1/queue/reorder",
    response_model=MidiMessageResponse,
    tags=["Queue"],
)
async def queue_reorder(body: QueueReorderBody) -> MidiMessageResponse:
    """Reorder the playback queue."""
    if autoqueue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-queue manager not initialised.",
        )
    autoqueue.reorder(body.track_ids)
    return _ok("Queue reordered")


@app.get(
    "/api/v1/queue",
    response_model=QueueResponse,
    tags=["Queue"],
)
async def queue_list() -> QueueResponse:
    """Return the current playback queue."""
    if autoqueue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-queue manager not initialised.",
        )
    return QueueResponse(queue=autoqueue.queue)


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/status",
    response_model=StatusResponse,
    tags=["Status"],
)
async def controller_status() -> StatusResponse:
    """Return the current status of the MIDI controller and queue."""
    active_deck_info = None
    is_playing = False
    crossfader = 64
    fx = None

    if autoqueue:
        ad = autoqueue.active_deck
        deck_info = autoqueue.decks.get(ad, {})
        active_deck_info = {
            "name": deck_info.get("track_name", ""),
            "artist": "",
            "bpm": deck_info.get("bpm", DEFAULT_BPM),
            "deck": ad,
        }
        is_playing = deck_info.get("playing", False)
        crossfader = autoqueue.crossfader_value
        fx = autoqueue.fx_state

    return StatusResponse(
        midi_connected=midi_controller.connected,
        midi_port=midi_controller.port_name,
        autoqueue_running=autoqueue.running if autoqueue else False,
        queue_length=len(autoqueue.queue) if autoqueue else 0,
        decks={str(k): v for k, v in autoqueue.decks.items()} if autoqueue else {},
        track=active_deck_info,
        is_playing=is_playing,
        crossfader=crossfader,
        fx=fx,
    )


@app.get(
    "/api/v1/now_playing",
    response_model=NowPlayingResponse,
    tags=["Status"],
)
async def now_playing() -> NowPlayingResponse:
    """Return information about the currently playing track."""
    if autoqueue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-queue manager not initialised.",
        )
    ad = autoqueue.active_deck
    deck_info = autoqueue.decks.get(ad, {})
    return NowPlayingResponse(
        track_id=deck_info.get("track_id") or "unknown",
        track_name=deck_info.get("track_name") or "No Track",
        deck=ad,
        bpm=deck_info.get("bpm", DEFAULT_BPM),
        is_playing=deck_info.get("playing", False),
    )


@app.get(
    "/api/v1/history",
    response_model=HistoryResponse,
    tags=["Status"],
)
async def playback_history() -> HistoryResponse:
    """Return the last played tracks."""
    tracks = autoqueue.history[-5:] if autoqueue else []
    return HistoryResponse(tracks=tracks)


# ---------------------------------------------------------------------------
# Entrypoint (for direct execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "midi_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
