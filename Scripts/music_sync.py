"""
Music Library Sync Module for RhythmClaw.

Handles music library synchronization with multiple streaming services
(Spotify, Apple Music, YouTube Music, Tidal) and local file uploads.
Imported tracks are stored in Supabase and on disk for playback via the
Telegram bot.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Optional

from supabase import Client as SupabaseClient
from supabase import create_client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "")

TIDAL_CLIENT_ID = os.getenv("TIDAL_CLIENT_ID", "")
TIDAL_CLIENT_SECRET = os.getenv("TIDAL_CLIENT_SECRET", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

MUSIC_STORAGE_PATH = Path(
    os.getenv("MUSIC_STORAGE_PATH", "SSOT/Music/Downloads")
)
MUSIC_UPLOAD_PATH = Path("SSOT/Music/Uploads")

SUPPORTED_UPLOAD_FORMATS = {"mp3", "mp4", "m4a", "wav", "flac", "ogg"}
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB (Telegram limit)
DEFAULT_AUDIO_BITRATE = "192"  # kbps

logger = logging.getLogger("rhythmclaw.music_sync")

# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class MusicSyncError(Exception):
    """Base exception for music-sync operations."""


class AuthenticationError(MusicSyncError):
    """Raised when authentication with a provider fails."""


class DownloadError(MusicSyncError):
    """Raised when a track download fails."""


class UploadError(MusicSyncError):
    """Raised when a local file upload fails."""


class TrackNotFoundError(MusicSyncError):
    """Raised when a requested track cannot be found."""


# ---------------------------------------------------------------------------
# Supabase helper
# ---------------------------------------------------------------------------

_supabase_client: Optional[SupabaseClient] = None


def get_supabase() -> SupabaseClient:
    """Return a shared Supabase client, creating one on first call."""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise MusicSyncError(
                "SUPABASE_URL and SUPABASE_KEY must be set in the environment"
            )
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class MusicProvider(ABC):
    """Abstract interface that every streaming-service provider implements."""

    @abstractmethod
    async def authenticate(self, **kwargs: Any) -> dict[str, Any]:
        """Authenticate with the provider.

        Returns:
            A dict with at least ``{"authenticated": True}`` on success.
        """

    @abstractmethod
    async def get_playlists(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch playlists for the authenticated user.

        Returns:
            List of ``{"id": ..., "name": ..., "track_count": ...}``.
        """

    @abstractmethod
    async def get_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        """List tracks in a playlist.

        Returns:
            List of ``{"id": ..., "name": ..., "artist": ...,
            "album": ..., "duration_ms": ...}``.
        """

    @abstractmethod
    async def import_track(
        self, track_id: str, user_id: str
    ) -> dict[str, Any]:
        """Import a single track into the local library.

        Returns:
            The newly-created library row as a dict.
        """


# ---------------------------------------------------------------------------
# Spotify Provider
# ---------------------------------------------------------------------------


