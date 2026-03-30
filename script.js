/* ============================================================
   RhythmClaw — DJ Controller + Site Script
   NO localStorage/sessionStorage (iframe restriction)
   ============================================================ */

// ─── TELEGRAM WEBAPP DETECTION ──────────────────────────────
(function() {
  'use strict';
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg && tg.initData) {
    document.body.classList.add('tg-mode');
    tg.expand();
    tg.ready();
  }
})();

// ─── HEADER SCROLL ──────────────────────────────────────────
(function() {
  'use strict';
  const header = document.querySelector('[data-header]');
  if (!header) return;
  let lastScrollY = window.scrollY;
  let ticking = false;

  function updateHeader() {
    const y = window.scrollY;
    if (y < 80) {
      header.classList.remove('header--hidden', 'header--scrolled');
    } else if (y - lastScrollY > 10) {
      header.classList.add('header--hidden', 'header--scrolled');
    } else if (lastScrollY - y > 10) {
      header.classList.remove('header--hidden');
      header.classList.add('header--scrolled');
    }
    lastScrollY = y;
    ticking = false;
  }

  window.addEventListener('scroll', () => {
    if (!ticking) { requestAnimationFrame(updateHeader); ticking = true; }
  }, { passive: true });
})();

// ─── MOBILE MENU ────────────────────────────────────────────
(function() {
  'use strict';
  const toggleBtn = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-mobile-nav]');
  const header = document.querySelector('[data-header]');
  if (!toggleBtn || !nav) return;
  let isOpen = false;

  function openMenu() {
    isOpen = true;
    nav.classList.add('nav--open');
    toggleBtn.setAttribute('aria-expanded', 'true');
    document.body.classList.add('menu-open');
    if (header) header.classList.remove('header--hidden');
    toggleBtn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  }
  function closeMenu() {
    isOpen = false;
    nav.classList.remove('nav--open');
    toggleBtn.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('menu-open');
    toggleBtn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>';
  }

  toggleBtn.addEventListener('click', () => isOpen ? closeMenu() : openMenu());
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen) closeMenu(); });
  nav.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('click', e => {
    if (isOpen && !nav.contains(e.target) && !toggleBtn.contains(e.target)) closeMenu();
  });
})();

// ─── SMOOTH SCROLL ──────────────────────────────────────────
(function() {
  'use strict';
  document.addEventListener('click', e => {
    const anchor = e.target.closest('a[href^="#"]');
    if (!anchor) return;
    const id = anchor.getAttribute('href').slice(1);
    if (!id) return;
    const el = document.getElementById(id);
    if (!el) return;
    e.preventDefault();
    const header = document.querySelector('[data-header]');
    const offset = header ? header.offsetHeight + 16 : 80;
    const top = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    history.pushState(null, '', '#' + id);
  });
})();

// ─── SCROLL REVEAL ──────────────────────────────────────────
(function() {
  'use strict';
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('[data-reveal]').forEach(el => {
        el.style.opacity = '1'; el.style.transform = 'none';
      });
    });
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        setTimeout(() => el.classList.add('revealed'), parseInt(el.dataset.revealDelay || '0', 10));
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -60px 0px' });

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-reveal]').forEach(el => {
      const dir = el.dataset.reveal || 'up';
      el.style.transition = 'opacity 0.7s cubic-bezier(0.16,1,0.3,1), transform 0.7s cubic-bezier(0.16,1,0.3,1)';
      el.style.opacity = '0';
      if (dir === 'up') el.style.transform = 'translateY(30px)';
      else if (dir === 'down') el.style.transform = 'translateY(-30px)';
      else if (dir === 'scale') el.style.transform = 'scale(0.95)';
      observer.observe(el);
    });
  });

  const s = document.createElement('style');
  s.textContent = '.revealed{opacity:1!important;transform:none!important;}';
  document.head.appendChild(s);
})();

// ─── TECH BAR ANIMATION ─────────────────────────────────────
(function() {
  'use strict';
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const fill = entry.target.querySelector('.tech-bar-fill');
        if (fill) {
          const w = getComputedStyle(fill).getPropertyValue('--width');
          fill.style.width = '0%';
          requestAnimationFrame(() => requestAnimationFrame(() => { fill.style.width = w; }));
        }
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tech-bar').forEach(el => obs.observe(el));
  });
})();

