/* ============================================================
   RhythmClaw — DJ Mini-Player Application
   ============================================================ */

// --------------- Telegram WebApp Integration ---------------
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

if (tg.themeParams) {
  const root = document.documentElement;
  if (tg.themeParams.bg_color) {
    root.style.setProperty('--bg', tg.themeParams.bg_color);
  }
  if (tg.themeParams.secondary_bg_color) {
    root.style.setProperty('--surface', tg.themeParams.secondary_bg_color);
  }
  if (tg.themeParams.text_color) {
    root.style.setProperty('--text', tg.themeParams.text_color);
  }
  if (tg.themeParams.hint_color) {
    root.style.setProperty('--text-secondary', tg.themeParams.hint_color);
  }
}

// --------------- Configuration ---------------
const MIDI_SERVER_URL =
  (tg.initDataUnsafe && tg.initDataUnsafe.start_param) ||
  localStorage.getItem('rhythmclaw_server') ||
  'http://localhost:8000';

const POLL_INTERVAL_MS = 2000;
const EDGE_SNAP_THRESHOLD = 60;
const MIN_PLAYER_HEIGHT = 200;
const MAX_PLAYER_HEIGHT_VH = 60;
const STORAGE_KEY_POS = 'rhythmclaw_position';
const STORAGE_KEY_SIZE = 'rhythmclaw_size';

// --------------- State ---------------
const state = {
  isPlaying: false,
  currentTrack: { name: '', artist: '', bpm: 0, deck: 1 },
  isLiked: false,
  isCollapsed: false,
  edgeSide: null, // 'left' | 'right' | null
  position: { x: 0, y: 0 },
  crossfaderValue: 64, // 0–127
  playerHeight: null,
};

// --------------- DOM References ---------------
let els = {};

function cacheDom() {
  els = {
    player: document.getElementById('mini-player'),
    trackName: document.getElementById('track-name'),
    trackArtist: document.getElementById('track-artist'),
    bpmBadge: document.getElementById('badge-bpm'),
    deckBadge: document.getElementById('badge-deck'),
    canvas: document.getElementById('waveform-canvas'),
    btnPlay: document.getElementById('btn-play'),
    btnPrev: document.getElementById('btn-prev'),
    btnNext: document.getElementById('btn-next'),
    btnLike: document.getElementById('btn-like'),
    iconPlay: document.getElementById('icon-play'),
    iconPause: document.getElementById('icon-pause'),
    crossfaderFill: document.getElementById('crossfader-fill'),
    crossfaderThumb: document.getElementById('crossfader-thumb'),
    edgeTab: document.getElementById('edge-tab'),
    fxEcho: document.getElementById('fx-echo'),
    fxReverb: document.getElementById('fx-reverb'),
    fxFilter: document.getElementById('fx-filter'),
  };
}

// --------------- API Communication ---------------
async function apiCall(endpoint, method = 'POST', body = null) {
  const url = `${MIDI_SERVER_URL}${endpoint}`;
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) {
    opts.body = JSON.stringify(body);
  }
  try {
    const res = await fetch(url, opts);
    if (!res.ok) {
      console.error(`API ${method} ${endpoint} → ${res.status}`);
      return null;
    }
    const text = await res.text();
    return text ? JSON.parse(text) : null;
  } catch (err) {
    console.error(`API ${method} ${endpoint} error:`, err.message);
    return null;
  }
}

async function togglePlay() {
  state.isPlaying = !state.isPlaying;
  renderPlayState();
  await apiCall(`/api/v1/deck/${state.currentTrack.deck}/play`, 'POST');
}

async function skipTrack() {
  // Load next queued track on the opposing deck
  const nextDeck = state.currentTrack.deck === 1 ? 2 : 1;
  await apiCall(`/api/v1/deck/${nextDeck}/load`, 'POST');
}

async function prevTrack() {
  // Cue the current deck (return to cue point)
  await apiCall(`/api/v1/deck/${state.currentTrack.deck}/cue`, 'POST');
}

async function toggleLike() {
  state.isLiked = !state.isLiked;
  renderLike();
  await apiCall('/api/v1/track/like', 'POST', { liked: state.isLiked });
}

async function setCrossfader(value) {
  state.crossfaderValue = Math.max(0, Math.min(127, value));
  renderCrossfader();
  await apiCall('/api/v1/mixer/crossfader', 'POST', { value: state.crossfaderValue });
}

// --------------- Render Helpers ---------------
function renderTrackInfo() {
  const t = state.currentTrack;
  els.trackName.textContent = t.name || 'No Track Loaded';
  els.trackArtist.textContent = t.artist || '—';
  els.bpmBadge.textContent = t.bpm ? `${t.bpm} BPM` : '— BPM';
  els.deckBadge.textContent = `D${t.deck || 1}`;
}