class SpotifyProvider(MusicProvider):
    """Spotify integration via *spotipy* with OAuth PKCE / auth-code flow."""

    def __init__(self) -> None:
        try:
            import spotipy  # noqa: F401
            from spotipy.oauth2 import SpotifyOAuth  # noqa: F401
        except ImportError as exc:
            raise MusicSyncError(
                "spotipy is required for Spotify support – "
                "install it with `pip install spotipy`"
            ) from exc

        self._client_id = SPOTIFY_CLIENT_ID
        self._client_secret = SPOTIFY_CLIENT_SECRET
        self._redirect_uri = SPOTIFY_REDIRECT_URI
        self._sp: Any = None
        self._oauth: Any = None

    # -- Auth helpers -------------------------------------------------------

    def get_auth_url(self, user_id: str) -> str:
        """Return an OAuth URL for the given *user_id*.

        Args:
            user_id: Telegram user id (used as ``state`` parameter).

        Returns:
            The Spotify authorization URL.
        """
        from spotipy.oauth2 import SpotifyOAuth

        self._oauth = SpotifyOAuth(
            client_id=self._client_id,
            client_secret=self._client_secret,
            redirect_uri=self._redirect_uri,
            scope="playlist-read-private user-library-read",
            state=user_id,
        )
        return self._oauth.get_authorize_url()

    def handle_callback(self, code: str) -> dict[str, Any]:
        """Exchange an authorization *code* for an access token.

        Returns:
            Token info dict from Spotify.
        """
        import spotipy

        if self._oauth is None:
            raise AuthenticationError("OAuth flow was not started")
        token_info = self._oauth.get_access_token(code)
        self._sp = spotipy.Spotify(auth=token_info["access_token"])
        logger.info("Spotify authentication successful")
        return token_info

    # -- MusicProvider interface --------------------------------------------

    async def authenticate(self, **kwargs: Any) -> dict[str, Any]:
        """Authenticate using a pre-obtained *token* passed in kwargs."""
        import spotipy

        token: str | None = kwargs.get("token")
        if not token:
            raise AuthenticationError("A Spotify token is required")
        self._sp = spotipy.Spotify(auth=token)
        # Verify token with a lightweight API call
        try:
            me = await asyncio.to_thread(self._sp.current_user)
        except Exception as exc:
            raise AuthenticationError(
                f"Spotify token validation failed: {exc}"
            ) from exc
        logger.info("Authenticated as Spotify user %s", me.get("id"))
        return {"authenticated": True, "user": me}

    async def get_playlists(self, user_id: str) -> list[dict[str, Any]]:
        """Return the user's Spotify playlists."""
        if self._sp is None:
            raise AuthenticationError("Not authenticated with Spotify")
        results = await asyncio.to_thread(self._sp.current_user_playlists)
        playlists: list[dict[str, Any]] = []
        for item in results.get("items", []):
            playlists.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "track_count": item["tracks"]["total"],
                }
            )
        return playlists

    async def get_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        """Return tracks in a Spotify playlist."""
        if self._sp is None:
            raise AuthenticationError("Not authenticated with Spotify")
        results = await asyncio.to_thread(
            self._sp.playlist_tracks, playlist_id
        )
        tracks: list[dict[str, Any]] = []
        for item in results.get("items", []):
            t = item.get("track")
            if t is None:
                continue
            tracks.append(
                {
                    "id": t["id"],
                    "name": t["name"],
                    "artist": ", ".join(a["name"] for a in t["artists"]),
                    "album": t["album"]["name"],
                    "duration_ms": t["duration_ms"],
                }
            )
        return tracks

    async def import_track(
        self, track_id: str, user_id: str
    ) -> dict[str, Any]:
        """Import a Spotify track by downloading a matched YouTube audio."""
        if self._sp is None:
            raise AuthenticationError("Not authenticated with Spotify")
        track = await asyncio.to_thread(self._sp.track, track_id)
        artist = ", ".join(a["name"] for a in track["artists"])
        query = f"{track['name']} {artist}"
        logger.info("Searching YouTube for: %s", query)

        yt = YouTubeMusicProvider()
        results = await yt.search(query)
        if not results:
            raise DownloadError(
                f"No YouTube results for Spotify track {track_id}"
            )
        file_path = await yt.download(results[0]["url"])

        row = _insert_library_track(
            title=track["name"],
            artist=artist,
            album=track["album"]["name"],
            duration_seconds=track["duration_ms"] // 1000,
            file_path=str(file_path),
            source="spotify",
            source_id=track_id,
            added_by=user_id,
        )
        logger.info("Imported Spotify track %s → library id %s", track_id, row["id"])
        return row


# ---------------------------------------------------------------------------
# Apple Music Provider (placeholder)
# ---------------------------------------------------------------------------


