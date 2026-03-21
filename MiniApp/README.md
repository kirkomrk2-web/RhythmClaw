# RhythmClaw — Telegram Mini App DJ Mini-Player

## Overview

RhythmClaw Mini App is a Telegram-native DJ control surface that runs inside any
Telegram chat as a Mini App. It connects to the RhythmClaw MIDI server to
provide real-time transport controls, waveform visualization, crossfader mixing,
and track-liking—all from a compact, draggable player that can snap to the
screen edge for a minimal footprint.

## Screenshots

> **Default state** — Full player showing track info, waveform, transport
> controls, like button, and crossfader bar.

> **Collapsed state** — A thin vertical tab pinned to the left or right edge of
> the screen with a small waveform icon. Tap to expand.

> **Expanded state** — Player slides back in from the edge with a smooth 300 ms
> animation.

*(Replace these placeholders with actual screenshots after deployment.)*

## Setup

### Prerequisites

| Requirement | Why |
|---|---|
| **HTTPS hosting** | Telegram Mini Apps require a valid TLS certificate. |
| **RhythmClaw MIDI server** | The player calls `/api/v1/*` endpoints on the server. |
| **Telegram Bot** | You need a bot token from [@BotFather](https://t.me/BotFather). |

### Configure the MIDI Server URL

Open `app.js` and update the `MIDI_SERVER_URL` fallback to point at your running
MIDI server instance:

```javascript
const MIDI_SERVER_URL =
  (tg.initDataUnsafe && tg.initDataUnsafe.start_param) ||
  localStorage.getItem('rhythmclaw_server') ||
  'https://your-server.example.com';   // ← change this
```

Alternatively, pass the URL as the `start_param` when launching the Mini App
from your bot.

### Register with BotFather

1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. Send `/newapp` and select your bot.
3. Follow the prompts to set a title, description, and photo.
4. When asked for the **Web App URL**, enter the HTTPS URL where the Mini App is
   hosted (e.g., `https://yourdomain.com/MiniApp/`).

## Deployment Options

### GitHub Pages

```bash
# 1. Push MiniApp/ to a GitHub repository (it can be this repo).
git add MiniApp/
git commit -m "Add Telegram Mini App"
git push

# 2. In the repo Settings → Pages, choose the branch and folder
#    (e.g., main / docs or main / MiniApp).

# 3. (Optional) Set a custom domain under Settings → Pages → Custom domain
#    and configure DNS. GitHub will provision a TLS certificate automatically.
```

After deployment the app will be available at:

```
https://<username>.github.io/<repo>/MiniApp/
```

### Vercel

```bash
# From the repository root:
npx vercel --prod

# Vercel auto-detects the static site structure. Set the root directory to
# MiniApp/ if prompted, or add a vercel.json:
# {
#   "outputDirectory": "MiniApp"
# }
```

Vercel provides HTTPS out of the box on `*.vercel.app` domains.

### Netlify

1. Connect your repository on [Netlify](https://app.netlify.com/).
2. Set **Publish directory** to `MiniApp`.
3. Deploy. Netlify provides HTTPS automatically.

## Telegram Configuration

### Set the Web App URL

```
/setmenubutton
```

Select your bot, then provide the Mini App URL. This adds a button to every chat
with the bot that opens the Mini App directly.

### Domain Whitelist

In BotFather:

```
/setdomain
```

Add the domain where the Mini App is hosted so Telegram can validate it.

## Architecture

```
┌──────────────────┐         HTTPS/JSON          ┌──────────────┐
│  Telegram Client │  ◄─────────────────────────► │  Mini App    │
│  (WebView)       │                              │  (index.html │
└──────────────────┘                              │   + app.js)  │
                                                  └──────┬───────┘
                                                         │ fetch
                                                         ▼
                                                  ┌──────────────┐
                                                  │  MIDI Server │
                                                  │  /api/v1/*   │
                                                  └──────────────┘
```

- **State management** — A single `state` object in `app.js` is the source of
  truth. UI is rendered from state via small `render*()` helpers.
- **Polling** — The app polls `GET /api/v1/status` every 2 seconds to stay in
  sync with the MIDI server. Future versions may upgrade to WebSockets.
- **Offline / background** — When the Telegram WebView is backgrounded, polling
  pauses automatically (the browser suspends `setInterval`). The player
  re-syncs on the next poll when brought back to the foreground.

## Browser Compatibility

| Platform | Status |
|---|---|
| Telegram for **iOS** | ✅ Tested |
| Telegram for **Android** | ✅ Tested |
| Telegram **Desktop** (Windows / macOS / Linux) | ✅ Tested (drag/edge-snap requires touch) |

## Known Limitations

- **Picture-in-Picture (PiP)** — Behavior varies by OS and Telegram version.
  Some platforms do not support PiP for Mini App WebViews.
- **Background playback** — Actual audio playback is handled by the MIDI server,
  not the Mini App itself. The Mini App is a remote control; closing it does not
  stop playback.
- **Edge snap is touch-only** — Drag-to-edge collapsing relies on touch events
  and does not activate with mouse drag on desktop clients.
- **Pinch-to-resize** — Only works on touch-capable devices.

## Development

### Run Locally

Serve the `MiniApp` directory over HTTP:

```bash
# Python
python3 -m http.server 8000 --directory MiniApp

# Node.js (npx, no install needed)
npx serve MiniApp
```

### Expose via HTTPS (required for Telegram testing)

Use [ngrok](https://ngrok.com/) to tunnel your local server:

```bash
ngrok http 8000
```

Copy the generated `https://` URL and set it as the Web App URL in BotFather.

### Hot Reload

For a smoother development loop, use a live-reload server:

```bash
npx browser-sync start --server MiniApp --files "MiniApp/*"
```

Then point ngrok at the browser-sync port.