function renderPlayState() {
  if (state.isPlaying) {
    els.iconPlay.style.display = 'none';
    els.iconPause.style.display = 'block';
    els.btnPlay.setAttribute('aria-label', 'Pause');
  } else {
    els.iconPlay.style.display = 'block';
    els.iconPause.style.display = 'none';
    els.btnPlay.setAttribute('aria-label', 'Play');
  }
}

function renderLike() {
  els.btnLike.classList.toggle('active', state.isLiked);
}

function renderCrossfader() {
  const pct = (state.crossfaderValue / 127) * 100;
  els.crossfaderFill.style.width = `${pct}%`;
  els.crossfaderThumb.style.left = `${pct}%`;
}

// --------------- Waveform Visualization ---------------
let waveformBars = [];
let waveformTargets = [];
const WAVEFORM_BAR_COUNT = 64;
let waveformRafId = null;

function initWaveformBars() {
  waveformBars = Array.from({ length: WAVEFORM_BAR_COUNT }, () => Math.random() * 0.3 + 0.1);
  waveformTargets = waveformBars.slice();
}

function drawWaveform() {
  const canvas = els.canvas;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
  }

  const w = rect.width;
  const h = rect.height;
  ctx.clearRect(0, 0, w, h);

  const barW = Math.max(2, (w / WAVEFORM_BAR_COUNT) - 1);
  const gap = (w - barW * WAVEFORM_BAR_COUNT) / (WAVEFORM_BAR_COUNT - 1);

  if (state.isPlaying) {
    for (let i = 0; i < WAVEFORM_BAR_COUNT; i++) {
      waveformTargets[i] = Math.random() * 0.85 + 0.15;
    }
  }

  for (let i = 0; i < WAVEFORM_BAR_COUNT; i++) {
    waveformBars[i] += (waveformTargets[i] - waveformBars[i]) * 0.18;
    const barH = waveformBars[i] * h;
    const x = i * (barW + gap);
    const y = (h - barH) / 2;

    ctx.fillStyle = state.isPlaying ? '#a855f7' : '#444';
    ctx.beginPath();
    ctx.roundRect(x, y, barW, barH, 1);
    ctx.fill();
  }

  waveformRafId = requestAnimationFrame(drawWaveform);
}

function stopWaveformAnimation() {
  if (waveformRafId) {
    cancelAnimationFrame(waveformRafId);
    waveformRafId = null;
  }
}

// --------------- Drag & Edge Snap ---------------
let dragState = null;

function handleTouchStart(e) {
  if (state.isCollapsed || e.touches.length !== 1) return;
  const touch = e.touches[0];
  dragState = {
    startX: touch.clientX,
    startY: touch.clientY,
    offsetX: state.position.x,
    offsetY: state.position.y,
    moved: false,
  };
}

function handleTouchMove(e) {
  if (!dragState || e.touches.length !== 1) return;
  const touch = e.touches[0];
  const dx = touch.clientX - dragState.startX;
  const dy = touch.clientY - dragState.startY;

  if (Math.abs(dx) > 8 || Math.abs(dy) > 8) {
    dragState.moved = true;
  }

  if (dragState.moved) {
    state.position.x = dragState.offsetX + dx;
    state.position.y = dragState.offsetY + dy;
    els.player.style.transform = `translate(${state.position.x}px, ${state.position.y}px)`;
  }
}

function handleTouchEnd(e) {
  if (!dragState) return;
  if (!dragState.moved) {
    dragState = null;
    return;
  }

  const screenW = window.innerWidth;
  const playerRect = els.player.getBoundingClientRect();

  if (playerRect.left < EDGE_SNAP_THRESHOLD) {
    collapseToEdge('left');
  } else if (screenW - playerRect.right < EDGE_SNAP_THRESHOLD) {
    collapseToEdge('right');
  } else {
    savePosition();
  }

  dragState = null;
}

function collapseToEdge(side) {
  state.isCollapsed = true;
  state.edgeSide = side;

  const slideDir = side === 'left' ? '-100%' : '100%';
  els.player.style.setProperty('--slide-to', slideDir);
  els.player.classList.add('collapse-exit');

  els.player.addEventListener('animationend', function onEnd() {
    els.player.removeEventListener('animationend', onEnd);
    els.player.classList.remove('collapse-exit');
    els.player.style.display = 'none';

    els.edgeTab.className = `edge-tab edge-tab--${side} visible`;
  }, { once: true });

  localStorage.setItem(STORAGE_KEY_POS, JSON.stringify({ collapsed: true, side }));
}

function expandFromEdge() {
  if (!state.isCollapsed) return;

  const side = state.edgeSide;
  const slideDir = side === 'left' ? '-100%' : '100%';

  els.edgeTab.classList.remove('visible');
  els.player.style.display = '';
  els.player.style.transform = '';
  els.player.style.setProperty('--slide-from', slideDir);
  els.player.classList.add('expand-enter');

  els.player.addEventListener('animationend', function onEnd() {
    els.player.removeEventListener('animationend', onEnd);
    els.player.classList.remove('expand-enter');
  }, { once: true });

  state.isCollapsed = false;
  state.edgeSide = null;
  state.position = { x: 0, y: 0 };

  localStorage.setItem(STORAGE_KEY_POS, JSON.stringify({ collapsed: false }));
}