class AppleMusicProvider(MusicProvider):
    """Placeholder for Apple Music integration via MusicKit.

    Apple Music requires a *developer token* (JWT signed with a MusicKit
    private key) and a *user token* obtained through the Apple Music web
    authentication flow.

    Relevant API endpoints (v1):
        - ``GET /v1/me/library/playlists``
        - ``GET /v1/me/library/playlists/{id}/tracks``
        - ``GET /v1/catalog/{storefront}/songs/{id}``
        - ``GET /v1/me/library/songs``

    See: https://developer.apple.com/documentation/applemusicapi
    """

    # TODO: Implement developer-token generation (ES256 JWT).
    # TODO: Implement user-token acquisition via web auth flow.
    # TODO: Implement catalog search for matched downloads.

    async def authenticate(self, **kwargs: Any) -> dict[str, Any]:
        """Authenticate with Apple Music.

        Requires ``developer_token`` and ``user_token`` in *kwargs*.

        Returns:
            Authentication result dict.
        """
        # TODO: Validate tokens against Apple Music API.
        raise NotImplementedError("Apple Music support is not yet available")

    async def get_playlists(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch the user's Apple Music library playlists.

        Endpoint: ``GET /v1/me/library/playlists``

        Returns:
            List of playlist dicts.
        """
        # TODO: Call Apple Music API with user token.
        raise NotImplementedError("Apple Music support is not yet available")

    async def get_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        """Fetch tracks in an Apple Music playlist.

        Endpoint: ``GET /v1/me/library/playlists/{id}/tracks``

        Returns:
            List of track dicts.
        """
        # TODO: Call Apple Music API with user token.
        raise NotImplementedError("Apple Music support is not yet available")

    async def import_track(
        self, track_id: str, user_id: str
    ) -> dict[str, Any]:
        """Import an Apple Music track via matched YouTube download.

        Endpoint: ``GET /v1/catalog/{storefront}/songs/{id}``

        Returns:
            The newly-created library row.
        """
        # TODO: Fetch track metadata, search YouTube, download, insert.
        raise NotImplementedError("Apple Music support is not yet available")


# ---------------------------------------------------------------------------
# YouTube Music Provider
# ---------------------------------------------------------------------------


class YouTubeMusicProvider(MusicProvider):
    """YouTube Music / YouTube audio provider using *yt-dlp*."""

    def __init__(self, bitrate: str = DEFAULT_AUDIO_BITRATE) -> None:
        self._bitrate = bitrate

    async def authenticate(self, **kwargs: Any) -> dict[str, Any]:
        """No authentication required for public YouTube content."""
        return {"authenticated": True}

    async def get_playlists(self, user_id: str) -> list[dict[str, Any]]:
        """Not applicable for YouTube – returns an empty list."""
        return []

    async def get_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        """List videos in a YouTube playlist.

        Uses yt-dlp ``--flat-playlist`` to avoid downloading.
        """
        import yt_dlp

        entries: list[dict[str, Any]] = []
        opts: dict[str, Any] = {
            "quiet": True,
            "extract_flat": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(
                ydl.extract_info, playlist_id, download=False
            )
        for entry in (info or {}).get("entries", []):
            entries.append(
                {
                    "id": entry.get("id", ""),
                    "name": entry.get("title", "Unknown"),
                    "artist": entry.get("uploader", "Unknown"),
                    "album": "",
                    "duration_ms": (entry.get("duration") or 0) * 1000,
                }
            )
        return entries

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search YouTube for tracks matching *query*.

        Args:
            query: Free-text search string.
            limit: Maximum number of results.

        Returns:
            List of ``{"id": ..., "title": ..., "url": ...,
            "duration": ..., "uploader": ...}``.
        """
        import yt_dlp

        opts: dict[str, Any] = {
            "quiet": True,
            "extract_flat": True,
            "skip_download": True,
            "default_search": f"ytsearch{limit}",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(
                ydl.extract_info, query, download=False
            )
        results: list[dict[str, Any]] = []
        for entry in (info or {}).get("entries", []):
            results.append(
                {
                    "id": entry.get("id", ""),
                    "title": entry.get("title", "Unknown"),
                    "url": entry.get("url", ""),
                    "duration": entry.get("duration", 0),
                    "uploader": entry.get("uploader", "Unknown"),
                }
            )
        return results

    async def download(self, url: str) -> Path:
        """Download audio from *url* as MP3 into ``MUSIC_STORAGE_PATH``.

        Args:
            url: YouTube video URL or ID.

        Returns:
            Path to the downloaded file.

        Raises:
            DownloadError: If the download or conversion fails.
        """
        import yt_dlp

        MUSIC_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        file_id = uuid.uuid4().hex[:12]
        output_template = str(MUSIC_STORAGE_PATH / f"{file_id}.%(ext)s")

        opts: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": self._bitrate,
                }
            ],
            "quiet": True,
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                await asyncio.to_thread(ydl.download, [url])
        except Exception as exc:
            raise DownloadError(f"yt-dlp download failed: {exc}") from exc

        downloaded = MUSIC_STORAGE_PATH / f"{file_id}.mp3"
        if not downloaded.exists():
            raise DownloadError(
                f"Expected file {downloaded} not found after download"
            )
        logger.info("Downloaded %s → %s", url, downloaded)
        return downloaded

    async def import_track(
        self, track_id: str, user_id: str
    ) -> dict[str, Any]:
        """Download a YouTube track and add it to the library.

        Args:
            track_id: YouTube video URL or video ID.
            user_id: Telegram user id of the requester.

        Returns:
            The newly-created library row.
        """
        return await self.import_from_url(track_id, user_id)

    async def import_from_url(
        self, url: str, user_id: str
    ) -> dict[str, Any]:
        """Download from *url*, extract metadata, and insert into Supabase.

        Args:
            url: YouTube video URL.
            user_id: Telegram user id.

        Returns:
            The newly-created library row.
        """
        import yt_dlp

        # Fetch metadata first
        opts: dict[str, Any] = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(
                ydl.extract_info, url, download=False
            )

        title = (info or {}).get("title", "Unknown")
        uploader = (info or {}).get("uploader", "Unknown")
        duration = (info or {}).get("duration", 0)
        video_id = (info or {}).get("id", "")

        file_path = await self.download(url)

        row = _insert_library_track(
            title=title,
            artist=uploader,
            album="",
            duration_seconds=duration,
            file_path=str(file_path),
            source="youtube",
            source_id=video_id,
            added_by=user_id,
        )
        logger.info("Imported YouTube track %s → library id %s", url, row["id"])
        return row