// ─── PAD CLICK (Controller Showcase Section) ────────────────
(function() {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.performance-pads .pad').forEach(pad => {
      pad.addEventListener('click', () => pad.classList.toggle('pad--active'));
    });
  });
})();

// ═══════════════════════════════════════════════════════════
// DJ CONTROLLER INTERACTIVE FEATURES
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  // ─── WAVEFORM GENERATOR ─────────────────────────────────
  ['waveformA', 'waveformB'].forEach(id => {
    const container = document.getElementById(id);
    if (!container) return;
    const count = 60;
    for (let i = 0; i < count; i++) {
      const bar = document.createElement('div');
      bar.className = 'w-bar';
      const x = i / count;
      const base = Math.sin(x * Math.PI) * 0.7;
      const noise = Math.random() * 0.3;
      bar.style.height = Math.max(3, (base + noise) * 24) + 'px';
      container.appendChild(bar);
    }
  });

  // ─── VINYL SPINNING + SCRATCH ──────────────────────────
  const vinylA = document.getElementById('vinylA');
  const vinylB = document.getElementById('vinylB');
  const playA = document.getElementById('playA');
  const playB = document.getElementById('playB');

  // Vinyl state
  const vinylState = {
    a: { playing: true, angle: 0, speed: 1.8 },  // degrees per frame at ~60fps
    b: { playing: true, angle: 0, speed: 1.8 }
  };

  if (playA) playA.classList.add('playing');
  if (playB) playB.classList.add('playing');

  if (playA) {
    playA.addEventListener('click', () => {
      vinylState.a.playing = !vinylState.a.playing;
      playA.classList.toggle('playing', vinylState.a.playing);
    });
  }
  if (playB) {
    playB.addEventListener('click', () => {
      vinylState.b.playing = !vinylState.b.playing;
      playB.classList.toggle('playing', vinylState.b.playing);
    });
  }

  // Animation loop for vinyl rotation
  let lastTime = 0;
  function animateVinyls(ts) {
    const dt = lastTime ? (ts - lastTime) / 16.667 : 1; // normalize to 60fps
    lastTime = ts;
    ['a', 'b'].forEach(key => {
      const state = vinylState[key];
      const vinyl = key === 'a' ? vinylA : vinylB;
      if (!vinyl) return;
      if (state.playing && !state.scratching) {
        state.angle = (state.angle + state.speed * dt) % 360;
      }
      vinyl.style.transform = 'rotate(' + state.angle + 'deg)';
    });
    requestAnimationFrame(animateVinyls);
  }
  requestAnimationFrame(animateVinyls);

  // ─── WEB AUDIO SCRATCH ENGINE ─────────────────────────
  let scratchCtx = null;
  let scratchNoiseBuffer = null;

  function getScratchCtx() {
    if (!scratchCtx) {
      scratchCtx = new (window.AudioContext || window.webkitAudioContext)();
      // Pre-generate noise buffer (1 second)
      const sr = scratchCtx.sampleRate;
      scratchNoiseBuffer = scratchCtx.createBuffer(1, sr, sr);
      const data = scratchNoiseBuffer.getChannelData(0);
      for (let i = 0; i < sr; i++) {
        data[i] = Math.random() * 2 - 1;
      }
    }
    if (scratchCtx.state === 'suspended') scratchCtx.resume();
    return scratchCtx;
  }

  function playScratchSound(speed, direction) {
    // speed: 0-1 intensity, direction: 1 forward, -1 backward
    try {
      const ctx = getScratchCtx();
      const src = ctx.createBufferSource();
      src.buffer = scratchNoiseBuffer;

      // Bandpass filter to shape scratch sound
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = 1200 + speed * 2000; // higher freq for faster scratch
      bp.Q.value = 2 + speed * 4;

      // Gain based on speed
      const gain = ctx.createGain();
      gain.gain.value = Math.min(0.35, 0.05 + speed * 0.3);
      gain.gain.linearRampToValueAtTime(0.001, ctx.currentTime + 0.08 + speed * 0.05);

      // Playback rate modulated by direction and speed
      src.playbackRate.value = (0.5 + speed * 2) * direction;

      src.connect(bp);
      bp.connect(gain);
      gain.connect(ctx.destination);
      src.start(0, Math.random() * 0.5, 0.15);
    } catch(e) { /* Audio not available */ }
  }

  // ─── VINYL TOUCH/MOUSE SCRATCH ────────────────────────
  [{ vinyl: vinylA, key: 'a' }, { vinyl: vinylB, key: 'b' }].forEach(({ vinyl, key }) => {
    if (!vinyl) return;
    const state = vinylState[key];
    let lastPointerAngle = 0;
    let scratchThrottle = 0;

    function getPointerAngle(e) {
      const rect = vinyl.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const pt = e.touches ? e.touches[0] : e;
      return Math.atan2(pt.clientY - cy, pt.clientX - cx) * (180 / Math.PI);
    }

    function onStart(e) {
      e.preventDefault();
      state.scratching = true;
      vinyl.classList.add('scratching');
      lastPointerAngle = getPointerAngle(e);
      document.addEventListener('mousemove', onMove);
      document.addEventListener('touchmove', onMove, { passive: false });
      document.addEventListener('mouseup', onEnd);
      document.addEventListener('touchend', onEnd);
    }

    function onMove(e) {
      if (!state.scratching) return;
      e.preventDefault();
      const currentAngle = getPointerAngle(e);
      let delta = currentAngle - lastPointerAngle;
      // Handle wrap-around at +/-180
      if (delta > 180) delta -= 360;
      if (delta < -180) delta += 360;
      lastPointerAngle = currentAngle;

      // Apply rotation
      state.angle = (state.angle + delta) % 360;

      // Play scratch sound (throttled)
      const now = performance.now();
      const absDelta = Math.abs(delta);
      if (absDelta > 0.5 && now - scratchThrottle > 40) {
        const speed = Math.min(1, absDelta / 15);
        const dir = delta > 0 ? 1 : -1;
        playScratchSound(speed, dir);
        scratchThrottle = now;
      }
    }

    function onEnd() {
      state.scratching = false;
      vinyl.classList.remove('scratching');
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('touchmove', onMove);
      document.removeEventListener('mouseup', onEnd);
      document.removeEventListener('touchend', onEnd);
    }

    vinyl.addEventListener('mousedown', onStart);
    vinyl.addEventListener('touchstart', onStart, { passive: false });
  });

  // ─── CROSSFADER DRAG ───────────────────────────────────
  const cfTrack = document.getElementById('crossfaderTrack');
  const cfKnob = document.getElementById('crossfaderKnob');
  if (cfTrack && cfKnob) {
    let dragging = false;
    function setCfPosition(clientX) {
      const rect = cfTrack.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      cfKnob.style.left = (pct * 100) + '%';
    }
    function onStart(e) {
      e.preventDefault();
      dragging = true;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      setCfPosition(clientX);
    }
    function onMove(e) {
      if (!dragging) return;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      setCfPosition(clientX);
    }
    function onEnd() { dragging = false; }
    cfTrack.addEventListener('mousedown', onStart);
    cfTrack.addEventListener('touchstart', onStart, { passive: false });
    cfKnob.addEventListener('mousedown', onStart);
    cfKnob.addEventListener('touchstart', onStart, { passive: false });
    document.addEventListener('mousemove', onMove);
    document.addEventListener('touchmove', onMove, { passive: false });
    document.addEventListener('mouseup', onEnd);
    document.addEventListener('touchend', onEnd);
  }

  // ─── FX PANEL ──────────────────────────────────────────
  const fxPanel = document.getElementById('fxPanel');
  const fxToggle = document.getElementById('fxToggle');
  const fxClose = document.getElementById('fxClose');
  const fxName = document.getElementById('fxName');
  const fxPrev = document.getElementById('fxPrev');
  const fxNext = document.getElementById('fxNext');
  const effects = ['Gate', 'Flanger', 'Echo', 'Reverb'];
  let currentFx = 0;

  if (fxToggle) fxToggle.addEventListener('click', () => {
    fxPanel.classList.toggle('visible');
    fxToggle.classList.toggle('active');
    samplePanel.classList.remove('visible');
    updateBottomNav('fx');
  });
  if (fxClose) fxClose.addEventListener('click', () => {
    fxPanel.classList.remove('visible');
    fxToggle.classList.remove('active');
    updateBottomNav('main');
  });
  if (fxPrev) fxPrev.addEventListener('click', () => {
    currentFx = (currentFx - 1 + effects.length) % effects.length;
    if (fxName) fxName.textContent = effects[currentFx];
  });
  if (fxNext) fxNext.addEventListener('click', () => {
    currentFx = (currentFx + 1) % effects.length;
    if (fxName) fxName.textContent = effects[currentFx];
  });

  // XY Pad touch
  const xyPad = document.getElementById('xyPad');
  const xyCursor = document.getElementById('xyCursor');
  if (xyPad && xyCursor) {
    let xyActive = false;
    function moveXY(e) {
      const rect = xyPad.getBoundingClientRect();
      const touch = e.touches ? e.touches[0] : e;
      const x = Math.max(0, Math.min(1, (touch.clientX - rect.left) / rect.width));
      const y = Math.max(0, Math.min(1, (touch.clientY - rect.top) / rect.height));
      xyCursor.style.left = (x * 100) + '%';
      xyCursor.style.top = (y * 100) + '%';
    }
    xyPad.addEventListener('mousedown', (e) => { xyActive = true; moveXY(e); });
    xyPad.addEventListener('touchstart', (e) => { e.preventDefault(); xyActive = true; moveXY(e); }, { passive: false });
    document.addEventListener('mousemove', (e) => { if (xyActive) moveXY(e); });
    document.addEventListener('touchmove', (e) => { if (xyActive) moveXY(e); }, { passive: false });
    document.addEventListener('mouseup', () => { xyActive = false; });
    document.addEventListener('touchend', () => { xyActive = false; });
  }

  // ─── SAMPLE PADS ──────────────────────────────────────
  const samplePanel = document.getElementById('samplePanel');
  const sampleClose = document.getElementById('sampleClose');

  // Apply pad colors
  document.querySelectorAll('.sample-pad').forEach(pad => {
    const color = pad.dataset.color;
    if (color) pad.style.setProperty('--pad-bg', color);
  });

  if (sampleClose) sampleClose.addEventListener('click', () => {
    samplePanel.classList.remove('visible');
    updateBottomNav('main');
  });

  // Web Audio API for sample sounds
  let audioCtx = null;
  function getAudioCtx() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
  }

  // Sound generators
  const soundGenerators = {
    airhorn: (ctx) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sawtooth'; o.frequency.value = 800;
      o.frequency.linearRampToValueAtTime(400, ctx.currentTime + 0.3);
      g.gain.value = 0.3;
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
      o.connect(g); g.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.4);
    },
    uhh: (ctx) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine'; o.frequency.value = 180;
      o.frequency.linearRampToValueAtTime(120, ctx.currentTime + 0.2);
      g.gain.value = 0.3;
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      o.connect(g); g.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.25);
    },
    echo: (ctx) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      const delay = ctx.createDelay(0.5);
      const fb = ctx.createGain();
      o.type = 'sine'; o.frequency.value = 1200;
      delay.delayTime.value = 0.1;
      fb.gain.value = 0.4;
      g.gain.value = 0.2;
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
      o.connect(g); g.connect(delay); delay.connect(fb); fb.connect(delay);
      g.connect(ctx.destination); delay.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.15);
    },
    chord: (ctx) => {
      [261.6, 329.6, 392].forEach(freq => {
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = 'triangle'; o.frequency.value = freq;
        g.gain.value = 0.15;
        g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
        o.connect(g); g.connect(ctx.destination);
        o.start(); o.stop(ctx.currentTime + 0.5);
      });
    },
    hat: (ctx) => {
      const bufSize = ctx.sampleRate * 0.05;
      const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < bufSize; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / bufSize);
      const src = ctx.createBufferSource();
      const hp = ctx.createBiquadFilter();
      hp.type = 'highpass'; hp.frequency.value = 8000;
      const g = ctx.createGain(); g.gain.value = 0.3;
      src.buffer = buf;
      src.connect(hp); hp.connect(g); g.connect(ctx.destination);
      src.start();
    },
    cymbal: (ctx) => {
      const bufSize = ctx.sampleRate * 0.2;
      const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < bufSize; i++) data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / bufSize, 2);
      const src = ctx.createBufferSource();
      const hp = ctx.createBiquadFilter();
      hp.type = 'highpass'; hp.frequency.value = 5000;
      const g = ctx.createGain(); g.gain.value = 0.25;
      src.buffer = buf;
      src.connect(hp); hp.connect(g); g.connect(ctx.destination);
      src.start();
    },
    kick: (ctx) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine'; o.frequency.value = 150;
      o.frequency.exponentialRampToValueAtTime(50, ctx.currentTime + 0.1);
      g.gain.value = 0.5;
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
      o.connect(g); g.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.2);
    },
    snare: (ctx) => {
      // Noise
      const bufSize = ctx.sampleRate * 0.1;
      const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < bufSize; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / bufSize);
      const src = ctx.createBufferSource();
      const g = ctx.createGain(); g.gain.value = 0.3;
      src.buffer = buf;
      src.connect(g); g.connect(ctx.destination);
      src.start();
      // Tone
      const o = ctx.createOscillator();
      const g2 = ctx.createGain();
      o.type = 'triangle'; o.frequency.value = 200;
      g2.gain.value = 0.2;
      g2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1);
      o.connect(g2); g2.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.1);
    }
  };

  document.querySelectorAll('.sample-pad').forEach(pad => {
    const handler = (e) => {
      e.preventDefault();
      const sound = pad.dataset.sound;
      if (sound && soundGenerators[sound]) {
        try {
          const ctx = getAudioCtx();
          soundGenerators[sound](ctx);
        } catch (err) { /* Audio not available */ }
      }
      pad.classList.add('triggered');
      setTimeout(() => pad.classList.remove('triggered'), 150);
    };
    pad.addEventListener('click', handler);
    pad.addEventListener('touchstart', handler, { passive: false });
  });

  // ─── BOTTOM NAVIGATION ────────────────────────────────
  const navEQ = document.getElementById('navEQ');
  const navMain = document.getElementById('navMain');
  const navSampler = document.getElementById('navSampler');

  function updateBottomNav(active) {
    [navEQ, navMain, navSampler].forEach(b => { if (b) b.classList.remove('active'); });
    if (active === 'fx' && navEQ) navEQ.classList.add('active');
    else if (active === 'sampler' && navSampler) navSampler.classList.add('active');
    else if (navMain) navMain.classList.add('active');
  }

  if (navEQ) navEQ.addEventListener('click', () => {
    const showing = fxPanel.classList.contains('visible');
    fxPanel.classList.toggle('visible', !showing);
    samplePanel.classList.remove('visible');
    fxToggle.classList.toggle('active', !showing);
    updateBottomNav(showing ? 'main' : 'fx');
  });

  if (navMain) navMain.addEventListener('click', () => {
    fxPanel.classList.remove('visible');
    samplePanel.classList.remove('visible');
    fxToggle.classList.remove('active');
    updateBottomNav('main');
  });

  if (navSampler) navSampler.addEventListener('click', () => {
    const showing = samplePanel.classList.contains('visible');
    samplePanel.classList.toggle('visible', !showing);
    fxPanel.classList.remove('visible');
    fxToggle.classList.remove('active');
    updateBottomNav(showing ? 'main' : 'sampler');
  });

  // ─── POWER BUTTON ─────────────────────────────────────
  const powerBtn = document.getElementById('powerBtn');
  if (powerBtn) {
    powerBtn.addEventListener('click', () => {
      powerBtn.classList.toggle('active');
    });
  }
});