function savePosition() {
  localStorage.setItem(STORAGE_KEY_POS, JSON.stringify({
    collapsed: false,
    x: state.position.x,
    y: state.position.y,
  }));
}

// --------------- Pinch-to-Resize ---------------
let pinchState = null;

function handlePinchStart(e) {
  if (e.touches.length !== 2) return;
  const d = Math.hypot(
    e.touches[1].clientX - e.touches[0].clientX,
    e.touches[1].clientY - e.touches[0].clientY,
  );
  pinchState = { initialDist: d, initialHeight: els.player.offsetHeight };
}

function handlePinchMove(e) {
  if (!pinchState || e.touches.length !== 2) return;
  e.preventDefault();

  const d = Math.hypot(
    e.touches[1].clientX - e.touches[0].clientX,
    e.touches[1].clientY - e.touches[0].clientY,
  );
  const scale = d / pinchState.initialDist;
  const maxH = window.innerHeight * (MAX_PLAYER_HEIGHT_VH / 100);
  const newH = Math.round(Math.min(maxH, Math.max(MIN_PLAYER_HEIGHT, pinchState.initialHeight * scale)));

  els.player.style.height = `${newH}px`;
  els.player.style.minHeight = `${newH}px`;
  state.playerHeight = newH;
}

function handlePinchEnd() {
  if (!pinchState) return;
  pinchState = null;
  if (state.playerHeight) {
    localStorage.setItem(STORAGE_KEY_SIZE, JSON.stringify({ height: state.playerHeight }));
  }
}

// --------------- Polling for Server Updates ---------------
let pollTimer = null;

function startPolling() {
  pollTimer = setInterval(fetchStatus, POLL_INTERVAL_MS);
  fetchStatus();
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function fetchStatus() {
  const data = await apiCall('/api/v1/status', 'GET');
  if (!data) return;

  if (data.track) {
    state.currentTrack.name = data.track.name || '';
    state.currentTrack.artist = data.track.artist || '';
    state.currentTrack.bpm = data.track.bpm || 0;
    state.currentTrack.deck = data.track.deck || 1;
    renderTrackInfo();
  }

  if (typeof data.is_playing === 'boolean' && data.is_playing !== state.isPlaying) {
    state.isPlaying = data.is_playing;
    renderPlayState();
  }

  if (typeof data.crossfader === 'number') {
    state.crossfaderValue = data.crossfader;
    renderCrossfader();
  }

  if (data.fx) {
    els.fxEcho.classList.toggle('active', !!data.fx.fx1);
    els.fxReverb.classList.toggle('active', !!data.fx.fx2);
  }
}

// --------------- Restore Persisted State ---------------
function restorePosition() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_POS);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (saved.collapsed && saved.side) {
      collapseToEdge(saved.side);
    } else if (typeof saved.x === 'number' && typeof saved.y === 'number') {
      state.position.x = saved.x;
      state.position.y = saved.y;
      els.player.style.transform = `translate(${saved.x}px, ${saved.y}px)`;
    }
  } catch { /* ignore corrupt data */ }
}

function restoreSize() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_SIZE);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (saved.height) {
      state.playerHeight = saved.height;
      els.player.style.height = `${saved.height}px`;
      els.player.style.minHeight = `${saved.height}px`;
    }
  } catch { /* ignore corrupt data */ }
}

// --------------- Event Binding ---------------
function attachListeners() {
  // Transport buttons
  els.btnPlay.addEventListener('click', togglePlay);
  els.btnPrev.addEventListener('click', prevTrack);
  els.btnNext.addEventListener('click', skipTrack);
  els.btnLike.addEventListener('click', toggleLike);

  // Edge tab expand
  els.edgeTab.addEventListener('click', expandFromEdge);

  // Drag (single touch)
  els.player.addEventListener('touchstart', handleTouchStart, { passive: true });
  els.player.addEventListener('touchmove', handleTouchMove, { passive: true });
  els.player.addEventListener('touchend', handleTouchEnd, { passive: true });

  // Pinch (two-finger)
  els.player.addEventListener('touchstart', handlePinchStart, { passive: true });
  els.player.addEventListener('touchmove', handlePinchMove, { passive: false });
  els.player.addEventListener('touchend', handlePinchEnd, { passive: true });

  // Telegram viewport changes
  tg.onEvent('viewportChanged', (event) => {
    if (event.isStateStable && !state.isCollapsed) {
      els.player.style.height = '';
      els.player.style.minHeight = '';
    }
  });
}

// --------------- Initialization ---------------
function init() {
  cacheDom();
  attachListeners();
  restorePosition();
  restoreSize();
  renderTrackInfo();
  renderPlayState();
  renderLike();
  renderCrossfader();
  initWaveformBars();
  drawWaveform();
  startPolling();
}

document.addEventListener('DOMContentLoaded', init);