# ---------------------------------------------------------------------------
# Tidal Provider
# ---------------------------------------------------------------------------


class TidalProvider(MusicProvider):
    """Tidal integration via the *tidalapi* library."""

    def __init__(self) -> None:
        try:
            import tidalapi  # noqa: F401
        except ImportError as exc:
            raise MusicSyncError(
                "tidalapi is required for Tidal support – "
                "install it with `pip install tidalapi`"
            ) from exc
        self._session: Any = None

    async def authenticate(self, **kwargs: Any) -> dict[str, Any]:
        """Start or resume a Tidal OAuth session.

        Pass ``oauth_token`` to resume, or call without arguments to
        initiate a device-code flow.

        Returns:
            ``{"authenticated": True, "user": ...}`` on success.
        """
        import tidalapi

        self._session = tidalapi.Session()
        token: str | None = kwargs.get("oauth_token")
        if token:
            self._session.access_token = token
            try:
                await asyncio.to_thread(self._session.check_login)
            except Exception as exc:
                raise AuthenticationError(
                    f"Tidal token validation failed: {exc}"
                ) from exc
        else:
            login, future = self._session.login_oauth()
            logger.info("Tidal device-code login URL: %s", login.verification_uri_complete)
            return {
                "authenticated": False,
                "verification_url": login.verification_uri_complete,
                "message": "Open the URL to authorize, then call authenticate again with oauth_token.",
            }
        logger.info("Tidal authentication successful")
        return {"authenticated": True, "user": str(self._session.user)}

    async def get_playlists(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch playlists from the authenticated Tidal account."""
        if self._session is None:
            raise AuthenticationError("Not authenticated with Tidal")
        playlists_raw = await asyncio.to_thread(
            self._session.user.playlists
        )
        playlists: list[dict[str, Any]] = []
        for p in playlists_raw:
            playlists.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "track_count": p.num_tracks,
                }
            )
        return playlists

    async def get_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        """Fetch tracks in a Tidal playlist."""
        if self._session is None:
            raise AuthenticationError("Not authenticated with Tidal")
        import tidalapi

        playlist = await asyncio.to_thread(
            tidalapi.Playlist, self._session, playlist_id
        )
        tracks_raw = await asyncio.to_thread(playlist.tracks)
        tracks: list[dict[str, Any]] = []
        for t in tracks_raw:
            tracks.append(
                {
                    "id": str(t.id),
                    "name": t.name,
                    "artist": t.artist.name if t.artist else "Unknown",
                    "album": t.album.name if t.album else "",
                    "duration_ms": (t.duration or 0) * 1000,
                }
            )
        return tracks

    async def get_favorites(self) -> list[dict[str, Any]]:
        """Fetch the user's favourite tracks from Tidal.

        Returns:
            List of track dicts identical in shape to ``get_tracks``.
        """
        if self._session is None:
            raise AuthenticationError("Not authenticated with Tidal")
        favorites = await asyncio.to_thread(
            self._session.user.favorites.tracks
        )
        tracks: list[dict[str, Any]] = []
        for t in favorites:
            tracks.append(
                {
                    "id": str(t.id),
                    "name": t.name,
                    "artist": t.artist.name if t.artist else "Unknown",
                    "album": t.album.name if t.album else "",
                    "duration_ms": (t.duration or 0) * 1000,
                }
            )
        return tracks

    async def import_track(
        self, track_id: str, user_id: str
    ) -> dict[str, Any]:
        """Import a Tidal track via matched YouTube download.

        Fetches metadata from Tidal, searches YouTube for a match,
        downloads the audio, and inserts a library row.
        """
        if self._session is None:
            raise AuthenticationError("Not authenticated with Tidal")
        import tidalapi

        track = await asyncio.to_thread(
            tidalapi.Track, self._session, track_id
        )
        artist = track.artist.name if track.artist else "Unknown"
        query = f"{track.name} {artist}"
        logger.info("Searching YouTube for Tidal track: %s", query)

        yt = YouTubeMusicProvider()
        results = await yt.search(query)
        if not results:
            raise DownloadError(
                f"No YouTube results for Tidal track {track_id}"
            )
        file_path = await yt.download(results[0]["url"])

        row = _insert_library_track(
            title=track.name,
            artist=artist,
            album=track.album.name if track.album else "",
            duration_seconds=track.duration or 0,
            file_path=str(file_path),
            source="tidal",
            source_id=track_id,
            added_by=user_id,
        )
        logger.info("Imported Tidal track %s → library id %s", track_id, row["id"])
        return row


# ---------------------------------------------------------------------------
# Local Upload Handler
# ---------------------------------------------------------------------------


class LocalUploadHandler:
    """Handles audio files uploaded directly via the Telegram bot."""

    @staticmethod
    async def handle_telegram_upload(
        file_bytes: bytes | BinaryIO,
        filename: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Save an uploaded file and register it in the library.

        Args:
            file_bytes: Raw bytes or file-like object of the uploaded file.
            filename: Original filename including extension.
            user_id: Telegram user id of the uploader.

        Returns:
            The newly-created library row.

        Raises:
            UploadError: On validation failure or I/O error.
        """
        ext = Path(filename).suffix.lstrip(".").lower()
        if ext not in SUPPORTED_UPLOAD_FORMATS:
            raise UploadError(
                f"Unsupported format '.{ext}'. "
                f"Allowed: {', '.join(sorted(SUPPORTED_UPLOAD_FORMATS))}"
            )

        data = (
            file_bytes
            if isinstance(file_bytes, bytes)
            else file_bytes.read()
        )
        if len(data) > MAX_UPLOAD_SIZE_BYTES:
            raise UploadError(
                f"File exceeds the {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB limit"
            )

        MUSIC_UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^\w.\-]", "_", filename)
        dest = MUSIC_UPLOAD_PATH / f"{uuid.uuid4().hex[:8]}_{safe_name}"
        await asyncio.to_thread(_write_bytes, dest, data)
        logger.info("Saved upload to %s (%d bytes)", dest, len(data))

        metadata = await asyncio.to_thread(_extract_metadata, dest)

        row = _insert_library_track(
            title=metadata.get("title", Path(filename).stem),
            artist=metadata.get("artist", "Unknown"),
            album=metadata.get("album", ""),
            duration_seconds=metadata.get("duration", 0),
            file_path=str(dest),
            source="upload",
            source_id="",
            added_by=user_id,
        )
        logger.info("Registered upload as library id %s", row["id"])
        return row


