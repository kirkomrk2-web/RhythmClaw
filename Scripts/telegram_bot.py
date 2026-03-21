"""
RhythmClaw Telegram Bot — DJ Control Panel

Controls a Pioneer DDJ-FLX4 DJ controller via a FastAPI MIDI server.
Uses python-telegram-bot v20+ (async) with inline keyboards and
in-place menu transitions.

Environment variables:
    TELEGRAM_BOT_TOKEN  – Telegram Bot API token
    MIDI_SERVER_URL     – FastAPI MIDI server base URL
    SUPABASE_URL        – Supabase project URL
    SUPABASE_KEY        – Supabase anon/service key
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from supabase import create_client, Client as SupabaseClient
from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    User,
    Chat,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("rhythmclaw_bot")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
MIDI_SERVER_URL: str = os.environ.get("MIDI_SERVER_URL", "http://localhost:8000")
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]

TRANSLATIONS_PATH = Path(__file__).resolve().parent.parent / "Config" / "translations.json"


# ---------------------------------------------------------------------------
# Update extraction helpers
# ---------------------------------------------------------------------------

def _get_user(update: Update) -> User:
    """Extract the User from an update, raising if absent."""
    user = update.effective_user
    if user is None:
        raise ValueError("Update has no effective_user")
    return user


def _get_chat(update: Update) -> Chat:
    """Extract the Chat from an update, raising if absent."""
    chat = update.effective_chat
    if chat is None:
        raise ValueError("Update has no effective_chat")
    return chat

# ---------------------------------------------------------------------------
# Global state (per-user, in-memory)
# ---------------------------------------------------------------------------
# Navigation stack per user for Back button support
nav_stack: dict[int, list[str]] = {}
# Last bot message id per user (for auto-delete)
last_message_id: dict[int, int] = {}
# Now-playing message id per user (never auto-deleted)
now_playing_message_id: dict[int, int] = {}
# Currently selected deck per user
selected_deck: dict[int, int] = {}
# Language preference cache (authoritative source is Supabase)
user_language: dict[int, str] = {}

# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------------
# HTTP client for MIDI server
# ---------------------------------------------------------------------------
http_client = httpx.AsyncClient(base_url=MIDI_SERVER_URL, timeout=10.0)

# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------
_translations: dict[str, dict[str, str]] = {}


def _load_translations() -> None:
    """Load translations from Config/translations.json."""
    global _translations
    with open(TRANSLATIONS_PATH, encoding="utf-8") as fh:
        _translations = json.load(fh)
    logger.info("Loaded translations for languages: %s", list(_translations.keys()))


def t(key: str, lang: str = "en") -> str:
    """Return the translated string for *key* in the given *lang*.

    Falls back to English, then to the raw key if not found.
    """
    text = _translations.get(lang, {}).get(key)
    if text is None:
        text = _translations.get("en", {}).get(key, key)
    return text


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

async def get_user_lang(user_id: int) -> str:
    """Fetch language preference from cache or Supabase."""
    if user_id in user_language:
        return user_language[user_id]
    try:
        resp = (
            supabase.table("user_preferences")
            .select("language")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if resp.data:
            lang = resp.data[0].get("language", "en")
        else:
            lang = "en"
            supabase.table("user_preferences").insert(
                {"user_id": str(user_id), "language": lang}
            ).execute()
    except Exception:
        logger.exception("Supabase: failed to fetch language for user %s", user_id)
        lang = "en"
    user_language[user_id] = lang
    return lang


async def set_user_lang(user_id: int, lang: str) -> None:
    """Persist language preference to Supabase and cache."""
    user_language[user_id] = lang
    try:
        supabase.table("user_preferences").upsert(
            {"user_id": str(user_id), "language": lang}
        ).execute()
    except Exception:
        logger.exception("Supabase: failed to set language for user %s", user_id)


async def add_favorite(user_id: int, track_id: str, track_name: str) -> None:
    """Save a track to the user's favourites in Supabase."""
    try:
        supabase.table("favorites").upsert(
            {
                "user_id": str(user_id),
                "track_id": track_id,
                "track_name": track_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="user_id,track_id",
        ).execute()
    except Exception:
        logger.exception("Supabase: failed to add favorite for user %s", user_id)


async def get_favorites(user_id: int) -> list[dict[str, Any]]:
    """Return the user's favourited tracks from Supabase."""
    try:
        resp = (
            supabase.table("favorites")
            .select("track_id, track_name, timestamp")
            .eq("user_id", str(user_id))
            .order("timestamp", desc=True)
            .limit(20)
            .execute()
        )
        return resp.data or []
    except Exception:
        logger.exception("Supabase: failed to fetch favorites for user %s", user_id)
        return []


async def get_user_setting(user_id: int, key: str, default: bool = True) -> bool:
    """Read a boolean setting from Supabase user_preferences."""
    try:
        resp = (
            supabase.table("user_preferences")
            .select(key)
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if resp.data and key in resp.data[0]:
            return bool(resp.data[0][key])
    except Exception:
        logger.exception("Supabase: failed to read setting %s for user %s", key, user_id)
    return default


async def toggle_user_setting(user_id: int, key: str) -> bool:
    """Toggle a boolean setting and return the new value."""
    current = await get_user_setting(user_id, key)
    new_val = not current
    try:
        supabase.table("user_preferences").upsert(
            {"user_id": str(user_id), key: new_val}
        ).execute()
    except Exception:
        logger.exception("Supabase: failed to toggle setting %s for user %s", key, user_id)
    return new_val


# ---------------------------------------------------------------------------
# MIDI server helpers
# ---------------------------------------------------------------------------

async def midi_command(endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a command to the MIDI server and return the JSON response."""
    try:
        if payload:
            resp = await http_client.post(endpoint, json=payload)
        else:
            resp = await http_client.post(endpoint)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("MIDI server HTTP error: %s %s", exc.response.status_code, exc.response.text)
        raise
    except httpx.RequestError as exc:
        logger.error("MIDI server request error: %s", exc)
        raise


async def midi_get(endpoint: str) -> dict[str, Any]:
    """GET request to the MIDI server."""
    try:
        resp = await http_client.get(endpoint)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logger.exception("MIDI server GET error on %s", endpoint)
        raise


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

async def delete_last_message(user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Delete the previously stored bot message for a user (not Now Playing)."""
    msg_id = last_message_id.pop(user_id, None)
    if msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            logger.debug("Could not delete message %s for user %s", msg_id, user_id)


async def send_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: InlineKeyboardMarkup,
    *,
    push_state: str | None = None,
) -> None:
    """Send or edit a menu message with auto-delete of the previous one.

    If the interaction comes from a callback query, we edit the existing
    message.  Otherwise we delete the old message and send a new one.
    """
    user_id = _get_user(update).id
    chat_id = _get_chat(update).id

    if push_state is not None:
        nav_stack.setdefault(user_id, []).append(push_state)

    query = update.callback_query
    if query:
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
            last_message_id[user_id] = query.message.message_id  # type: ignore[union-attr]
            return
        except Exception:
            logger.debug("edit_message_text failed; falling back to new message")

    await delete_last_message(user_id, context, chat_id)
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )
    last_message_id[user_id] = msg.message_id


async def answer_toast(query: CallbackQuery, text: str) -> None:
    """Show a short toast notification via answerCallbackQuery."""
    try:
        await query.answer(text=text, show_alert=False)
    except Exception:
        logger.debug("answerCallbackQuery failed")


async def safe_error(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Send a generic error message to the user."""
    chat_id = _get_chat(update).id
    await context.bot.send_message(chat_id=chat_id, text=t("error_generic", lang))


# ---------------------------------------------------------------------------
# Keyboard builders
# ---------------------------------------------------------------------------

def _btn(label: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=data)


def build_main_menu(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Return (text, keyboard) for the main menu."""
    text = t("main_menu_title", lang)
    keyboard = InlineKeyboardMarkup(
        [
            [_btn(t("play", lang), "cmd:play"), _btn(t("pause", lang), "cmd:pause"), _btn(t("skip", lang), "cmd:skip")],
            [_btn(t("decks", lang), "menu:decks"), _btn(t("queue", lang), "menu:queue"), _btn(t("fx", lang), "menu:fx")],
            [_btn(t("library", lang), "menu:library"), _btn(t("favs", lang), "menu:favs"), _btn(t("settings", lang), "menu:settings")],
            [_btn(t("toggle_lang", lang), "action:toggle_lang")],
        ]
    )
    return text, keyboard


def build_deck_select_menu(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Deck selection screen."""
    text = t("deck_select_title", lang)
    keyboard = InlineKeyboardMarkup(
        [
            [_btn(t("deck_1", lang), "deck:select:1"), _btn(t("deck_2", lang), "deck:select:2")],
            [_btn(t("back", lang), "nav:back")],
        ]
    )
    return text, keyboard


def build_deck_control_menu(deck: int, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Controls for a specific deck."""
    d = str(deck)
    text = t("deck_control_title", lang).format(deck=deck)
    keyboard = InlineKeyboardMarkup(
        [
            [_btn(t("play", lang), f"deck:{d}:play"), _btn(t("pause", lang), f"deck:{d}:pause"), _btn(t("sync", lang), f"deck:{d}:sync")],
            [_btn(t("cue", lang), f"deck:{d}:cue"), _btn(t("skip", lang), f"deck:{d}:skip")],
            [_btn(f"HC {i}", f"deck:{d}:hotcue:{i}") for i in range(1, 5)],
            [_btn(f"HC {i}", f"deck:{d}:hotcue:{i}") for i in range(5, 9)],
            [
                _btn(t("loop_half", lang), f"deck:{d}:loop:0.5"),
                _btn(t("loop_1", lang), f"deck:{d}:loop:1"),
                _btn(t("loop_2", lang), f"deck:{d}:loop:2"),
                _btn(t("loop_4", lang), f"deck:{d}:loop:4"),
            ],
            [
                _btn(t("jump_back_2", lang), f"deck:{d}:jump:-2"),
                _btn(t("jump_back_4", lang), f"deck:{d}:jump:-4"),
                _btn(t("jump_fwd_8", lang), f"deck:{d}:jump:8"),
                _btn(t("jump_fwd_16", lang), f"deck:{d}:jump:16"),
            ],
            [_btn(t("back", lang), "nav:back")],
        ]
    )
    return text, keyboard


def build_queue_menu(queue_items: list[str], lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Queue display."""
    if queue_items:
        listing = "\n".join(f"{i+1}. {name}" for i, name in enumerate(queue_items[:8]))
        text = f"{t('queue_title', lang)}\n\n{listing}"
    else:
        text = f"{t('queue_title', lang)}\n\n{t('queue_empty', lang)}"
    keyboard = InlineKeyboardMarkup(
        [
            [_btn(t("queue_add", lang), "queue:add"), _btn(t("queue_clear", lang), "queue:clear")],
            [_btn(t("back", lang), "nav:back")],
        ]
    )
    return text, keyboard


def build_fx_menu(fx1_on: bool, fx2_on: bool, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """FX control menu."""
    text = t("fx_title", lang)
    fx1_label = t("fx1_on", lang) if fx1_on else t("fx1_off", lang)
    fx2_label = t("fx2_on", lang) if fx2_on else t("fx2_off", lang)
    keyboard = InlineKeyboardMarkup(
        [
            [_btn(fx1_label, "fx:toggle:1"), _btn(fx2_label, "fx:toggle:2")],
            [_btn(t("back", lang), "nav:back")],
        ]
    )
    return text, keyboard


def build_library_menu(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Library / source selection menu."""
    text = t("library_title", lang)
    keyboard = InlineKeyboardMarkup(
        [
            [_btn(t("lib_spotify", lang), "lib:spotify"), _btn(t("lib_apple", lang), "lib:apple")],
            [_btn(t("lib_youtube", lang), "lib:youtube"), _btn(t("lib_tidal", lang), "lib:tidal")],
            [_btn(t("lib_upload", lang), "lib:upload")],
            [_btn(t("back", lang), "nav:back")],
        ]
    )
    return text, keyboard


def build_favs_menu(favs: list[dict[str, Any]], lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Favourites list with load-to-deck buttons."""
    if favs:
        lines = [f"{i+1}. {f['track_name']}" for i, f in enumerate(favs[:10])]
        text = f"{t('favs_title', lang)}\n\n" + "\n".join(lines)
        rows: list[list[InlineKeyboardButton]] = []
        for i, f in enumerate(favs[:10]):
            tid = f["track_id"]
            rows.append(
                [
                    _btn(f"{i+1}. {t('load_d1', lang)}", f"fav:load:1:{tid}"),
                    _btn(f"{i+1}. {t('load_d2', lang)}", f"fav:load:2:{tid}"),
                ]
            )
        rows.append([_btn(t("back", lang), "nav:back")])
    else:
        text = f"{t('favs_title', lang)}\n\n{t('favs_empty', lang)}"
        rows = [[_btn(t("back", lang), "nav:back")]]
    return text, InlineKeyboardMarkup(rows)


def build_settings_menu(lang: str, bpm_on: bool, notif_on: bool) -> tuple[str, InlineKeyboardMarkup]:
    """Settings menu."""
    text = t("settings_title", lang)
    lang_label = t("settings_lang", lang).format(lang=lang.upper())
    bpm_label = t("settings_bpm_on", lang) if bpm_on else t("settings_bpm_off", lang)
    notif_label = t("settings_notif_on", lang) if notif_on else t("settings_notif_off", lang)
    keyboard = InlineKeyboardMarkup(
        [
            [_btn(lang_label, "action:toggle_lang")],
            [_btn(bpm_label, "settings:toggle:bpm_display")],
            [_btn(notif_label, "settings:toggle:notifications")],
            [_btn(t("back", lang), "nav:back")],
        ]
    )
    return text, keyboard


def build_now_playing(track_name: str, deck: int, bpm: int | float, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Now-playing card."""
    text = t("now_playing_template", lang).format(track=track_name, deck=deck, bpm=bpm)
    keyboard = InlineKeyboardMarkup(
        [
            [
                _btn(t("like", lang), "np:like"),
                _btn(t("skip", lang), "np:skip"),
                _btn(t("pause", lang), "np:pause"),
            ],
        ]
    )
    return text, keyboard


def build_history_menu(tracks: list[str], lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """History view — last 5 played tracks."""
    if tracks:
        listing = "\n".join(f"{i+1}. {name}" for i, name in enumerate(tracks[:5]))
        text = f"{t('history_title', lang)}\n\n{listing}"
    else:
        text = f"{t('history_title', lang)}\n\n{t('history_empty', lang)}"
    keyboard = InlineKeyboardMarkup(
        [[_btn(t("back", lang), "nav:back")]],
    )
    return text, keyboard


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — send the main menu."""
    user_id = _get_user(update).id
    lang = await get_user_lang(user_id)
    nav_stack[user_id] = ["main"]
    text, kb = build_main_menu(lang)
    await send_menu(update, context, text, kb)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — show help text."""
    user_id = _get_user(update).id
    lang = await get_user_lang(user_id)
    chat_id = _get_chat(update).id
    await delete_last_message(user_id, context, chat_id)
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=t("help_text", lang),
        parse_mode=ParseMode.HTML,
    )
    last_message_id[user_id] = msg.message_id


async def cmd_now_playing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /nowplaying — show (or update) the Now Playing card."""
    user_id = _get_user(update).id
    chat_id = _get_chat(update).id
    lang = await get_user_lang(user_id)
    try:
        data = await midi_get("/now_playing")
        track_name = data.get("track_name", t("unknown_track", lang))
        deck = data.get("deck", 1)
        bpm = data.get("bpm", 0)
    except Exception:
        await safe_error(update, context, lang)
        return

    text, kb = build_now_playing(track_name, deck, bpm, lang)

    existing = now_playing_message_id.get(user_id)
    if existing:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=existing,
                text=text,
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
            return
        except Exception:
            logger.debug("Could not edit existing Now Playing message")

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )
    now_playing_message_id[user_id] = msg.message_id


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /history — show last 5 played tracks."""
    user_id = _get_user(update).id
    lang = await get_user_lang(user_id)
    try:
        data = await midi_get("/history")
        tracks: list[str] = data.get("tracks", [])
    except Exception:
        tracks = []

    nav_stack.setdefault(user_id, ["main"]).append("history")
    text, kb = build_history_menu(tracks, lang)
    await send_menu(update, context, text, kb)


# ---------------------------------------------------------------------------
# Callback query router
# ---------------------------------------------------------------------------

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all inline-keyboard callbacks."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    user_id = _get_user(update).id
    lang = await get_user_lang(user_id)
    data = query.data

    try:
        if data == "nav:back":
            await _handle_back(update, context, user_id, lang)
        elif data.startswith("cmd:"):
            await _handle_global_cmd(update, context, user_id, lang, data)
        elif data.startswith("menu:"):
            await _handle_menu_nav(update, context, user_id, lang, data)
        elif data.startswith("deck:"):
            await _handle_deck(update, context, user_id, lang, data)
        elif data.startswith("queue:"):
            await _handle_queue(update, context, user_id, lang, data)
        elif data.startswith("fx:"):
            await _handle_fx(update, context, user_id, lang, data)
        elif data.startswith("lib:"):
            await _handle_library(update, context, user_id, lang, data)
        elif data.startswith("fav:"):
            await _handle_fav(update, context, user_id, lang, data)
        elif data.startswith("settings:"):
            await _handle_settings(update, context, user_id, lang, data)
        elif data.startswith("action:"):
            await _handle_action(update, context, user_id, lang, data)
        elif data.startswith("np:"):
            await _handle_now_playing(update, context, user_id, lang, data)
        else:
            logger.warning("Unhandled callback data: %s", data)
    except Exception:
        logger.exception("Error handling callback %s", data)
        await safe_error(update, context, lang)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

async def _handle_back(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str
) -> None:
    """Go back one level in the navigation stack."""
    stack = nav_stack.get(user_id, ["main"])
    if len(stack) > 1:
        stack.pop()
    state = stack[-1] if stack else "main"
    await _render_state(update, context, user_id, lang, state)


async def _render_state(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    lang: str,
    state: str,
) -> None:
    """Render a menu state by name."""
    if state == "main":
        text, kb = build_main_menu(lang)
    elif state == "decks":
        text, kb = build_deck_select_menu(lang)
    elif state.startswith("deck_control:"):
        deck = int(state.split(":")[1])
        text, kb = build_deck_control_menu(deck, lang)
    elif state == "queue":
        queue_items = await _fetch_queue()
        text, kb = build_queue_menu(queue_items, lang)
    elif state == "fx":
        fx1, fx2 = await _fetch_fx_state()
        text, kb = build_fx_menu(fx1, fx2, lang)
    elif state == "library":
        text, kb = build_library_menu(lang)
    elif state == "favs":
        favs = await get_favorites(user_id)
        text, kb = build_favs_menu(favs, lang)
    elif state == "settings":
        bpm_on = await get_user_setting(user_id, "bpm_display")
        notif_on = await get_user_setting(user_id, "notifications")
        text, kb = build_settings_menu(lang, bpm_on, notif_on)
    elif state == "history":
        try:
            data = await midi_get("/history")
            tracks = data.get("tracks", [])
        except Exception:
            tracks = []
        text, kb = build_history_menu(tracks, lang)
    else:
        text, kb = build_main_menu(lang)

    await send_menu(update, context, text, kb)


# ---------------------------------------------------------------------------
# Global commands (play / pause / skip from main menu)
# ---------------------------------------------------------------------------

async def _handle_global_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    cmd = data.split(":")[1]
    try:
        await midi_command(f"/transport/{cmd}")
        await answer_toast(update.callback_query, t(f"{cmd}_confirm", lang))  # type: ignore[arg-type]
    except Exception:
        await answer_toast(update.callback_query, t("error_midi", lang))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Menu navigation
# ---------------------------------------------------------------------------

async def _handle_menu_nav(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    menu = data.split(":")[1]
    nav_stack.setdefault(user_id, ["main"]).append(menu)
    await _render_state(update, context, user_id, lang, menu)


# ---------------------------------------------------------------------------
# Deck controls
# ---------------------------------------------------------------------------

async def _handle_deck(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    parts = data.split(":")
    # deck:select:<n>
    if parts[1] == "select":
        deck = int(parts[2])
        selected_deck[user_id] = deck
        state = f"deck_control:{deck}"
        nav_stack.setdefault(user_id, ["main"]).append(state)
        text, kb = build_deck_control_menu(deck, lang)
        await send_menu(update, context, text, kb)
        return

    deck = int(parts[1])
    action = parts[2]

    if action == "hotcue":
        pad = int(parts[3])
        endpoint = f"/deck/{deck}/hotcue/{pad}"
    elif action == "loop":
        beats = parts[3]
        endpoint = f"/deck/{deck}/loop/{beats}"
    elif action == "jump":
        beats = parts[3]
        endpoint = f"/deck/{deck}/jump/{beats}"
    else:
        endpoint = f"/deck/{deck}/{action}"

    try:
        await midi_command(endpoint)
        await answer_toast(update.callback_query, t("deck_action_confirm", lang).format(deck=deck, action=action))  # type: ignore[arg-type]
    except Exception:
        await answer_toast(update.callback_query, t("error_midi", lang))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------

async def _fetch_queue() -> list[str]:
    """Fetch the current queue from the MIDI server."""
    try:
        data = await midi_get("/queue")
        return data.get("items", [])
    except Exception:
        return []


async def _handle_queue(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    action = data.split(":")[1]
    if action == "add":
        await answer_toast(update.callback_query, t("queue_add_prompt", lang))  # type: ignore[arg-type]
        return
    if action == "clear":
        try:
            await midi_command("/queue/clear")
            await answer_toast(update.callback_query, t("queue_cleared", lang))  # type: ignore[arg-type]
        except Exception:
            await answer_toast(update.callback_query, t("error_midi", lang))  # type: ignore[arg-type]
        # Re-render queue
        queue_items = await _fetch_queue()
        text, kb = build_queue_menu(queue_items, lang)
        await send_menu(update, context, text, kb)


# ---------------------------------------------------------------------------
# FX
# ---------------------------------------------------------------------------

async def _fetch_fx_state() -> tuple[bool, bool]:
    """Fetch FX on/off state from the MIDI server."""
    try:
        data = await midi_get("/fx/state")
        return data.get("fx1", False), data.get("fx2", False)
    except Exception:
        return False, False


async def _handle_fx(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    fx_num = data.split(":")[2]
    try:
        await midi_command(f"/fx/{fx_num}/toggle")
        await answer_toast(update.callback_query, t("fx_toggled", lang).format(fx=fx_num))  # type: ignore[arg-type]
    except Exception:
        await answer_toast(update.callback_query, t("error_midi", lang))  # type: ignore[arg-type]
    # Re-render
    fx1, fx2 = await _fetch_fx_state()
    text, kb = build_fx_menu(fx1, fx2, lang)
    await send_menu(update, context, text, kb)


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------

async def _handle_library(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    source = data.split(":")[1]
    if source == "upload":
        await answer_toast(update.callback_query, t("lib_upload_prompt", lang))  # type: ignore[arg-type]
        return
    try:
        await midi_command(f"/library/browse", payload={"source": source})
        await answer_toast(update.callback_query, t("lib_browsing", lang).format(source=source.title()))  # type: ignore[arg-type]
    except Exception:
        await answer_toast(update.callback_query, t("error_midi", lang))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Favourites
# ---------------------------------------------------------------------------

async def _handle_fav(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    # fav:load:<deck>:<track_id>
    parts = data.split(":")
    deck = int(parts[2])
    track_id = parts[3]
    try:
        await midi_command(f"/deck/{deck}/load", payload={"track_id": track_id})
        await answer_toast(update.callback_query, t("fav_loaded", lang).format(deck=deck))  # type: ignore[arg-type]
    except Exception:
        await answer_toast(update.callback_query, t("error_midi", lang))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

async def _handle_settings(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    # settings:toggle:<key>
    parts = data.split(":")
    key = parts[2]
    new_val = await toggle_user_setting(user_id, key)
    state_str = t("on", lang) if new_val else t("off", lang)
    await answer_toast(update.callback_query, f"{key}: {state_str}")  # type: ignore[arg-type]
    # Re-render settings
    bpm_on = await get_user_setting(user_id, "bpm_display")
    notif_on = await get_user_setting(user_id, "notifications")
    text, kb = build_settings_menu(lang, bpm_on, notif_on)
    await send_menu(update, context, text, kb)


# ---------------------------------------------------------------------------
# Language toggle
# ---------------------------------------------------------------------------

async def _handle_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    action = data.split(":")[1]
    if action == "toggle_lang":
        new_lang = "bg" if lang == "en" else "en"
        await set_user_lang(user_id, new_lang)
        # Re-render current view
        stack = nav_stack.get(user_id, ["main"])
        state = stack[-1] if stack else "main"
        await _render_state(update, context, user_id, new_lang, state)


# ---------------------------------------------------------------------------
# Now Playing actions
# ---------------------------------------------------------------------------

async def _handle_now_playing(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str, data: str
) -> None:
    action = data.split(":")[1]
    if action == "like":
        try:
            np_data = await midi_get("/now_playing")
            track_id = np_data.get("track_id", "unknown")
            track_name = np_data.get("track_name", t("unknown_track", lang))
            await add_favorite(user_id, track_id, track_name)
            await answer_toast(update.callback_query, t("liked_confirm", lang).format(track=track_name))  # type: ignore[arg-type]
        except Exception:
            await answer_toast(update.callback_query, t("error_generic", lang))  # type: ignore[arg-type]
    elif action == "skip":
        try:
            await midi_command("/transport/skip")
            await answer_toast(update.callback_query, t("skip_confirm", lang))  # type: ignore[arg-type]
        except Exception:
            await answer_toast(update.callback_query, t("error_midi", lang))  # type: ignore[arg-type]
    elif action == "pause":
        try:
            await midi_command("/transport/pause")
            await answer_toast(update.callback_query, t("pause_confirm", lang))  # type: ignore[arg-type]
        except Exception:
            await answer_toast(update.callback_query, t("error_midi", lang))  # type: ignore[arg-type]

    # Refresh now-playing card in place
    await cmd_now_playing(update, context)


# ---------------------------------------------------------------------------
# File upload handler
# ---------------------------------------------------------------------------

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle uploaded MP3/MP4 files."""
    user_id = _get_user(update).id
    chat_id = _get_chat(update).id
    lang = await get_user_lang(user_id)
    doc = update.message.document  # type: ignore[union-attr]

    if not doc:
        return

    mime = doc.mime_type or ""
    if mime not in ("audio/mpeg", "audio/mp4", "video/mp4", "audio/x-m4a"):
        await context.bot.send_message(
            chat_id=chat_id,
            text=t("upload_invalid_format", lang),
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=t("upload_processing", lang),
    )

    try:
        file = await doc.get_file()
        file_bytes = await file.download_as_bytearray()
        resp = await http_client.post(
            "/library/upload",
            files={"file": (doc.file_name or "upload.mp3", bytes(file_bytes), mime)},
        )
        resp.raise_for_status()
        result = resp.json()
        track_name = result.get("track_name", doc.file_name)
        await context.bot.send_message(
            chat_id=chat_id,
            text=t("upload_success", lang).format(track=track_name),
        )
    except Exception:
        logger.exception("Upload failed for user %s", user_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=t("upload_failed", lang),
        )


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler."""
    logger.error("Unhandled exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ An unexpected error occurred. Please try again.",
            )
        except Exception:
            pass


async def _shutdown_cleanup(_app: Application) -> None:
    """Clean up resources on bot shutdown."""
    await http_client.aclose()
    logger.info("HTTP client closed.")


# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point — build and run the Telegram bot."""
    _load_translations()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("nowplaying", cmd_now_playing))
    app.add_handler(CommandHandler("history", cmd_history))

    # Callback query handler (inline keyboard)
    app.add_handler(CallbackQueryHandler(callback_router))

    # Document upload handler
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Global error handler
    app.add_error_handler(error_handler)

    # Lifecycle
    app.post_shutdown(_shutdown_cleanup)

    logger.info("Starting RhythmClaw Telegram bot…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
