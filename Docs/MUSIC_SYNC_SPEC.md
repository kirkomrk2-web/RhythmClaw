# RhythmClaw — Music Sync System Specification

## 1. Overview

The Music Sync module lets RhythmClaw users import music from external streaming services and local files into a unified library stored in **Supabase**. Audio files are persisted on disk and served by the Telegram bot for playback, queuing, and playlist management.

Supported sources:

| Provider | Status | Auth | Download Method |
|---|---|---|---|
| Spotify | ✅ Implemented | OAuth 2.0 | YouTube-matched audio via yt-dlp |
| Apple Music | 🚧 Placeholder | MusicKit JWT + User Token | YouTube-matched (planned) |
| YouTube Music | ✅ Implemented | None (public) | Direct yt-dlp download |
| Tidal | ✅ Implemented | OAuth 2.0 / Device Code | YouTube-matched audio via yt-dlp |
| Local Upload | ✅ Implemented | N/A | Telegram file upload |

---

## 2. Architecture Diagram

```
┌──────────────┐
│ Telegram User │
└──────┬───────┘
       │  /sync, /import, file upload
       ▼
┌──────────────┐
│  Telegram Bot │  (bot.py / handlers)
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│            music_sync.py                     │
│                                              │
│  ┌────────────┐  ┌──────────────────┐       │
│  │ MusicProvider│  │ LocalUploadHandler│      │
│  │  (abstract) │  └──────────────────┘       │
│  └─────┬──────┘                              │
│        │                                     │
│  ┌─────┴──────────────────────────────┐      │
│  │  SpotifyProvider                   │      │
│  │  AppleMusicProvider (placeholder)  │      │
│  │  YouTubeMusicProvider              │      │
│  │  TidalProvider                     │      │
│  └────────────────────────────────────┘      │
│                                              │
│  Helper functions:                           │
│    search_library()                          │
│    get_library_tracks()                      │
│    delete_track()                            │
│    get_track_file_path()                     │
└──────────┬──────────────┬────────────────────┘
           │              │
           ▼              ▼
  ┌────────────┐   ┌──────────────────┐
  │  Supabase  │   │  Local Disk      │
  │  (library, │   │  SSOT/Music/     │
  │  playlists,│   │    Downloads/    │
  │  playlist_ │   │    Uploads/      │
  │  tracks)   │   │                  │
  └────────────┘   └──────────────────┘
```

---

## 3. Provider Details

### 3.1 Spotify