def _write_bytes(path: Path, data: bytes) -> None:
    """Synchronous helper to write bytes to *path*."""
    path.write_bytes(data)


def _extract_metadata(path: Path) -> dict[str, Any]:
    """Extract basic audio metadata from *path* using mutagen.

    Falls back to filename-based guesses if mutagen is unavailable.

    Returns:
        ``{"title": ..., "artist": ..., "album": ..., "duration": ...}``
    """
    meta: dict[str, Any] = {
        "title": path.stem,
        "artist": "Unknown",
        "album": "",
        "duration": 0,
    }
    try:
        import mutagen

        audio = mutagen.File(str(path), easy=True)
        if audio is None:
            return meta
        meta["duration"] = int(audio.info.length) if audio.info else 0
        meta["title"] = _first(audio.get("title"), path.stem)
        meta["artist"] = _first(audio.get("artist"), "Unknown")
        meta["album"] = _first(audio.get("album"), "")
    except ImportError:
        logger.warning(
            "mutagen is not installed – metadata extraction skipped"
        )
    except Exception as exc:
        logger.warning("Metadata extraction failed for %s: %s", path, exc)
    return meta


def _first(value: Any, default: str) -> str:
    """Return the first element of *value* if it is a list, else *default*."""
    if isinstance(value, list) and value:
        return str(value[0])
    if isinstance(value, str) and value:
        return value
    return default


