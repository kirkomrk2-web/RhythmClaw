# RhythmClaw Telegram Bot — UI Specification

> Version 1.0 · Last updated: 2025

---

## Table of Contents

1. [Overview](#1-overview)
2. [ASCII Wireframes](#2-ascii-wireframes)
3. [Navigation Flow](#3-navigation-flow)
4. [Message Lifecycle](#4-message-lifecycle)
5. [Bilingual Support](#5-bilingual-support)
6. [Auto-Clear Behaviour](#6-auto-clear-behaviour)
7. [Like / Star Feature](#7-like--star-feature)
8. [Error State Handling](#8-error-state-handling)
9. [Accessibility Considerations](#9-accessibility-considerations)

---

## 1. Overview

The RhythmClaw Telegram bot provides a complete DJ control panel for the
Pioneer DDJ-FLX4 controller.  All interaction happens through **inline
keyboards** attached to a single bot message that is **edited in place**
("reframe animation") as the user navigates menus.

Key design principles:

| Principle | Detail |
|---|---|
| Single-message UI | Only one active menu message per user at any time |
| In-place transitions | `editMessageText` replaces content; no new messages |
| Navigation stack | Per-user stack enables **◀️ Back** at every level |
| Auto-delete | Previous bot messages are removed (except Now Playing) |
| Bilingual | Every string supports English (EN) and Bulgarian (BG) |

---

## 2. ASCII Wireframes

### 2.1 Main Menu (`/start`)

```
┌──────────────────────────────────────────┐
│  🎵 RhythmClaw — DJ Control Panel       │
│                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ ▶️ Play  │ │ ⏸ Pause  │ │ ⏭ Skip  │ │
│  └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ 🎛 Decks │ │ 🔀 Queue │ │ 🎚 FX   │ │
│  └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │📂 Library│ │ ⭐ Favs  │ │⚙️ Settings│ │
│  └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────────────────────────────────┐│
│  │            🌐 BG/EN                  ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### 2.2 Deck Selection

```
┌──────────────────────────────────────────┐
│  🎛 Select Deck                          │
│                                          │
│  ┌──────────────┐ ┌──────────────┐       │
│  │  🎛 Deck 1   │ │  🎛 Deck 2   │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────────────────────────────┐│
│  │            ◀️ Back                   ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### 2.3 Deck Controls (e.g. Deck 1)

```
┌──────────────────────────────────────────┐
│  🎛 Deck 1 Controls                      │
│                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ ▶️ Play  │ │ ⏸ Pause  │ │ 🔄 Sync │ │
│  └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────────┐ ┌──────────────┐       │
│  │   🎯 CUE     │ │   ⏭ Skip     │       │
│  └──────────────┘ └──────────────┘       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  │  HC 1  │ │  HC 2  │ │  HC 3  │ │  HC 4  │
│  └────────┘ └────────┘ └────────┘ └────────┘
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  │  HC 5  │ │  HC 6  │ │  HC 7  │ │  HC 8  │
│  └────────┘ └────────┘ └────────┘ └────────┘
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  │Loop ½  │ │ Loop 1 │ │ Loop 2 │ │ Loop 4 │
│  └────────┘ └────────┘ └────────┘ └────────┘
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  │Jump ◀2 │ │Jump ◀4 │ │Jump 8▶ │ │Jump16▶ │
│  └────────┘ └────────┘ └────────┘ └────────┘
│  ┌──────────────────────────────────────┐│
│  │            ◀️ Back                   ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### 2.4 Queue

```
┌──────────────────────────────────────────┐
│  🔀 Queue                                │
│                                          │
│  1. Track Alpha — Artist A               │
│  2. Track Beta — Artist B                │
│  3. Track Gamma — Artist C               │
│  (up to 8 items shown)                   │
│                                          │
│  ┌──────────────┐ ┌──────────────┐       │
│  │ ➕ Add Song  │ │ 🗑 Clear     │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────────────────────────────┐│
│  │            ◀️ Back                   ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### 2.5 FX Controls

```
┌──────────────────────────────────────────┐
│  🎚 FX Controls                          │
│                                          │
│  ┌──────────────┐ ┌──────────────┐       │
│  │ FX1: ON  ✅  │ │ FX2: OFF ❌  │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────────────────────────────┐│
│  │            ◀️ Back                   ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### 2.6 Library

```
┌──────────────────────────────────────────┐
│  📂 Library — Choose Source              │
│                                          │
│  ┌──────────────┐ ┌──────────────┐       │
│  │ 🎵 Spotify   │ │🍎 Apple Music│       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐       │
│  │ ▶️ YouTube   │ │ 🌊 Tidal     │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────────────────────────────┐│
│  │         📁 Upload MP3/MP4            ││
│  └──────────────────────────────────────┘│
│  ┌──────────────────────────────────────┐│
│  │            ◀️ Back                   ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### 2.7 Favourites

```
┌──────────────────────────────────────────┐
│  ⭐ Favourites                           │
│                                          │
│  1. Blinding Lights — The Weeknd         │
│  2. Levitating — Dua Lipa               │
│  3. Don't Start Now — Dua Lipa          │
│                                          │
│  ┌──────────────┐ ┌──────────────┐       │
│  │ 1. Load D1   │ │ 1. Load D2   │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐       │
│  │ 2. Load D1   │ │ 2. Load D2   │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐       │
│  │ 3. Load D1   │ │ 3. Load D2   │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────────────────────────────┐│
│  │            ◀️ Back                   ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### 2.8 Settings

```
┌──────────────────────────────────────────┐
│  ⚙️ Settings                             │
│                                          │
│  ┌──────────────────────────────────────┐│
│  │         🌐 Language: EN              ││
│  └──────────────────────────────────────┘│
│  ┌──────────────────────────────────────┐│
│  │      📊 BPM Display: ON             ││
│  └──────────────────────────────────────┘│
│  ┌──────────────────────────────────────┐│
│  │      🔔 Notifications: ON           ││
│  └──────────────────────────────────────┘│
│  ┌──────────────────────────────────────┐│
│  │            ◀️ Back                   ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### 2.9 Now Playing

```
┌──────────────────────────────────────────┐
│  🎵 Now Playing                          │
│                                          │
│  🎶 Blinding Lights — The Weeknd        │
│  🎛 Deck 1  |  BPM: 171                 │
│                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ ❤️ Like  │ │ ⏭ Skip  │ │ ⏸ Pause  │ │
│  └──────────┘ └──────────┘ └──────────┘ │
└──────────────────────────────────────────┘
```

### 2.10 History

```
┌──────────────────────────────────────────┐
│  📜 Recently Played                      │
│                                          │
│  1. Don't Start Now — Dua Lipa          │
│  2. Blinding Lights — The Weeknd        │
│  3. Save Your Tears — The Weeknd        │
│  4. Physical — Dua Lipa                 │
│  5. Take On Me — a-ha                   │
│                                          │
│  ┌──────────────────────────────────────┐│
│  │            ◀️ Back                   ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

---

## 3. Navigation Flow

```
                        /start
                          │
                          ▼
                   ┌─────────────┐
                   │  MAIN MENU  │◄──────────────────────────────────┐
                   └──────┬──────┘                                   │
        ┌────────┬────────┼────────┬────────┬────────┐               │
        ▼        ▼        ▼        ▼        ▼        ▼               │
    ┌───────┐┌───────┐┌──────┐┌────────┐┌──────┐┌────────┐          │
    │ Decks ││ Queue ││  FX  ││Library ││ Favs ││Settings│          │
    └───┬───┘└───┬───┘└──┬───┘└───┬────┘└──┬───┘└───┬────┘          │
        │        │       │        │        │        │               │
        ▼        │       │        │        │        │               │
  ┌──────────┐   │       │        │        │        │               │
  │Deck 1 / 2│   │       │        │        │        │               │
  │ Controls │   │       │        │        │        │               │
  └─────┬────┘   │       │        │        │        │               │
        │        │       │        │        │        │               │
        └────────┴───────┴────────┴────────┴────────┘               │
                          │                                          │
                     ◀️ Back ─────────────────────────────────────────┘

  Standalone (no auto-delete):

    /nowplaying ──► Now Playing card (edited in place, persistent)
    /history    ──► History view (Back → Main Menu)
```

### Navigation Stack Example

| User action | Stack state |
|---|---|
| `/start` | `[main]` |
| Tap 🎛 Decks | `[main, decks]` |
| Tap Deck 1 | `[main, decks, deck_control:1]` |
| Tap ◀️ Back | `[main, decks]` |
| Tap ◀️ Back | `[main]` |

The stack is stored per `user_id` and reset on `/start`.

---

## 4. Message Lifecycle

### 4.1 Creation Rules

| Trigger | Action |
|---|---|
| `/start` | Delete any existing menu message → send new |
| Menu button press | `editMessageText` on current message |
| `editMessageText` fails | Delete old → send new message |
| `/nowplaying` | Send or edit the Now Playing message |
| `/history` | Delete old menu → send history view |
| `/help` | Delete old menu → send help text |
| File upload | Send processing → success / error message |

### 4.2 Edit (Reframe) Rules

- All sub-menu navigation uses `editMessageText` on the same message.
- If editing fails (e.g. message too old, deleted by user), the bot
  falls back to deleting the old message and sending a new one.

### 4.3 Deletion Rules

| Message type | Auto-deleted? | When? |
|---|---|---|
| Menu messages | ✅ Yes | Before sending the next menu message |
| Now Playing | ❌ No | Kept and updated in place |
| History | ❌ No | Kept; Back button returns to main menu |
| Help text | ✅ Yes | Replaced when user opens a new menu |
| Upload status | ✅ Yes | Replaced on next interaction |
| Error messages | ✅ Yes | Replaced on next interaction |

### 4.4 Message ID Tracking

```
last_message_id[user_id]        → most recent bot menu message
now_playing_message_id[user_id] → persistent Now Playing card
```

---

## 5. Bilingual Support

### 5.1 Language Storage

- **Primary store**: Supabase `user_preferences` table
  ```
  user_id (text PK) | language (text) | bpm_display (bool) | notifications (bool)
  ```
- **In-memory cache**: `user_language[user_id]` for fast lookups
- **Default**: `en` (English)

### 5.2 Translation System

- All user-facing strings are stored in `Config/translations.json`
- Helper function `t(key, lang)` returns the localised string
- Fallback chain: requested language → English → raw key name
- Format placeholders use Python `str.format()` syntax: `{track}`, `{deck}`, `{bpm}`

### 5.3 Language Toggle

- **Main menu**: 🌐 BG/EN button toggles between `en` and `bg`
- **Settings menu**: 🌐 Language: EN/BG button (same action)
- On toggle:
  1. New language is saved to Supabase and cache
  2. Current menu is re-rendered in the new language (in place)

### 5.4 Translation Key Count

Each language must have **60+ keys** covering:

| Category | Example keys |
|---|---|
| Menu titles | `main_menu_title`, `deck_select_title`, `queue_title` |
| Button labels | `play`, `pause`, `skip`, `sync`, `cue`, `back` |
| Status messages | `play_confirm`, `pause_confirm`, `skip_confirm` |
| Error messages | `error_generic`, `error_midi`, `error_network` |
| Queue messages | `queue_empty`, `queue_cleared`, `queue_add_prompt` |
| FX labels | `fx1_on`, `fx1_off`, `fx_toggled` |
| Library items | `lib_spotify`, `lib_apple`, `lib_upload` |
| Now Playing | `now_playing_template`, `like`, `liked_confirm` |
| Settings | `settings_lang`, `settings_bpm_on`, `settings_notif_off` |
| Upload | `upload_processing`, `upload_success`, `upload_failed` |
| General | `loading`, `yes`, `no`, `cancelled` |

---

## 6. Auto-Clear Behaviour

### 6.1 Core Rule

> After each interaction, the previous bot message is deleted
> **except** the Now Playing card.

### 6.2 Implementation

```python
async def delete_last_message(user_id, context, chat_id):
    msg_id = last_message_id.pop(user_id, None)
    if msg_id:
        await context.bot.delete_message(chat_id, msg_id)
```

### 6.3 Sequence Diagram

```
User taps [🎛 Decks]
  │
  ├─► Bot calls editMessageText(current_msg, deck_select_menu)
  │   └─► Success: message updated in place (no delete needed)
  │   └─► Failure: delete current_msg → send new message
  │
  └─► last_message_id[user_id] = new message id
```

### 6.4 Edge Cases

| Scenario | Behaviour |
|---|---|
| User deletes bot message manually | `editMessageText` fails → fallback to new message |
| User sends `/start` mid-navigation | Stack is reset; old message deleted; new main menu sent |
| Bot restarts | In-memory state lost; user must `/start` again |
| Multiple rapid taps | Each edit is atomic; Telegram API handles ordering |

---

## 7. Like / Star Feature

### 7.1 Overview

Users can "like" the currently playing track from the Now Playing card.
Liked tracks appear in the ⭐ Favourites menu and can be loaded to
either deck.

### 7.2 Data Model (Supabase)

```sql
CREATE TABLE favorites (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    track_id    TEXT NOT NULL,
    track_name  TEXT NOT NULL,
    timestamp   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, track_id)
);
```

### 7.3 Like Flow

```
User taps [❤️ Like] on Now Playing card
  │
  ├─► Bot fetches current track info from MIDI server (GET /now_playing)
  ├─► Bot upserts record into Supabase `favorites` table
  ├─► Bot shows toast: ❤️ Added "Track Name" to Favourites!
  │   (via answerCallbackQuery, non-blocking)
  └─► Now Playing card is NOT modified (stays in place)
```

### 7.4 Favourites Menu Flow

```
User taps [⭐ Favs] from Main Menu
  │
  ├─► Bot fetches user's favorites from Supabase (up to 10)
  ├─► Renders numbered list with [Load D1] [Load D2] per track
  └─► User taps [Load D1] → POST /deck/1/load { track_id }
      └─► Toast: ✅ Loaded to Deck 1.
```

### 7.5 Duplicate Handling

The `UNIQUE(user_id, track_id)` constraint with `UPSERT` ensures that
liking the same track twice simply updates the timestamp.

---

## 8. Error State Handling

### 8.1 Error Categories

| Error | User-facing message | Recovery |
|---|---|---|
| MIDI server unreachable | "Could not reach the DJ controller. Is it connected?" | Toast notification; menu stays |
| Supabase error | "Something went wrong. Please try again." | Graceful fallback; defaults used |
| Invalid file upload | "Please upload an MP3 or MP4 file only." | Informational message |
| Upload processing error | "Upload failed. Please try again." | User can retry |
| Network timeout | "Network error. Please check your connection." | Toast notification |
| Unknown callback data | Logged server-side; no user message | Silent |
| Telegram API error | Logged server-side; fallback to new message | Automatic recovery |

### 8.2 Error Display Rules

- **Transient errors** (MIDI, network): shown as `answerCallbackQuery` toast
  — the menu remains visible and usable.
- **Blocking errors** (upload failure): shown as a regular message that is
  auto-deleted on the next interaction.
- **Fatal errors** (unhandled exceptions): caught by the global error
  handler; a generic error message is sent to the user.

### 8.3 Resilience Patterns

1. **HTTP retry**: `httpx.AsyncClient` with a 10-second timeout. No
   automatic retry — failures surface immediately to the user.
2. **Supabase fallback**: if the database is unreachable, language
   defaults to `en`, settings default to `True`, and favourites return
   an empty list.
3. **Message edit fallback**: if `editMessageText` raises an exception,
   the bot deletes the old message and sends a new one.
4. **Graceful degradation**: the bot remains functional even if the MIDI
   server is down — menus still render, only actions that require the
   server will show an error toast.

---

## 9. Accessibility Considerations

### 9.1 Emoji as Visual Anchors

Every button and menu title uses a leading emoji to provide a visual
landmark.  This helps users quickly scan the keyboard:

| Emoji | Meaning |
|---|---|
| ▶️ | Play / start |
| ⏸ | Pause |
| ⏭ | Skip / next |
| 🎛 | Deck / mixer |
| 🔀 | Queue / shuffle |
| 🎚 | FX / fader |
| 📂 | Library / files |
| ⭐ | Favourites |
| ⚙️ | Settings |
| ◀️ | Back / navigation |
| ❤️ | Like / favourite |
| 🌐 | Language toggle |

### 9.2 Consistent Layout

- Transport controls (Play, Pause, Skip) are always in the **first row**
  on any screen that has them.
- The **◀️ Back** button is always the **last row**, full width.
- Grid-based layouts use a consistent number of columns (3 or 4).

### 9.3 Feedback

- Every action produces immediate feedback: either the menu updates, or
  a toast notification appears via `answerCallbackQuery`.
- Destructive actions (Clear Queue) show a confirmation toast.

### 9.4 Text Readability

- HTML bold (`<b>`) is used for menu titles.
- Track listings use numbered lists for scanability.
- Status info (BPM, deck number) is always on its own line with clear
  labels.

### 9.5 Language Accessibility

- The bot supports two languages (EN/BG) switchable at any time.
- The language toggle is available from both the main menu and the
  settings menu for easy discoverability.
- Switching languages re-renders the current screen immediately — no
  need to navigate away.

### 9.6 Screen Reader Compatibility

- Telegram inline buttons carry their text labels, which are read by
  screen readers on mobile devices.
- Emoji are followed by text labels (e.g. "▶️ Play" not just "▶️") so
  screen readers announce meaningful content.
- Avoid using emoji-only buttons.

---

## Appendix A: Callback Data Schema

All `callback_data` strings follow a prefix-based routing pattern:

| Prefix | Format | Example |
|---|---|---|
| `cmd:` | `cmd:<action>` | `cmd:play`, `cmd:pause` |
| `menu:` | `menu:<name>` | `menu:decks`, `menu:queue` |
| `nav:` | `nav:back` | `nav:back` |
| `deck:` | `deck:<n>:<action>` | `deck:1:play`, `deck:2:hotcue:3` |
| `queue:` | `queue:<action>` | `queue:add`, `queue:clear` |
| `fx:` | `fx:toggle:<n>` | `fx:toggle:1` |
| `lib:` | `lib:<source>` | `lib:spotify`, `lib:upload` |
| `fav:` | `fav:load:<deck>:<id>` | `fav:load:1:abc123` |
| `settings:` | `settings:toggle:<key>` | `settings:toggle:bpm_display` |
| `action:` | `action:<name>` | `action:toggle_lang` |
| `np:` | `np:<action>` | `np:like`, `np:skip` |

---

## Appendix B: Supabase Tables

### `user_preferences`

| Column | Type | Default | Description |
|---|---|---|---|
| `user_id` | `text` (PK) | — | Telegram user ID |
| `language` | `text` | `'en'` | `en` or `bg` |
| `bpm_display` | `boolean` | `true` | Show BPM in Now Playing |
| `notifications` | `boolean` | `true` | Send track-change notifications |

### `favorites`

| Column | Type | Default | Description |
|---|---|---|---|
| `id` | `bigserial` (PK) | auto | Row ID |
| `user_id` | `text` | — | Telegram user ID |
| `track_id` | `text` | — | Unique track identifier |
| `track_name` | `text` | — | Human-readable track name |
| `timestamp` | `timestamptz` | `now()` | When the track was liked |

Unique constraint: `(user_id, track_id)`

---

## Appendix C: Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `MIDI_SERVER_URL` | ❌ | FastAPI MIDI server URL (default: `http://localhost:8000`) |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon or service-role key |