| Item | Detail |
|---|---|
| **Library** | [spotipy](https://github.com/spotipy-dev/spotipy) |
| **Auth** | OAuth 2.0 Authorization Code flow |
| **Scopes** | `playlist-read-private`, `user-library-read` |
| **Download** | Search YouTube for `"{track} {artist}"`, download via yt-dlp |
| **Rate Limits** | ~180 requests / minute (Spotify Web API) |
| **Required Env** | `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI` |

**Auth flow:**

1. Bot calls `SpotifyProvider.get_auth_url(user_id)` → returns URL.
2. User opens URL, authorises, Spotify redirects with `code`.
3. Bot calls `SpotifyProvider.handle_callback(code)` → token stored.

**Limitations:**

- Spotify does not expose direct audio streams; download is via YouTube match.
- Matched audio may occasionally differ from the Spotify version.
- Token expires after 1 hour; spotipy handles refresh automatically.

### 3.2 Apple Music

| Item | Detail |
|---|---|
| **Status** | 🚧 Placeholder — not yet implemented |
| **Auth** | MusicKit developer token (ES256 JWT) + user token |
| **API base** | `https://api.music.apple.com/v1` |
| **Required keys** | Apple Developer account, MusicKit private key |

**Planned endpoints:**

- `GET /v1/me/library/playlists`
- `GET /v1/me/library/playlists/{id}/tracks`
- `GET /v1/catalog/{storefront}/songs/{id}`
- `GET /v1/me/library/songs`

**TODOs:**

- Generate ES256 JWT developer token.
- Implement browser-based user-token acquisition.
- Map catalog metadata to YouTube search for download.

### 3.3 YouTube Music

| Item | Detail |
|---|---|
| **Library** | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| **Auth** | None (public content only) |
| **Download** | Direct audio extraction to MP3 |
| **Quality** | Configurable; default **192 kbps** |
| **Required Env** | *(none — yt-dlp uses public endpoints)* |

**Capabilities:**

- `search(query)` — keyword search via `ytsearch`.
- `download(url)` — download + FFmpeg post-processing to MP3.
- `import_from_url(url)` — download + metadata extraction + Supabase insert.
- `get_tracks(playlist_id)` — flat-playlist extraction for YouTube playlists.

**Limitations:**

- Subject to YouTube rate limits and potential IP blocks for heavy use.
- Audio quality depends on the source video.
- Some region-locked content may fail to download.

### 3.4 Tidal

| Item | Detail |
|---|---|
| **Library** | [python-tidal (tidalapi)](https://github.com/tamland/python-tidal) |
| **Auth** | OAuth 2.0 Device Code flow |
| **Download** | YouTube-matched audio via yt-dlp (same as Spotify) |
| **Required Env** | `TIDAL_CLIENT_ID`, `TIDAL_CLIENT_SECRET` |

**Auth flow:**

1. Bot calls `TidalProvider.authenticate()` → returns device-code URL.
2. User opens URL and authorises on Tidal's website.
3. Bot polls or user triggers `authenticate(oauth_token=...)` to complete.

**Capabilities:**

- `get_playlists()` — user playlists.
- `get_tracks(playlist_id)` — playlist tracks.
- `get_favorites()` — user's favourite / liked tracks.
- `import_track(track_id)` — search YouTube, download, insert.

### 3.5 Local Upload

| Item | Detail |
|---|---|
| **Formats** | MP3, MP4, M4A, WAV, FLAC, OGG |
| **Size Limit** | 50 MB (Telegram maximum) |
| **Metadata** | Extracted via [mutagen](https://github.com/quodlibet/mutagen) (title, artist, album, duration) |
| **Storage** | `SSOT/Music/Uploads/` |

---

## 4. Database Schema

All tables live in the default Supabase (PostgreSQL) schema.

```sql
-- Tracks imported into the user's library
CREATE TABLE IF NOT EXISTS library (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT        NOT NULL,
    artist      TEXT        NOT NULL DEFAULT 'Unknown',
    album       TEXT        NOT NULL DEFAULT '',
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    file_path   TEXT        NOT NULL,
    source      TEXT        NOT NULL CHECK (source IN (
                    'spotify', 'youtube', 'tidal', 'apple', 'upload'
                )),
    source_id   TEXT        NOT NULL DEFAULT '',
    added_by    TEXT        NOT NULL,          -- Telegram user ID
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_library_source     ON library (source);
CREATE INDEX idx_library_added_by   ON library (added_by);
CREATE INDEX idx_library_title_trgm ON library USING gin (title gin_trgm_ops);

-- Synced playlists from external services
CREATE TABLE IF NOT EXISTS playlists (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,
    source      TEXT        NOT NULL CHECK (source IN (
                    'spotify', 'youtube', 'tidal', 'apple'
                )),
    source_id   TEXT        NOT NULL,
    user_id     TEXT        NOT NULL,          -- Telegram user ID
    track_count INTEGER     NOT NULL DEFAULT 0,
    synced_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_playlists_user ON playlists (user_id);

-- Many-to-many relationship between playlists and library tracks
CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id UUID NOT NULL REFERENCES playlists (id) ON DELETE CASCADE,
    track_id    UUID NOT NULL REFERENCES library   (id) ON DELETE CASCADE,
    position    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (playlist_id, track_id)
);

CREATE INDEX idx_playlist_tracks_track ON playlist_tracks (track_id);
```

---

## 5. User Flows

### 5.1 Spotify Playlist Import (3-Tap Flow)

```
User                        Bot                         Spotify
 │                           │                            │
 │  /sync spotify            │                            │
 │ ─────────────────────────►│                            │
 │                           │  get_auth_url(user_id)     │
 │                           │ ──────────────────────────►│
 │  ◄── "Tap to authorize"  │  ◄── auth URL              │
 │                           │                            │
 │  [User opens URL]  ──────────────────────────────────►│
 │                           │  ◄── callback with code    │
 │                           │  handle_callback(code)     │
 │                           │ ──────────────────────────►│
 │  ◄── "Pick a playlist"   │  ◄── token                 │
 │                           │                            │
 │  [Taps playlist]          │                            │
 │ ─────────────────────────►│  get_tracks(playlist_id)   │
 │                           │ ──────────────────────────►│
 │                           │  import_track() × N        │
 │  ◄── "Imported 12 tracks" │                            │
```

### 5.2 YouTube Track Download

```
User                        Bot                     yt-dlp
 │                           │                        │
 │  /yt <URL or query>       │                        │
 │ ─────────────────────────►│                        │
 │                           │  search() or download() │
 │                           │ ──────────────────────►│
 │                           │  ◄── file path          │
 │                           │  _insert_library_track() │
 │  ◄── "Added to library"  │                        │
```

### 5.3 Tidal Favorites Sync

```
User                        Bot                     Tidal
 │                           │                        │
 │  /sync tidal              │                        │
 │ ─────────────────────────►│  authenticate()        │
 │  ◄── "Open this link"    │ ──────────────────────►│
 │  [Authorizes on Tidal]   │                        │
 │  /sync tidal confirm      │  authenticate(token)   │
 │ ─────────────────────────►│ ──────────────────────►│
 │                           │  get_favorites()       │
 │                           │  import_track() × N    │
 │  ◄── "Synced 8 favorites" │                        │
```

### 5.4 Local File Upload

```
User                        Bot
 │                           │
 │  [Sends audio file]       │
 │ ─────────────────────────►│
 │                           │  validate format & size
 │                           │  save to SSOT/Music/Uploads/
 │                           │  _extract_metadata()
 │                           │  _insert_library_track()
 │  ◄── "Saved: Song Title"  │
```

---

## 6. File Storage

### Directory Structure

```
SSOT/
└── Music/
    ├── Downloads/          ← Tracks downloaded via yt-dlp
    │   ├── a1b2c3d4e5f6.mp3
    │   └── ...
    └── Uploads/            ← Files uploaded via Telegram
        ├── 1a2b3c4d_MySong.mp3
        └── ...
```

### Naming Conventions

| Source | Pattern | Example |
|---|---|---|
| Downloaded | `{uuid_hex_12}.mp3` | `a1b2c3d4e5f6.mp3` |
| Uploaded | `{uuid_hex_8}_{sanitized_filename}` | `1a2b3c4d_My_Song.mp3` |

Filenames are sanitized: non-word characters (except `.` and `-`) are replaced with underscores.

### Cleanup Policy

- When `delete_track(track_id)` is called, both the Supabase row **and** the on-disk file are removed.
- Orphaned files (no matching library row) should be cleaned up by a periodic maintenance job (not yet implemented).
- Consider a weekly cron that compares `library.file_path` against files on disk.

---

## 7. Error Handling

| Error | Exception | Recovery |
|---|---|---|
| Missing env vars | `MusicSyncError` | Log and surface setup instructions to the admin |
| OAuth token expired | `AuthenticationError` | Re-trigger auth flow; spotipy auto-refreshes Spotify tokens |
| YouTube download fails | `DownloadError` | Retry once; notify user if persistent |
| Unsupported upload format | `UploadError` | Return supported-formats list to user |
| File exceeds 50 MB | `UploadError` | Inform user of the Telegram size limit |
| Track not found in library | `TrackNotFoundError` | Return 404-style message |
| Supabase insert failure | `MusicSyncError` | Log full error; notify admin |
| yt-dlp rate-limited | `DownloadError` | Back off and retry after delay |

All exceptions inherit from `MusicSyncError` so callers can catch the entire family with a single `except MusicSyncError`.

---

## 8. GitHub References

| Project | URL | Used For |
|---|---|---|
| spotipy | <https://github.com/spotipy-dev/spotipy> | Spotify Web API client |
| yt-dlp | <https://github.com/yt-dlp/yt-dlp> | YouTube audio download & extraction |
| python-tidal | <https://github.com/tamland/python-tidal> | Tidal API client |
| mutagen | <https://github.com/quodlibet/mutagen> | Audio metadata extraction |
| supabase-py | <https://github.com/supabase-community/supabase-py> | Supabase Python client |
| python-telegram-bot | <https://github.com/python-telegram-bot/python-telegram-bot> | Telegram bot framework |

---

## 9. Setup Guide

### 9.1 Spotify

1. Go to <https://developer.spotify.com/dashboard> and create an app.
2. Set the **Redirect URI** (e.g., `https://yourdomain.com/callback/spotify`).
3. Copy **Client ID** and **Client Secret** into environment variables:
   ```bash
   export SPOTIFY_CLIENT_ID="..."
   export SPOTIFY_CLIENT_SECRET="..."
   export SPOTIFY_REDIRECT_URI="https://yourdomain.com/callback/spotify"
   ```

### 9.2 Tidal

1. Register at <https://developer.tidal.com> for API access.
2. Create an application and note the **Client ID** and **Client Secret**.
3. Set environment variables:
   ```bash
   export TIDAL_CLIENT_ID="..."
   export TIDAL_CLIENT_SECRET="..."
   ```

### 9.3 Apple Music (future)

1. Enrol in the Apple Developer Program.
2. Create a MusicKit key at <https://developer.apple.com/account/resources/authkeys>.
3. Generate an ES256 JWT developer token using the private key.
4. *(Further steps will be documented once the provider is implemented.)*

### 9.4 YouTube / yt-dlp

No API keys are needed. Install yt-dlp and FFmpeg:

```bash
pip install yt-dlp
# Ensure FFmpeg is available on PATH
sudo apt-get install ffmpeg   # Debian/Ubuntu
brew install ffmpeg            # macOS
```

### 9.5 Supabase

1. Create a project at <https://supabase.com>.
2. Run the SQL from [Section 4](#4-database-schema) in the Supabase SQL editor.
3. Copy the **Project URL** and **anon/service key**:
   ```bash
   export SUPABASE_URL="https://xxxxx.supabase.co"
   export SUPABASE_KEY="eyJ..."
   ```

### 9.6 General

```bash
pip install spotipy yt-dlp tidalapi mutagen supabase
export MUSIC_STORAGE_PATH="SSOT/Music/Downloads"  # optional override
```

---

## 10. TODOs

- [ ] **Apple Music provider** — implement full MusicKit integration.
- [ ] **Token persistence** — store OAuth tokens in Supabase per user for session resumption.
- [ ] **Playlist sync scheduling** — allow users to auto-sync playlists on a schedule.
- [ ] **Duplicate detection** — check `source` + `source_id` before importing to avoid duplicates.
- [ ] **Orphan file cleanup** — periodic job to remove files with no library row.
- [ ] **Progress callbacks** — report import progress to the Telegram chat in real time.
- [ ] **Audio quality selector** — let users choose bitrate (128 / 192 / 320) per download.
- [ ] **Lyrics integration** — fetch and store lyrics alongside tracks.
- [ ] **Album art** — download and cache cover art for display in the bot.
- [ ] **Rate-limit handling** — implement exponential back-off for yt-dlp and Spotify API.
- [ ] **Unit tests** — add pytest suite with mocked API responses for each provider.
- [ ] **CI pipeline** — GitHub Actions workflow for linting, type-checking, and testing.