# ---------------------------------------------------------------------------
# Library CRUD helpers
# ---------------------------------------------------------------------------


def _insert_library_track(
    *,
    title: str,
    artist: str,
    album: str,
    duration_seconds: int,
    file_path: str,
    source: str,
    source_id: str,
    added_by: str,
) -> dict[str, Any]:
    """Insert a track into the Supabase ``library`` table.

    Returns:
        The inserted row as a dict (includes ``id`` and ``created_at``).
    """
    sb = get_supabase()
    payload = {
        "title": title,
        "artist": artist,
        "album": album,
        "duration_seconds": duration_seconds,
        "file_path": file_path,
        "source": source,
        "source_id": source_id,
        "added_by": added_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = sb.table("library").insert(payload).execute()
    if not result.data:
        raise MusicSyncError("Supabase insert returned no data")
    return result.data[0]


async def search_library(
    query: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Search the library by title or artist.

    Args:
        query: Free-text search string.
        limit: Maximum results to return.

    Returns:
        Matching library rows.
    """
    sb = get_supabase()
    result = (
        sb.table("library")
        .select("*")
        .or_(f"title.ilike.%{query}%,artist.ilike.%{query}%")
        .limit(limit)
        .execute()
    )
    return result.data or []


async def get_library_tracks(
    page: int = 1, per_page: int = 20
) -> list[dict[str, Any]]:
    """Return a paginated list of library tracks.

    Args:
        page: 1-based page number.
        per_page: Number of tracks per page.

    Returns:
        List of library rows for the requested page.
    """
    sb = get_supabase()
    start = (page - 1) * per_page
    end = start + per_page - 1
    result = (
        sb.table("library")
        .select("*")
        .order("created_at", desc=True)
        .range(start, end)
        .execute()
    )
    return result.data or []


async def delete_track(track_id: str) -> bool:
    """Delete a track from the library and remove its file from disk.

    Args:
        track_id: The ``id`` column value in the library table.

    Returns:
        ``True`` if the track was deleted.

    Raises:
        TrackNotFoundError: If the track does not exist.
    """
    sb = get_supabase()
    existing = (
        sb.table("library").select("file_path").eq("id", track_id).execute()
    )
    if not existing.data:
        raise TrackNotFoundError(f"Track {track_id} not found")

    file_path = Path(existing.data[0]["file_path"])
    if file_path.exists():
        await asyncio.to_thread(file_path.unlink)
        logger.info("Deleted file %s", file_path)

    sb.table("library").delete().eq("id", track_id).execute()
    logger.info("Deleted library track %s", track_id)
    return True


async def get_track_file_path(track_id: str) -> Path:
    """Resolve the on-disk file path for a library track.

    Args:
        track_id: The ``id`` column value in the library table.

    Returns:
        Absolute ``Path`` to the audio file.

    Raises:
        TrackNotFoundError: If the track does not exist or the file is missing.
    """
    sb = get_supabase()
    result = (
        sb.table("library").select("file_path").eq("id", track_id).execute()
    )
    if not result.data:
        raise TrackNotFoundError(f"Track {track_id} not found in library")
    path = Path(result.data[0]["file_path"])
    if not path.exists():
        raise TrackNotFoundError(
            f"File for track {track_id} is missing at {path}"
        )
    return path