/* ===== Web MIDI API: DDJ-FLX4 Connection Detection ===== */
(function() {
  var controllerDot = document.getElementById('controllerDot');
  var controllerLabel = document.getElementById('controllerLabel');
  var automixSwitch = document.getElementById('automixSwitch');
  var automixMainSwitch = document.getElementById('automixMainSwitch');
  var automixPanel = document.getElementById('automixPanel');
  var automixClose = document.getElementById('automixClose');
  var automixToggleBar = document.getElementById('automixToggle');
  var automixStatus = document.getElementById('automixStatus');
  var tabManual = document.getElementById('tabManual');
  var tabAutomix = document.getElementById('tabAutomix');
  var isAutomix = false;
  var controllerConnected = false;

  // DDJ-FLX4 connection detection via Web MIDI
  function initMIDI() {
    if (!navigator.requestMIDIAccess) {
      controllerLabel.textContent = 'MIDI not supported';
      return;
    }
    navigator.requestMIDIAccess({ sysex: false }).then(function(midi) {
      function checkDevices() {
        var found = false;
        midi.inputs.forEach(function(input) {
          var name = input.name || '';
          if (name.toLowerCase().indexOf('ddj') !== -1 || 
              name.toLowerCase().indexOf('pioneer') !== -1 ||
              name.toLowerCase().indexOf('flx') !== -1) {
            found = true;
            connectController(name);
          }
        });
        if (!found && controllerConnected) {
          disconnectController();
        }
      }
      midi.onstatechange = function() { checkDevices(); };
      checkDevices();
    }).catch(function() {
      controllerLabel.textContent = 'MIDI access denied';
    });
  }

  function connectController(name) {
    controllerConnected = true;
    controllerDot.className = 'conn-dot conn-dot--connected';
    controllerLabel.textContent = name + ' Connected';
    controllerLabel.style.color = '#00e676';
    // Log to Supabase
    logToSupabase('mix_sessions', {
      session_name: 'Live Session',
      controller_connected: true,
      controller_model: name
    });
  }

  function disconnectController() {
    controllerConnected = false;
    controllerDot.className = 'conn-dot conn-dot--red';
    controllerLabel.textContent = 'DDJ-FLX4 Disconnected';
    controllerLabel.style.color = '';
  }

  // Automix toggle
  function toggleAutomix() {
    isAutomix = !isAutomix;
    if (automixSwitch) automixSwitch.classList.toggle('active', isAutomix);
    if (automixMainSwitch) automixMainSwitch.classList.toggle('active', isAutomix);
    if (automixStatus) automixStatus.textContent = isAutomix ? 'On' : 'Off';
    if (tabManual) tabManual.classList.toggle('mode-tab--active', !isAutomix);
    if (tabAutomix) tabAutomix.classList.toggle('mode-tab--active', isAutomix);
    // Visual feedback
    if (isAutomix) {
      document.body.classList.add('automix-active');
    } else {
      document.body.classList.remove('automix-active');
    }
  }

  if (automixSwitch) automixSwitch.addEventListener('click', toggleAutomix);
  if (automixMainSwitch) automixMainSwitch.addEventListener('click', toggleAutomix);
  if (automixToggleBar) {
    automixToggleBar.addEventListener('click', function() {
      if (automixPanel) {
        automixPanel.style.display = automixPanel.style.display === 'none' ? 'block' : 'none';
      }
    });
  }
  if (automixClose) {
    automixClose.addEventListener('click', function() {
      if (automixPanel) automixPanel.style.display = 'none';
    });
  }
  if (tabManual) {
    tabManual.addEventListener('click', function() { if (isAutomix) toggleAutomix(); });
  }
  if (tabAutomix) {
    tabAutomix.addEventListener('click', function() { if (!isAutomix) toggleAutomix(); });
  }

  // Supabase REST helper
  var SUPABASE_URL = 'https://ansiaiuaygcfztabtknl.supabase.co';
  var SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFuc2lhaXVheWdjZnp0YWJ0a25sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMwNjg2NjksImV4cCI6MjA3ODY0NDY2OX0.-a4CakCH4DhHGOG1vMo9nVdtW0ux252QqXRi-7CA_gA';

  function logToSupabase(table, data) {
    fetch(SUPABASE_URL + '/rest/v1/' + table, {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + SUPABASE_KEY,
        'Content-Type': 'application/json',
        'Content-Profile': 'public',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify(data)
    }).catch(function() {});
  }

  // Log page view as a track session
  logToSupabase('page_views', {
    site_name: 'rhythmclaw',
    page_path: window.location.pathname,
    referrer: document.referrer || '',
    user_agent: navigator.userAgent,
    session_id: Math.random().toString(36).slice(2)
  });

  // Initialize MIDI on load
  if (document.readyState === 'complete') {
    initMIDI();
  } else {
    window.addEventListener('load', initMIDI);
  }
})();
