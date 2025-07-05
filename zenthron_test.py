# ZenthronBot - Telegram bot
# Copyright (C) 2025 R0X
# Licensed under the GNU General Public License v3.0
# See the LICENSE file for details.

#!/usr/bin/env python
# -*- coding: utf-8 -*-

# --- ZenthronBot ---

import logging
import random
import os
import requests
import html
import sqlite3
import speedtest
import asyncio
import subprocess
import re
import io
import telegram
import time
import google.generativeai as genai
import platform
from telegram import __version__ as ptb_version
from telethon import __version__ as telethon_version
from typing import List, Tuple
from telethon import TelegramClient
from telethon.tl.types import User as TelethonUser, Channel as TelethonChannel
from telegram import Update, User, Chat, constants, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode, ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ApplicationHandlerStop, JobQueue, CallbackQueryHandler, ChatMemberHandler
from telegram.error import TelegramError, BadRequest
from telegram.request import HTTPXRequest
from datetime import datetime, timezone, timedelta
from texts import (
    KILL_TEXTS, SLAP_TEXTS, PUNCH_TEXTS,
    PAT_TEXTS, BONK_TEXTS, OWNER_WELCOME_TEXTS, LEAVE_TEXTS,
    CANT_TARGET_OWNER_TEXTS, CANT_TARGET_SELF_TEXTS, DEV_WELCOME_TEXTS,
    SUDO_WELCOME_TEXTS, SUPPORT_WELCOME_TEXTS, GENERIC_WELCOME_TEXTS,
    GENERIC_GOODBYE_TEXTS,
)

# --- Logging Configuration ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.vendor.ptb_urllib3.urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger('telethon').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Owner ID Configuration & Bot Start Time ---
OWNER_ID = None
BOT_START_TIME = datetime.now()
TENOR_API_KEY = None
DB_NAME = "zenthron_data.db"
LOG_CHAT_ID = None
API_ID = None
API_HASH = None
SESSION_NAME = "zenthron_user_session"
PUBLIC_AI_ENABLED = False
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MAX_WARNS = 3

# --- Load configuration from environment variables ---
try:
    owner_id_str = os.getenv("TELEGRAM_OWNER_ID")
    if owner_id_str: OWNER_ID = int(owner_id_str); logger.info(f"Owner ID loaded: {OWNER_ID}")
    else: raise ValueError("TELEGRAM_OWNER_ID environment variable not set or empty")
except (ValueError, TypeError) as e: logger.critical(f"CRITICAL: Invalid or missing TELEGRAM_OWNER_ID: {e}"); print(f"\n--- FATAL ERROR --- \nInvalid or missing TELEGRAM_OWNER_ID."); exit(1)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN: logger.critical("CRITICAL: TELEGRAM_BOT_TOKEN not set!"); print("\n--- FATAL ERROR --- \nTELEGRAM_BOT_TOKEN is not set."); exit(1)

try:
    api_id_str = os.getenv("TELEGRAM_API_ID")
    if api_id_str: API_ID = int(api_id_str); logger.info("API ID loaded.")
    else: raise ValueError("TELEGRAM_API_ID environment variable not set or empty")
    API_HASH = os.getenv("TELEGRAM_API_HASH")
    if not API_HASH: raise ValueError("TELEGRAM_API_HASH environment variable not set or empty")
    logger.info("Telethon API credentials loaded successfully.")
except (ValueError, TypeError) as e: 
    logger.critical(f"CRITICAL: Invalid or missing Telethon API credentials: {e}")
    print(f"\n--- FATAL ERROR --- \nInvalid or missing TELEGRAM_API_ID or TELEGRAM_API_HASH."); exit(1)

TENOR_API_KEY = os.getenv("TENOR_API_KEY")
if not TENOR_API_KEY: logger.warning("WARNING: TENOR_API_KEY not set. Themed GIFs disabled.")
else: logger.info("Tenor API Key loaded. Themed GIFs enabled.")

log_chat_id_str = os.getenv("LOG_CHAT_ID")
if log_chat_id_str:
    try:
        LOG_CHAT_ID = int(log_chat_id_str)
        logger.info(f"Log Chat ID loaded: {LOG_CHAT_ID}")
    except ValueError:
        logger.error(f"Invalid LOG_CHAT_ID: '{log_chat_id_str}' is not a valid integer. Will fallback to OWNER_ID for logs.")
        LOG_CHAT_ID = None
else:
    logger.info("LOG_CHAT_ID not set. Operational logs will be sent to OWNER_ID if available.")

APPEAL_CHAT_USERNAME = os.getenv("APPEAL_CHAT_USERNAME")
if not APPEAL_CHAT_USERNAME:
    logger.critical("CRITICAL: APPEAL_CHAT_USERNAME not set!"); 
    print("\n--- FATAL ERROR --- \nAPPEAL_CHAT_USERNAME is not set."); 
    exit(1)
else:
    logger.info(f"Appeal chat loaded: {APPEAL_CHAT_USERNAME}")

# --- Database Initialization ---
def init_db():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                is_bot INTEGER,
                last_seen TEXT 
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_username ON users (username)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_by_id INTEGER,
                timestamp TEXT 
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whitelist_users (
                user_id INTEGER PRIMARY KEY,
                added_by_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_users (
                user_id INTEGER PRIMARY KEY,
                added_by_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sudo_users (
                user_id INTEGER PRIMARY KEY,
                added_by_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dev_users (
                user_id INTEGER PRIMARY KEY,
                added_by_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_bans (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_by_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                added_at TEXT NOT NULL,
                enforce_gban INTEGER DEFAULT 1 NOT NULL,
                welcome_enabled INTEGER DEFAULT 1 NOT NULL,
                custom_welcome TEXT,
                goodbye_enabled INTEGER DEFAULT 1 NOT NULL,
                custom_goodbye TEXT,
                clean_service_messages INTEGER DEFAULT 0 NOT NULL,
                warn_limit INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                chat_id INTEGER NOT NULL,
                note_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_by_id INTEGER,
                created_at TEXT,
                PRIMARY KEY (chat_id, note_name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                reason TEXT,
                warned_by_id INTEGER,
                warned_at TEXT
            )
        """)
        
        conn.commit()
        logger.info(f"Database '{DB_NAME}' initialized successfully (tables users, blacklist, whitelist_users, support_users, sudo_users, dev_users, global_bans, bot_chats, notes, warnings ensured).")
    except sqlite3.Error as e:
        logger.error(f"SQLite error during DB initialization: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

# --- HTML dictionary ---
def safe_escape(text: str) -> str:
    escape_dict = {
        "&": "&",
        "<": "<",
        ">": ">",
        '"': '"',
        "'": "’",
    }

    text_str = str(text)

    for char, replacement in escape_dict.items():
        text_str = text_str.replace(char, replacement)
        
    return text_str

# --- Start Message ---
async def send_startup_log(context: ContextTypes.DEFAULT_TYPE) -> None:
    startup_message_text = "<i>Bot Started...</i>"
    target_id_for_log = LOG_CHAT_ID or OWNER_ID
    
    if target_id_for_log:
        try:
            await context.bot.send_message(
                chat_id=target_id_for_log,
                text=startup_message_text,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Sent startup notification to {target_id_for_log}.")
        except Exception as e:
            logger.error(f"Failed to send startup message to {target_id_for_log}: {e}")
    else:
        logger.warning("No target (LOG_CHAT_ID or OWNER_ID) to send startup message.")

# --- Blacklist Helper Functions ---
def add_to_blacklist(user_id: int, banned_by_id: int, reason: str | None = "No reason provided.") -> bool:
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        current_timestamp_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT OR IGNORE INTO blacklist (user_id, reason, banned_by_id, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, reason, banned_by_id, current_timestamp_iso)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error adding user {user_id} to blacklist: {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()

def remove_from_blacklist(user_id: int) -> bool:
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error removing user {user_id} from blacklist: {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()

def get_blacklist_reason(user_id: int) -> str | None:
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT reason FROM blacklist WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return row[0]
        return None
    except sqlite3.Error as e:
        logger.error(f"SQLite error checking blacklist reason for user {user_id}: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def is_user_blacklisted(user_id: int) -> bool:
    return get_blacklist_reason(user_id) is not None

# --- Blacklist Check Handler ---
async def check_blacklist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    user = update.effective_user

    if user.id == OWNER_ID:
        return

    if is_user_blacklisted(user.id):
        user_mention_log = f"@{user.username}" if user.username else str(user.id)
        message_text_preview = update.message.text[:50] if update.message.text else "[No text content]"
        
        logger.info(f"User {user.id} ({user_mention_log}) is blacklisted. Silently ignoring and blocking interaction: '{message_text_preview}'")
        
        raise ApplicationHandlerStop

# --- Whitelist ---
def add_to_whitelist(user_id: int, added_by_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            timestamp = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT OR IGNORE INTO whitelist_users (user_id, added_by_id, timestamp) VALUES (?, ?, ?)",
                (user_id, added_by_id, timestamp)
            )
            return conn.total_changes > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error adding user {user_id} to whitelist: {e}")
        return False

def remove_from_whitelist(user_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM whitelist_users WHERE user_id = ?", (user_id,))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error removing user {user_id} from whitelist: {e}")
        return False

def is_whitelisted(user_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.cursor().execute("SELECT 1 FROM whitelist_users WHERE user_id = ?", (user_id,)).fetchone()
            return res is not None
    except sqlite3.Error:
        return False

def get_all_whitelist_users_from_db() -> List[Tuple[int, str]]:
    conn = None
    whitelist_list = []
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, timestamp FROM whitelist_users ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        for row in rows:
            whitelist_list.append((row[0], row[1]))
    except sqlite3.Error as e:
        logger.error(f"SQLite error fetching all whitelist users: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return whitelist_list

# --- Support ---
def add_support_user(user_id: int, added_by_id: int) -> bool:
    """Adds a user to the Support list."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        current_timestamp_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT OR IGNORE INTO support_users (user_id, added_by_id, timestamp) VALUES (?, ?, ?)",
            (user_id, added_by_id, current_timestamp_iso)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error adding support user {user_id}: {e}", exc_info=True)
        return False
    finally:
        if conn: conn.close()

def remove_support_user(user_id: int) -> bool:
    """Removes a user from the Support list."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM support_users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error removing support user {user_id}: {e}", exc_info=True)
        return False
    finally:
        if conn: conn.close()

def is_support_user(user_id: int) -> bool:
    """Checks if a user is on the Support list."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM support_users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"SQLite error checking support for user {user_id}: {e}", exc_info=True)
        return False
    finally:
        if conn: conn.close()

def get_all_support_users_from_db() -> List[Tuple[int, str]]:
    """Fetches all Support users from the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, timestamp FROM support_users ORDER BY timestamp DESC")
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"SQLite error fetching all support users: {e}", exc_info=True)
        return []

# --- Sudo ---
def add_sudo_user(user_id: int, added_by_id: int) -> bool:
    """Adds a user to the sudo list."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        current_timestamp_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT OR IGNORE INTO sudo_users (user_id, added_by_id, timestamp) VALUES (?, ?, ?)",
            (user_id, added_by_id, current_timestamp_iso)
        )
        conn.commit()
        return cursor.rowcount > 0 
    except sqlite3.Error as e:
        logger.error(f"SQLite error adding sudo user {user_id}: {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()

def remove_sudo_user(user_id: int) -> bool:
    """Removes a user from the sudo list."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sudo_users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error removing sudo user {user_id}: {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()

def is_sudo_user(user_id: int) -> bool:
    """Checks if a user is on the sudo list (database check only)."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sudo_users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"SQLite error checking sudo for user {user_id}: {e}", exc_info=True)
        return False 
    finally:
        if conn:
            conn.close()

# --- Developer ---
def add_dev_user(user_id: int, added_by_id: int) -> bool:
    """Adds a user to the Developer list."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        current_timestamp_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT OR IGNORE INTO dev_users (user_id, added_by_id, timestamp) VALUES (?, ?, ?)",
            (user_id, added_by_id, current_timestamp_iso)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error adding dev user {user_id}: {e}", exc_info=True)
        return False
    finally:
        if conn: conn.close()

def remove_dev_user(user_id: int) -> bool:
    """Removes a user from the Developer list."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dev_users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error removing dev user {user_id}: {e}", exc_info=True)
        return False
    finally:
        if conn: conn.close()

def is_dev_user(user_id: int) -> bool:
    """Checks if a user is on the Developer list."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM dev_users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"SQLite error checking dev for user {user_id}: {e}", exc_info=True)
        return False
    finally:
        if conn: conn.close()
        
def get_all_dev_users_from_db() -> List[Tuple[int, str]]:
    """Fetches all developers from the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, timestamp FROM dev_users ORDER BY timestamp DESC")
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"SQLite error fetching all dev users: {e}", exc_info=True)
        return []

def is_owner_or_dev(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    return is_dev_user(user_id)

def is_privileged_user(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    if is_dev_user(user_id):
        return True
    if is_sudo_user(user_id):
        return True
    if is_support_user(user_id):
        return True
    return False

# --- User logger ---
def update_user_in_db(user: User | None):
    if not user:
        return
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        current_timestamp_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, language_code, is_bot, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                language_code = excluded.language_code,
                is_bot = excluded.is_bot,
                last_seen = excluded.last_seen 
        """, (
            user.id, user.username, user.first_name, user.last_name,
            user.language_code, 1 if user.is_bot else 0, current_timestamp_iso
        ))
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"SQLite error updating user {user.id} in users table: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

def get_user_from_db_by_username(username_query: str) -> User | None:
    if not username_query:
        return None
    conn = None
    user_obj: User | None = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        normalized_username = username_query.lstrip('@').lower()
        cursor.execute(
            "SELECT user_id, username, first_name, last_name, language_code, is_bot FROM users WHERE LOWER(username) = ?",
            (normalized_username,)
        )
        row = cursor.fetchone()
        if row:
            user_obj = User(
                id=row[0], username=row[1], first_name=row[2] or "",
                last_name=row[3], language_code=row[4], is_bot=bool(row[5])
            )
            logger.info(f"User {username_query} found in DB with ID {row[0]}.")
    except sqlite3.Error as e:
        logger.error(f"SQLite error fetching user by username '{username_query}': {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return user_obj

def get_user_from_db_by_id(user_id: int) -> User | None:
    if not user_id:
        return None
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, first_name, last_name, language_code, is_bot FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                user_obj = User(
                    id=row[0], username=row[1], first_name=row[2] or "",
                    last_name=row[3], language_code=row[4], is_bot=bool(row[5])
                )
                logger.info(f"User ID {user_id} found in DB.")
                return user_obj
    except sqlite3.Error as e:
        logger.error(f"SQLite error fetching user by ID {user_id}: {e}", exc_info=True)
    return None

async def log_user_from_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user:
        update_user_in_db(update.effective_user)
    
    if update.message and update.message.reply_to_message and update.message.reply_to_message.from_user:
        update_user_in_db(update.message.reply_to_message.from_user)

    chat = update.effective_chat
    if chat and chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if 'known_chats' not in context.bot_data:
            context.bot_data['known_chats'] = set()
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    known_ids = {row[0] for row in cursor.execute("SELECT chat_id FROM bot_chats")}
                    context.bot_data['known_chats'] = known_ids
                    logger.info(f"Loaded {len(known_ids)} known chats into cache.")
            except sqlite3.Error as e:
                logger.error(f"Could not preload known chats into cache: {e}")

        if chat.id not in context.bot_data['known_chats']:
            logger.info(f"Passively discovered and adding new chat to DB: {chat.title} ({chat.id})")
            add_chat_to_db(chat.id, chat.title or f"Untitled Chat {chat.id}")
            context.bot_data['known_chats'].add(chat.id)

def get_all_sudo_users_from_db() -> List[Tuple[int, str]]:
    conn = None
    sudo_list = []
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, timestamp FROM sudo_users ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        for row in rows:
            sudo_list.append((row[0], row[1]))
    except sqlite3.Error as e:
        logger.error(f"SQLite error fetching all sudo users: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return sudo_list

def get_all_bot_chats_from_db() -> List[Tuple[int, str, str]]:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT chat_id, chat_title, added_at FROM bot_chats ORDER BY added_at DESC")
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"SQLite error fetching all bot chats: {e}", exc_info=True)
        return []

def remove_chat_from_db_by_id(chat_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bot_chats WHERE chat_id = ?", (chat_id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error removing chat {chat_id} from DB: {e}", exc_info=True)
        return False

async def damnbroski(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    special_message = "💀Bro..."
    
    await _handle_action_command(
        update,
        context,
        [special_message],
        ["caught in 4k", "caught in 4k meme"],
        "damnbroski",
        False,
        ""
    )

def parse_duration_to_timedelta(duration_str: str | None) -> timedelta | None:
    if not duration_str:
        return None
    duration_str = duration_str.lower()
    value = 0
    unit = None
    match = re.match(r"(\d+)([smhdw])", duration_str)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
    else:
        try:
            value = int(duration_str)
            unit = 'm' 
        except ValueError:
            return None
    if unit == 's': return timedelta(seconds=value)
    elif unit == 'm': return timedelta(minutes=value)
    elif unit == 'h': return timedelta(hours=value)
    elif unit == 'd': return timedelta(days=value)
    elif unit == 'w': return timedelta(weeks=value)
    return None

async def _parse_mod_command_args(args: list[str]) -> tuple[str | None, str | None, str | None]:
    target_arg: str | None = None
    duration_arg: str | None = None
    reason_list: list[str] = []
    if not args: return None, None, None
    target_arg = args[0]
    remaining_args = args[1:]
    if remaining_args:
        potential_duration_td = parse_duration_to_timedelta(remaining_args[0])
        if potential_duration_td is not None:
            duration_arg = remaining_args[0]
            reason_list = remaining_args[1:]
        else:
            reason_list = remaining_args
    reason_str = " ".join(reason_list) if reason_list else None
    return target_arg, duration_arg, reason_str

def parse_promote_args(args: list[str]) -> tuple[str | None, str | None]:
    target_arg: str | None = None
    custom_title_full: str | None = None

    if not args:
        return None, None
    
    target_arg = args[0]
    if len(args) > 1:
        custom_title_full = " ".join(args[1:])
        
    return target_arg, custom_title_full
    
async def send_safe_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs):
    """
    Tries to reply to the message. If the original message is deleted,
    it sends a new message to the chat instead of crashing.
    """
    try:
        await update.message.reply_text(text=text, **kwargs)
    except telegram.error.BadRequest as e:
        if "Message to be replied not found" in str(e):
            logger.warning("Original message not found for reply. Sending as a new message.")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, **kwargs)
        else:
            raise e

async def _can_user_perform_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    permission: str,
    failure_message: str,
    allow_bot_privileged_override: bool = True
) -> bool:
    user = update.effective_user
    chat = update.effective_chat

    if allow_bot_privileged_override and (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        return True

    try:
        actor_chat_member = await context.bot.get_chat_member(chat.id, user.id)
        
        if actor_chat_member.status == "creator":
            return True

        if actor_chat_member.status == "administrator" and getattr(actor_chat_member, permission, False):
            return True
            
    except TelegramError as e:
        logger.error(f"Error checking permissions for {user.id} in chat {chat.id}: {e}")
        await send_safe_reply(update, context, text="Error: Couldn't verify your permissions due to an API error.")
        return False

    await send_safe_reply(update, context, text=failure_message)
    return False

# --- Utility Functions ---
def telethon_entity_to_ptb_user(entity: 'TelethonUser') -> User | None:
    if not isinstance(entity, TelethonUser):
        return None
    
    return User(
        id=entity.id,
        first_name=entity.first_name or "",
        is_bot=entity.bot or False,
        last_name=entity.last_name,
        username=entity.username,
        language_code=getattr(entity, 'lang_code', None)
    )

async def resolve_user_with_telethon(context: ContextTypes.DEFAULT_TYPE, target_input: str, update: Update) -> User | Chat | None:
    if update.message and update.message.entities:
        for entity in update.message.entities:
            if entity.type == constants.MessageEntityType.TEXT_MENTION:
                mentioned_text = update.message.text[entity.offset:(entity.offset + entity.length)]
                if target_input.lstrip('@').lower() == mentioned_text.lstrip('@').lower():
                    if entity.user:
                        logger.info(f"Resolved '{target_input}' via Text Mention entity.")
                        update_user_in_db(entity.user)
                        return entity.user

    identifier: str | int = target_input
    try:
        identifier = int(target_input)
    except ValueError:
        pass

    if isinstance(identifier, int):
        entity_from_db = get_user_from_db_by_id(identifier)
    else:
        entity_from_db = get_user_from_db_by_username(identifier)
    
    if entity_from_db:
        return entity_from_db

    try:
        logger.info(f"Resolving '{target_input}' using PTB...")
        ptb_entity = await context.bot.get_chat(target_input)
        if ptb_entity:
            if isinstance(ptb_entity, User):
                update_user_in_db(ptb_entity)
            return ptb_entity
    except Exception as e:
        logger.warning(f"PTB failed for '{target_input}': {e}.")

    if not is_privileged_user(update.effective_user.id):
        logger.warning(f"User {update.effective_user.id} is not privileged to use Telethon search.")
        return None

    if 'telethon_client' not in context.bot_data:
        return None
    
    telethon_client: 'TelegramClient' = context.bot_data['telethon_client']
    try:
        logger.info(f"Resolving '{target_input}' using Telethon...")
        entity_from_telethon = await telethon_client.get_entity(target_input)
        
        if isinstance(entity_from_telethon, TelethonUser):
            ptb_user = telethon_entity_to_ptb_user(entity_from_telethon)
            if ptb_user:
                update_user_in_db(ptb_user)
                return ptb_user
        
    except Exception as e:
        logger.error(f"All methods failed for '{target_input}'. Final Telethon error: {e}")

    return None
    
def get_readable_time_delta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0: 
        return "0s"
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days > 0: 
        parts.append(f"{days}d")
    if hours > 0: 
        parts.append(f"{hours}h")
    if minutes > 0: 
        parts.append(f"{minutes}m")
    if not parts and seconds >= 0 : 
        parts.append(f"{seconds}s")
    elif seconds > 0: 
        parts.append(f"{seconds}s")
    return ", ".join(parts) if parts else "0s"

def add_to_gban(user_id: int, banned_by_id: int, reason: str | None) -> bool:
    reason = reason or "No reason provided."
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO global_bans (user_id, reason, banned_by_id, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, reason, banned_by_id, timestamp)
            )
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error adding user {user_id} to gban list: {e}")
        return False

def remove_from_gban(user_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM global_bans WHERE user_id = ?", (user_id,))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error removing user {user_id} from gban list: {e}")
        return False

def get_gban_reason(user_id: int) -> str | None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT reason FROM global_bans WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    except sqlite3.Error as e:
        logger.error(f"SQLite error checking gban status for user {user_id}: {e}")
        return None

def add_chat_to_db(chat_id: int, chat_title: str):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO bot_chats (chat_id, chat_title, added_at) VALUES (?, ?, ?)",
                (chat_id, chat_title, timestamp)
            )
    except sqlite3.Error as e:
        logger.error(f"Failed to add chat {chat_id} to DB: {e}")

def remove_chat_from_db(chat_id: int):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bot_chats WHERE chat_id = ?", (chat_id,))
    except sqlite3.Error as e:
        logger.error(f"Failed to remove chat {chat_id} from DB: {e}")

def is_gban_enforced(chat_id: int) -> bool:
    """Checks if gban enforcement is enabled for a specific chat."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            res = cursor.execute(
                "SELECT enforce_gban FROM bot_chats WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            if res is None:
                return True 
            return bool(res[0])
    except sqlite3.Error as e:
        logger.error(f"Could not check gban enforcement status for chat {chat_id}: {e}")
        return True
        
# --- Helper Functions (Check Targets, Get GIF) ---
async def check_target_protection(target_user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if target_user_id == OWNER_ID: return True
    if target_user_id == context.bot.id: return True
    return False

async def check_username_protection(target_mention: str, context: ContextTypes.DEFAULT_TYPE) -> tuple[bool, bool]:
    is_protected = False; is_owner_match = False; bot_username = context.bot.username
    if bot_username and target_mention.lower() == f"@{bot_username.lower()}": is_protected = True
    elif OWNER_ID:
        owner_username = None
        try: owner_chat = await context.bot.get_chat(OWNER_ID); owner_username = owner_chat.username
        except Exception as e: logger.warning(f"Could not fetch owner username for protection check: {e}")
        if owner_username and target_mention.lower() == f"@{owner_username.lower()}": is_protected = True; is_owner_match = True
    return is_protected, is_owner_match

async def get_themed_gif(context: ContextTypes.DEFAULT_TYPE, search_terms: list[str]) -> str | None:
    if not TENOR_API_KEY: return None
    if not search_terms: logger.warning("No search terms for get_themed_gif."); return None
    
    search_term = random.choice(search_terms)
    logger.info(f"Searching Tenor for BEST results: '{search_term}'")
    
    url = "https://tenor.googleapis.com/v2/search"
    params = { 
        "q": search_term, 
        "key": TENOR_API_KEY, 
        "client_key": "zenthron_project_py", 
        "limit": 50, 
        "media_filter": "gif", 
        "contentfilter": "high"
    }
    
    try:
        response = requests.get(url, params=params, timeout=7)
        if response.status_code != 200:
            logger.error(f"Tenor API failed for '{search_term}', status: {response.status_code}")
            try: error_content = response.json(); logger.error(f"Tenor error content: {error_content}")
            except requests.exceptions.JSONDecodeError: logger.error(f"Tenor error response (non-JSON): {response.text[:500]}")
            return None
        
        data = response.json()
        results = data.get("results")
        
        if results:
            top_gifs = results[:5] 
            selected_gif = random.choice(top_gifs)
            
            gif_url = selected_gif.get("media_formats", {}).get("gif", {}).get("url")
            if not gif_url: gif_url = selected_gif.get("media_formats", {}).get("tinygif", {}).get("url")
            
            if gif_url: 
                logger.info(f"Found high-quality GIF URL: {gif_url}")
                return gif_url
            else: 
                logger.warning(f"Could not extract GIF URL from Tenor item for '{search_term}'.")
        else: 
            logger.warning(f"No results on Tenor for '{search_term}'.")
            logger.debug(f"Tenor response (no results): {data}")
            
    except requests.exceptions.Timeout: logger.error(f"Timeout fetching GIF from Tenor for '{search_term}'.")
    except requests.exceptions.RequestException as e: logger.error(f"Network/Request error fetching GIF from Tenor: {e}")
    except Exception as e: logger.error(f"Unexpected error in get_themed_gif for '{search_term}': {e}", exc_info=True)
    
    return None

def create_user_html_link(user: User) -> str:
    
    full_name = getattr(user, 'full_name', None)
    first_name = getattr(user, 'first_name', None)
    
    display_text = ""
    if full_name:
        display_text = full_name
    elif first_name:
        display_text = first_name
    else:
        display_text = str(user.id)
        
    display_text = display_text.strip()
    
    if not display_text:
        display_text = str(user.id)
        
    return f'<a href="tg://user?id={user.id}">{safe_escape(display_text)}</a>'

def markdown_to_html(text: str) -> str:
    text = re.sub(
        r'```(\w+)\n(.*?)\n```', 
        r'<pre><code class="language-\1">\2</code></pre>', 
        text, 
        flags=re.DOTALL
    )
    
    text = re.sub(
        r'```\n(.*?)\n```', 
        r'<pre>\1</pre>', 
        text, 
        flags=re.DOTALL
    )
    
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    return text

# --- Welcome/Goodbye Helpers ---
def set_welcome_setting(chat_id: int, enabled: bool, text: str | None = None) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO bot_chats (chat_id, added_at) VALUES (?, ?)", 
                           (chat_id, datetime.now(timezone.utc).isoformat()))
            
            cursor.execute(
                "UPDATE bot_chats SET welcome_enabled = ?, custom_welcome = ? WHERE chat_id = ?",
                (1 if enabled else 0, text, chat_id)
            )
        return True
    except sqlite3.Error as e:
        logger.error(f"Error setting welcome for chat {chat_id}: {e}")
        return False

def set_goodbye_setting(chat_id: int, enabled: bool, text: str | None = None) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO bot_chats (chat_id, added_at) VALUES (?, ?)", 
                           (chat_id, datetime.now(timezone.utc).isoformat()))
            
            cursor.execute(
                "UPDATE bot_chats SET goodbye_enabled = ?, custom_goodbye = ? WHERE chat_id = ?",
                (1 if enabled else 0, text, chat_id)
            )
        return True
    except sqlite3.Error as e:
        logger.error(f"Error setting goodbye for chat {chat_id}: {e}")
        return False

def get_welcome_settings(chat_id: int) -> Tuple[bool, str | None]:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.cursor().execute(
                "SELECT welcome_enabled, custom_welcome FROM bot_chats WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            if res:
                return bool(res[0]), res[1]
            return True, None
    except sqlite3.Error:
        logger.error(f"Error getting welcome settings for chat {chat_id}")
        return True, None

def get_goodbye_settings(chat_id: int) -> Tuple[bool, str | None]:
    """Pobiera ustawienia pożegnań (czy włączone, jaki tekst)."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.cursor().execute(
                "SELECT goodbye_enabled, custom_goodbye FROM bot_chats WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            if res:
                return bool(res[0]), res[1]
            return True, None
    except sqlite3.Error:
        logger.error(f"Error getting goodbye settings for chat {chat_id}")
        return True, None

def set_clean_service(chat_id: int, enabled: bool) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO bot_chats (chat_id, added_at) VALUES (?, ?)", 
                           (chat_id, datetime.now(timezone.utc).isoformat()))
            
            cursor.execute(
                "UPDATE bot_chats SET clean_service_messages = ? WHERE chat_id = ?",
                (1 if enabled else 0, chat_id)
            )
        return True
    except sqlite3.Error as e:
        logger.error(f"Error setting clean service for chat {chat_id}: {e}")
        return False

def should_clean_service(chat_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.cursor().execute(
                "SELECT clean_service_messages FROM bot_chats WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            return bool(res[0]) if res else False
    except sqlite3.Error:
        logger.error(f"Error checking clean service for chat {chat_id}")
        return False

# --- Notes (Filters) Helper Functions ---
def add_note(chat_id: int, note_name: str, content: str, user_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            timestamp = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO notes (chat_id, note_name, content, created_by_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (chat_id, note_name.lower(), content, user_id, timestamp)
            )
        return True
    except sqlite3.Error as e:
        logger.error(f"Error adding note '{note_name}' to chat {chat_id}: {e}")
        return False

def remove_note(chat_id: int, note_name: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE chat_id = ? AND note_name = ?", (chat_id, note_name.lower()))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error removing note '{note_name}' from chat {chat_id}: {e}")
        return False

def get_note(chat_id: int, note_name: str) -> str | None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.cursor().execute("SELECT content FROM notes WHERE chat_id = ? AND note_name = ?", (chat_id, note_name.lower())).fetchone()
            return res[0] if res else None
    except sqlite3.Error:
        return None

def get_all_notes(chat_id: int) -> List[str]:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            notes = conn.cursor().execute("SELECT note_name FROM notes WHERE chat_id = ? ORDER BY note_name", (chat_id,)).fetchall()
            return [row[0] for row in notes]
    except sqlite3.Error:
        return []

# --- Warnings Helper Functions ---
def add_warning(chat_id: int, user_id: int, reason: str, admin_id: int) -> Tuple[int, int]:
    """Dodaje ostrzeżenie i zwraca (ID nowego warna, łączna liczba warnów)."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO warnings (chat_id, user_id, reason, warned_by_id, warned_at) VALUES (?, ?, ?, ?, ?)",
                (chat_id, user_id, reason, admin_id, timestamp)
            )
            new_warn_id = cursor.lastrowid
            
            count = cursor.execute(
                "SELECT COUNT(*) FROM warnings WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            ).fetchone()[0]
            
            return new_warn_id, count
    except sqlite3.Error as e:
        logger.error(f"Error adding warning for user {user_id} in chat {chat_id}: {e}")
        return -1, -1

def remove_warning_by_id(warn_id: int) -> bool:
    """Usuwa konkretne ostrzeżenie po jego ID."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM warnings WHERE id = ?", (warn_id,))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error removing warning with ID {warn_id}: {e}")
        return False

def get_warnings(chat_id: int, user_id: int) -> List[Tuple[str, int]]:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            warnings = conn.cursor().execute(
                "SELECT reason, warned_by_id FROM warnings WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            ).fetchall()
            return warnings
    except sqlite3.Error:
        logger.error(f"Error getting warnings for user {user_id} in chat {chat_id}")
        return []

def reset_warnings(chat_id: int, user_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error resetting warnings for user {user_id} in chat {chat_id}: {e}")
        return False

def set_warn_limit(chat_id: int, limit: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO bot_chats (chat_id, added_at) VALUES (?, ?)", 
                           (chat_id, datetime.now(timezone.utc).isoformat()))
            cursor.execute("UPDATE bot_chats SET warn_limit = ? WHERE chat_id = ?", (limit, chat_id))
        return True
    except sqlite3.Error as e:
        logger.error(f"Error setting warn limit for chat {chat_id}: {e}")
        return False

def get_warn_limit(chat_id: int) -> int:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.cursor().execute("SELECT warn_limit FROM bot_chats WHERE chat_id = ?", (chat_id,)).fetchone()
            if res and res[0] is not None and res[0] > 0:
                return res[0]
            return MAX_WARNS
    except sqlite3.Error:
        logger.error(f"Error getting warn limit for chat {chat_id}")
        return MAX_WARNS

async def handle_bot_permission_changes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.chat_member:
        return

    chat = update.chat_member.chat
    new_member_status = update.chat_member.new_chat_member
    
    if new_member_status.user.id != context.bot.id:
        return

    if new_member_status.status == ChatMemberStatus.ADMINISTRATOR:
        if hasattr(new_member_status, 'can_post_messages') and not new_member_status.can_post_messages:
            is_muted = True
        else:
            is_muted = False
    
    elif new_member_status.status == ChatMemberStatus.MEMBER and new_member_status.can_send_messages is False:
        is_muted = True
    
    elif new_member_status.status == ChatMemberStatus.RESTRICTED and new_member_status.can_send_messages is False:
        is_muted = True
        
    else:
        is_muted = False

    if is_muted:
        logger.warning(f"Bot was muted in chat {chat.title} ({chat.id}). Leaving automatically.")
        try:
            if OWNER_ID:
                log_text = (
                    f"<b>#AUTOLEAVE</b> (Muted)\n\n"
                    f"Bot automatically left the chat <b>{safe_escape(chat.title)}</b> (<code>{chat.id}</code>) "
                    f"because it was muted and can no longer send messages."
                )
                await context.bot.send_message(chat_id=OWNER_ID, text=log_text, parse_mode=ParseMode.HTML)

            await context.bot.leave_chat(chat.id)
            
        except Exception as e:
            logger.error(f"Error during automatic leave from chat {chat.id}: {e}")

# --- Command Handlers ---
HELP_TEXT = """
<b>Here are the commands you can use:</b>

<b>🔹 General Commands</b>
/start - Shows the welcome message.
/help - Shows this help message.
/ping - Checks the bot's latency.
/github - Get the link to the bot's source code.
/owner - Info about the bot owner.
/sudocmds - List privileged commands (for authorized users).

<b>🔹 User & Chat Info</b>
/info &lt;ID/@user/reply&gt; - Get information about a user.
/chatinfo - Get basic info about the current chat.
/id - Get user or chat id.
/listadmins - Show the list of administrators in this chat. <i>(Alias: /admins)</i>

<b>🔹 Moderation Commands</b>
/ban &lt;ID/@user/reply&gt; [Time] [Reason] - Ban a user.
/unban &lt;ID/@user/reply&gt; - Unban a user.
/mute &lt;ID/@user/reply&gt; [Time] [Reason] - Mute a user.
/unmute &lt;ID/@user/reply&gt; - Unmute a user.
/kick &lt;ID/@user/reply&gt; [Reason] - Kick a user.
/kickme - Kick yourself from the chat.
/warn &lt;ID/@user/reply&gt; [Reason] - Warn a user.
/warnings &lt;ID/@user/reply&gt; - Check a user's warnings.
/resetwarns &lt;ID/@user/reply&gt; - Reset user's warnings.

<b>🔹 Admin Tools</b>
/promote &lt;ID/@user/reply&gt; [Title] - Promote a user to admin.
/demote &lt;ID/@user/reply&gt; - Demote an admin.
/pin &lt;loud/notify&gt; - Pin the replied-to message.
/unpin - Unpin the currently pinned message.
/purge &lt;silent&gt; - Delete messages up to the replied-to message.
/report &lt;reason&gt; - Report a user to the chat admins (reply to a message).
/zombies &lt;clean&gt; - Find and optionally remove deleted accounts.

<b>🔹 Notes</b>
/notes - See all notes in this chat.
/addnote &lt;name&gt; [content] - Create a new note.
/delnote &lt;name&gt; - Delete a note.
<i>To get a note, simply use #notename in the chat.</i>

<b>🔹 Chat Settings</b>
/welcomehelp - Get help with text formatting and placeholders.
/welcome &lt;on/off&gt; - Enable or disable welcome messages.
/setwelcome &lt;text&gt; - Set a custom welcome message.
/resetwelcome - Reset the welcome message to default.
/goodbye &lt;on/off&gt; - Enable or disable goodbye messages.
/setgoodbye &lt;text&gt; - Set a custom goodbye message.
/resetgoodbye - Reset the goodbye message to default.
/setwarnlimit &lt;number&gt; - Set the warning limit for this chat.
/cleanservice &lt;on/off&gt; - Enable or disable cleaning of service messages.

<b>🔹 Chat Security</b>
/enforcegban &lt;yes/no&gt; - Enable/disable Global Ban enforcement. <i>(Chat Creator only)</i>

<b>🔹 AI Commands</b>
/askai &lt;prompt&gt; - Ask the AI a question.

<b>🔹 Fun Commands</b>
/kill &lt;@user/reply&gt; - Metaphorically eliminate someone.
/punch &lt;@user/reply&gt; - Deliver a textual punch.
/slap &lt;@user/reply&gt; - Administer a swift slap.
/pat &lt;@user/reply&gt; - Gently pat someone.
/bonk &lt;@user/reply&gt; - Playfully bonk someone.
"""

ADMIN_NOTE_TEXT = """
<i>Note: Commands /ban, /unban, /mute, /unmute, /kick, /pin, /unpin, /purge, /promote, /demote, /zombies can be used by sudo, developer users even if they are not chat administrators. (Use it wisely and don't overuse your power. Otherwise you may lose your privileges)</i>
"""

SUPPORT_COMMANDS_TEXT = """
<b>🔹 Your Privileged Commands:</b>
/gban &lt;ID/@user/reply&gt; [Reason] - Ban a user globally.
/ungban &lt;ID/@user/reply&gt; - Unban a user globally.
/ping - Check bot ping.
"""

SUDO_COMMANDS_TEXT = """
/status - Show bot status.
/stats - Show bot database stats.
/cinfo &lt;Optional chat ID&gt; - Get detailed info about the current or specified chat.
/say &lt;Optional chat ID&gt; [Your text] - Send a message as the bot.
/blist &lt;ID/@user/reply&gt; [Reason] - Add a user to the blacklist.
/unblist &lt;ID/@user/reply&gt; - Remove a user from the blacklist.
"""

DEVELOPER_COMMANDS_TEXT = """
/speedtest - Perform an internet speed test.
/setai &lt;enable/disable&gt; - Turn on or off ai access for all users. <i>(Does not apply to privileged users)</i>
/listgroups - List all known by bot groups.
/delgroup &lt;ID 1&gt; [ID 2] - Remove groups from database
/cleangroups - Remove cached groups from database automatically.
/listsupport - List all users with support privileges.
/addsupport &lt;ID/@user/reply&gt; - Grant Support permissions to a user.
/delsupport &lt;ID/@user/reply&gt; - Revoke Support permissions from a user.
/listsudo - List all users with sudo privileges.
/addsudo &lt;ID/@user/reply&gt; - Grant SUDO (bot admin) permissions to a user.
/delsudo &lt;ID/@user/reply&gt; - Revoke SUDO (bot admin) permissions from a user.
/listdevs - List all users with developer privileges.
/setrank &lt;ID/@user/reply&gt; [support/sudo/dev] - Change the rank of a privileged user.
"""

OWNER_COMMANDS_TEXT = """
/leave &lt;Optional chat ID&gt; - Make the bot leave a chat.
/adddev &lt;ID/@user/reply&gt; - Grant Developer (All) permissions to a user.
/deldev &lt;ID/@user/reply&gt; - Revoke Developer (All) permissions from a user.
/shell &lt;command&gt; - Execute the command in the terminal.
/execute &lt;file patch&gt; [args...] - Run script.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    welcome_message = f"Welcome, {user.mention_html()}! I am a Zenthron. Your Telegram group assistant.\nUse /help to see available commands.\n\n<i>I'm Still a Work In Progress [WIP]. Various bugs and security holes may appear for which Bot creators are not responsible [You add me to group at your own risk]. For any questions or issues, please contact our support team at {APPEAL_CHAT_USERNAME}.</i>"
    
    if context.args:
        if context.args[0] == 'help':
            await update.message.reply_html(HELP_TEXT, disable_web_page_preview=True)
            return
        
        if context.args[0] == 'sudocmds':
            if not is_privileged_user(user.id):
                return

            help_parts = []

            if is_sudo_user(user.id) or is_dev_user(user.id) or user.id == OWNER_ID:
                help_parts.append(ADMIN_NOTE_TEXT)
            
            if is_support_user(user.id) or is_sudo_user(user.id) or is_dev_user(user.id) or user.id == OWNER_ID:
                help_parts.append(SUPPORT_COMMANDS_TEXT)

            if is_sudo_user(user.id) or is_dev_user(user.id) or user.id == OWNER_ID:
                help_parts.append(SUDO_COMMANDS_TEXT)

            if is_dev_user(user.id) or user.id == OWNER_ID:
                help_parts.append(DEVELOPER_COMMANDS_TEXT)

            if user.id == OWNER_ID:
                help_parts.append(OWNER_COMMANDS_TEXT)
            
            final_sudo_help = "".join(help_parts)
            
            if final_sudo_help:
                await update.message.reply_html(final_sudo_help, disable_web_page_preview=True)
            return
            
    await update.message.reply_html(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_html(HELP_TEXT, disable_web_page_preview=True)
        return

    bot_username = context.bot.username
    deep_link_url = f"https://t.me/{bot_username}?start=help"
    
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="📬 Get Help (PM)", url=deep_link_url)]
        ]
    )
    
    message_text = "The help message has been sent to your private chat. Please click the button below to see it."
    
    await send_safe_reply(update, context, text=message_text, reply_markup=keyboard)

async def github(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    github_link = "https://github.com/R0Xofficial/ZenthronBot"
    await update.message.reply_text(f"This bot is open source. You can find the code here: {github_link}", disable_web_page_preview=True)

async def owner_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if OWNER_ID:
        owner_mention = f"<code>{OWNER_ID}</code>"; owner_name = "Bot Owner"
        try: owner_chat = await context.bot.get_chat(OWNER_ID); owner_mention = owner_chat.mention_html(); owner_name = owner_chat.full_name or owner_chat.username or owner_name
        except TelegramError as e: logger.warning(f"Could not fetch owner info ({OWNER_ID}): {e}")
        except Exception as e: logger.warning(f"Unexpected error fetching owner info: {e}")
        message = (f"My God is: 👤 <b>{safe_escape(owner_name)}</b> ({owner_mention})")
        await update.message.reply_html(message)
    else: await update.message.reply_text("Error: Owner information is not configured.")

def format_entity_info(entity: Chat | User,
                       chat_member_status_str: str | None = None,
                       is_target_owner: bool = False,
                       is_target_dev: bool = False,
                       is_target_sudo: bool = False,
                       is_target_support: bool = False,
                       is_target_whitelist: bool = False,
                       blacklist_reason_str: str | None = None,
                       gban_reason_str: str | None = None,
                       current_chat_id_for_status: int | None = None,
                       bot_context: ContextTypes.DEFAULT_TYPE | None = None
                       ) -> str:
    
    info_lines = []
    entity_id = entity.id
    is_user_type = isinstance(entity, User) 
    entity_chat_type = getattr(entity, 'type', None) if not is_user_type else ChatType.PRIVATE

    if is_user_type or entity_chat_type == ChatType.PRIVATE:
        user = entity
        info_lines.append(f"👤 <b>User Information:</b>\n")        
        first_name = safe_escape(getattr(user, 'first_name', "N/A") or "N/A")
        last_name = safe_escape(getattr(user, 'last_name', "") or "")
        username_display = f"@{safe_escape(user.username)}" if user.username else "N/A"
        permalink_user_url = f"tg://user?id={user.id}"
        permalink_text_display = "Link" 
        permalink_html_user = f"<a href=\"{permalink_user_url}\">{permalink_text_display}</a>"
        is_bot_val = getattr(user, 'is_bot', False)
        is_bot_str = "Yes" if is_bot_val else "No"
        language_code_val = getattr(user, 'language_code', "N/A")

        info_lines.extend([
            f"<b>• ID:</b> <code>{user.id}</code>",
            f"<b>• First Name:</b> {first_name}",
        ])
        if getattr(user, 'last_name', None):
            info_lines.append(f"<b>• Last Name:</b> {last_name}")
        
        info_lines.extend([
            f"<b>• Username:</b> {username_display}",
            f"<b>• Permalink:</b> {permalink_html_user}",
            f"<b>• Is Bot:</b> <code>{is_bot_str}</code>",
            f"<b>• Language Code:</b> <code>{language_code_val if language_code_val else 'N/A'}</code>"
        ])

        if chat_member_status_str and current_chat_id_for_status != user.id and current_chat_id_for_status is not None:
            display_status = ""
            if chat_member_status_str == "creator": display_status = "<code>Creator</code>"
            elif chat_member_status_str == "administrator": display_status = "<code>Admin</code>"
            elif chat_member_status_str == "member": display_status = "<code>Member</code>"
            elif chat_member_status_str == "left": display_status = "<code>Not in chat</code>"
            elif chat_member_status_str == "kicked": display_status = "<code>Banned</code>"
            elif chat_member_status_str == "restricted": display_status = "<code>Muted</code>"
            elif chat_member_status_str == "not_a_member": display_status = "<code>Not in chat</code>"
            else: display_status = f"<code>{safe_escape(chat_member_status_str.replace('_', ' ').capitalize())}</code>"
            info_lines.append(f"<b>• Status:</b> {display_status}")

        if is_target_owner:
            info_lines.append(f"\n<b>• User Level:</b> <code>God</code>")
        elif is_target_dev:
            info_lines.append(f"\n<b>• User Level:</b> <code>Developer</code>")
        elif is_target_sudo:
            info_lines.append(f"\n<b>• User Level:</b> <code>Sudo</code>")
        elif is_target_support:
            info_lines.append(f"\n<b>• User Level:</b> <code>Support</code>")
        elif is_target_whitelist:
            info_lines.append(f"\n<b>• User Level:</b> <code>Whitelist</code>")
            
        if blacklist_reason_str is not None:
            info_lines.append(f"\n<b>• Blacklisted:</b> <code>Yes</code>")
            info_lines.append(f"<b>Reason:</b> {safe_escape(blacklist_reason_str)}")
        else:
            info_lines.append(f"\n<b>• Blacklisted:</b> <code>No</code>")

        if gban_reason_str is not None:
            info_lines.append(f"\n<b>• Globally Banned:</b> <code>Yes</code>")
            info_lines.append(f"<b>Reason:</b> {safe_escape(gban_reason_str)}")
        else:
            info_lines.append(f"\n<b>• Globally Banned:</b> <code>No</code>")

        if gban_reason_str is not None or blacklist_reason_str is not None:
            info_lines.append(f"\n<b>Appeal Chat:</b> {APPEAL_CHAT_USERNAME}")

    elif entity_chat_type == ChatType.CHANNEL:
        channel = entity
        info_lines.append(f"📢 <b>Channel info:</b>\n")
        info_lines.append(f"<b>• ID:</b> <code>{channel.id}</code>")
        channel_name_to_display = channel.title or getattr(channel, 'first_name', None) or f"Channel {channel.id}"
        info_lines.append(f"<b>• Title:</b> {safe_escape(channel_name_to_display)}")
        
        if channel.username:
            info_lines.append(f"<b>• Username:</b> @{safe_escape(channel.username)}")
            permalink_channel_url = f"https://t.me/{safe_escape(channel.username)}"
            permalink_text_display = "Link"
            permalink_channel_html = f"<a href=\"{permalink_channel_url}\">{permalink_text_display}</a>"
            info_lines.append(f"<b>• Permalink:</b> {permalink_channel_html}")
        else:
            info_lines.append(f"<b>• Permalink:</b> Private channel (no public link)")
        
    elif entity_chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        chat = entity
        title = safe_escape(chat.title or f"{entity_chat_type.capitalize()} {chat.id}")
        info_lines.append(f"ℹ️ Entity <code>{chat.id}</code> is a <b>{entity_chat_type.capitalize()}</b> ({title}).")
        info_lines.append(f"This command primarily provides detailed info for Users and Channels.")

    else:
        info_lines.append(f"❓ <b>Unknown or Unsupported Entity Type:</b> ID <code>{safe_escape(str(entity_id))}</code>")
        if entity_chat_type:
            info_lines.append(f"  • Type detected: {entity_chat_type.capitalize()}")

    return "\n".join(info_lines)

async def entity_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target_entity: Chat | User | None = None
    
    if update.message.reply_to_message:
        target_entity = update.message.reply_to_message.sender_chat or update.message.reply_to_message.from_user
    elif context.args:
        target_input = " ".join(context.args)
        
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_entity:
            try:
                target_entity = await context.bot.get_chat(target_input)
            except Exception:
                await update.message.reply_text(f"Error: I couldn't find the user. Most likely I've never seen him.")
                return
    else:
        target_entity = update.message.sender_chat or update.effective_user

    if not target_entity:
        await update.message.reply_text("Skrrrt... I don't know what I'm looking for...")
        return

    if isinstance(target_entity, User):
        update_user_in_db(target_entity)

    is_target_owner_flag = (target_entity.id == OWNER_ID)
    is_target_dev_flag = is_dev_user(target_entity.id)
    is_target_sudo_flag = is_sudo_user(target_entity.id)
    is_target_support_flag = is_support_user(target_entity.id)
    is_target_whitelist_flag = is_whitelisted(target_entity.id)
    blacklist_reason_str = get_blacklist_reason(target_entity.id)
    gban_reason_str = get_gban_reason(target_entity.id)
    chat_member_obj: telegram.ChatMember | None = None
    
    if isinstance(target_entity, User) and update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        try:
            chat_member_obj = await context.bot.get_chat_member(update.effective_chat.id, target_entity.id)
        except TelegramError:
            pass

    info_message = format_entity_info(
        entity=target_entity,
        chat_member_status_str=member_status_in_current_chat_str,
        is_target_owner=is_target_owner_flag,
        is_target_dev=is_target_dev_flag,
        is_target_sudo=is_target_sudo_flag,
        is_target_support=is_target_support_flag,
        is_target_whitelist=is_target_whitelist_flag,
        blacklist_reason_str=blacklist_reason_str,
        gban_reason_str=gban_reason_str,
        current_chat_id_for_status=update.effective_chat.id
    )
    
    await update.message.reply_html(info_message, disable_web_page_preview=True)
        
async def list_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        await update.message.reply_text("Huh? This command can only be used in chats.")
        return

    try:
        administrators = await context.bot.get_chat_administrators(chat_id=chat.id)
    except TelegramError as e:
        logger.error(f"Failed to get admin list for chat {chat.id} ('{chat.title}'): {e}")
        await update.message.reply_text(f"Skrrrt... Some supernatural force is preventing me from getting a list of administrators for this chat. Reason: {safe_escape(str(e))}")
        return
    except Exception as e:
        logger.error(f"Unexpected error getting admin list for chat {chat.id}: {e}", exc_info=True)
        await update.message.reply_text(f"BOMBOCLAT! There was a problem retrieving the administrator list.")
        return

    if not administrators:
        await update.message.reply_text("There seem to be no admins in this chat. Unless I'm blind and need glasses 👓")
        return

    chat_title_display = safe_escape(chat.title or chat.first_name or f"Chat ID {chat.id}")
    response_lines = [f"<b>🛡️ Admin list in {chat_title_display}:</b>\n"]

    creator_line: str | None = None

    for admin_member in administrators:
        admin_user = admin_member.user
        
        user_display_name = ""
        if admin_user.username:
            user_display_name = f"<a href=\"tg://user?id={admin_user.id}\">@{safe_escape(admin_user.username)}</a>"
        elif admin_user.full_name:
            user_display_name = f"<a href=\"tg://user?id={admin_user.id}\">{safe_escape(admin_user.full_name)}</a>"
        elif admin_user.first_name:
            user_display_name = f"<a href=\"tg://user?id={admin_user.id}\">{safe_escape(admin_user.first_name)}</a>"
        else:
            user_display_name = f"<a href=\"tg://user?id={admin_user.id}\">User {admin_user.id}</a>"

        admin_info_line = f"• {user_display_name}"

        custom_title = getattr(admin_member, 'custom_title', None)
        is_anonymous = getattr(admin_member, 'is_anonymous', False)

        if is_anonymous:
            admin_info_line += " <i>(Anonymous Admin)</i>"
        
        if custom_title:
            admin_info_line += f" (<code>{safe_escape(custom_title)}</code>)"
        
        if admin_member.status == "creator":
            admin_info_line += " 👑"
            creator_line = admin_info_line
        else:
            response_lines.append(admin_info_line)

    if creator_line:
        response_lines.insert(1, creator_line)

    message_text = "\n".join(response_lines)
    
    if len(message_text) > 4090:
        logger.info(f"Admin list for chat {chat.id} is too long, attempting to send as a file.")
        try:
            import io
            file_content = "\n".join(response_lines).replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")
            file_content = file_content.replace("</a>", "").replace("✨", "").replace("🛡️", "")
            file_content = re.sub(r'<a href="[^"]*">', '', file_content)

            bio = io.BytesIO(file_content.encode('utf-8'))
            bio.name = f"admin_list_{chat.id}.txt"
            await update.message.reply_document(document=bio, caption=f"🛡️ Admin list for {chat_title_display} is too long to display directly. See the attached file.")
        except Exception as e_file:
            logger.error(f"Failed to send long admin list as file: {e_file}")
            await update.message.reply_text("Error: The admin list is too long to display, and I couldn't send it as a file.")
    else:
        await update.message.reply_html(message_text, disable_web_page_preview=True)

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_bans = update.effective_user
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't ban in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_entity: User | Chat | None = None
    args_after_target: list[str] = []

    if message.reply_to_message:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
        if context.args:
            args_after_target = context.args
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            args_after_target = context.args[1:]
        
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_entity and (target_input.isdigit() or (target_input.startswith('-') and target_input[1:].isdigit())):
            try:
                target_entity = await context.bot.get_chat(int(target_input))
            except:
                if target_input.isdigit():
                    target_entity = User(id=int(target_input), first_name="", is_bot=False)
    
    if not target_entity:
        await send_safe_reply(update, context, text="Usage: /ban <ID/@username/reply> [duration] [reason]")
        return
        
    duration_str: str | None = None
    reason: str = "No reason provided."
    if args_after_target:
        potential_duration_td = parse_duration_to_timedelta(args_after_target[0])
        if potential_duration_td:
            duration_str = args_after_target[0]
            if len(args_after_target) > 1: reason = " ".join(args_after_target[1:])
        else:
            reason = " ".join(args_after_target)
    if not reason.strip(): reason = "No reason provided."

    duration_td = parse_duration_to_timedelta(duration_str)
    until_date_for_api = datetime.now(timezone.utc) + duration_td if duration_td else None

    if target_entity.id == context.bot.id or target_entity.id == user_who_bans.id or is_privileged_user(target_entity.id):
        await send_safe_reply(update, context, text="Nuh uh... This user cannot be banned."); return

    is_user = isinstance(target_entity, User) or (isinstance(target_entity, Chat) and target_entity.type == ChatType.PRIVATE)
    is_channel = isinstance(target_entity, Chat) and target_entity.type == ChatType.CHANNEL

    if not (is_user or is_channel):
        await send_safe_reply(update, context, text="🧐 This action can only be applied to users or channels.")
        return

    if is_user:
        try:
            target_member = await context.bot.get_chat_member(chat.id, target_entity.id)
            if target_member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                await send_safe_reply(update, context, text="Chat Creator and Administrators cannot be banned.")
                return
        except TelegramError as e:
            if "user not found" not in str(e).lower():
                logger.warning(f"Could not get member status for /ban: {e}")
    
    try:
        if is_user:
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_entity.id, until_date=until_date_for_api)
        elif is_channel:
            await context.bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=target_entity.id)
        
        display_name = create_user_html_link(target_entity) if is_user else safe_escape(target_entity.title)
        
        response_lines = ["Success: User Banned"]
        response_lines.append(f"<b>• User:</b> {display_name} (<code>{target_entity.id}</code>)")
        response_lines.append(f"<b>• Reason:</b> {safe_escape(reason)}")
        
        if is_user:
            if duration_str and until_date_for_api:
                response_lines.append(f"<b>• Duration:</b> <code>{duration_str}</code> (until <code>{until_date_for_api.strftime('%Y-%m-%d %H:%M:%S %Z')}</code>)")
            else:
                response_lines.append(f"<b>• Duration:</b> <code>Permanent</code>")
        
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await send_safe_reply(update, context, text=f"Error: Failed to ban user: {safe_escape(str(e))}")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't unban in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_entity: User | Chat | None = None
    
    if message.reply_to_message:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    elif context.args:
        target_arg = context.args[0]
        target_entity = await resolve_user_with_telethon(context, target_arg, update)
        
        if not target_entity and (target_arg.isdigit() or (target_arg.startswith('-') and target_arg[1:].isdigit())):
            try:
                target_entity = await context.bot.get_chat(int(target_arg))
            except:
                if target_arg.isdigit():
                    target_entity = User(id=int(target_arg), first_name="", is_bot=False)

    else:
        await send_safe_reply(update, context, text="Usage: /unban <ID/@username/reply>")
        return

    if not target_entity:
        await send_safe_reply(update, context, text=f"Skrrrt... I can't find the user.")
        return
        
    is_user = isinstance(target_entity, User) or (isinstance(target_entity, Chat) and target_entity.type == ChatType.PRIVATE)
    is_channel = isinstance(target_entity, Chat) and target_entity.type == ChatType.CHANNEL

    if not (is_user or is_channel):
        await send_safe_reply(update, context, text="🧐 This action can only be applied to users or channels.")
        return

    try:
        if is_user:
            await context.bot.unban_chat_member(chat_id=chat.id, user_id=target_entity.id, only_if_banned=True)
        elif is_channel:
            await context.bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=target_entity.id)
        
        if is_user:
            display_name = create_user_html_link(target_entity)
        else:
            display_name = safe_escape(target_entity.title or f"Channel {target_entity.id}")

        response_lines = ["Success: User Unbanned"]
        response_lines.append(f"<b>• User:</b> {display_name} (<code>{target_entity.id}</code>)")
        
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await send_safe_reply(update, context, text=f"Failed to unban user: {safe_escape(str(e))}")

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_mutes = update.effective_user
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't mute in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    args_after_target: list[str] = []

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if context.args:
            args_after_target = context.args
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            args_after_target = context.args[1:]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in MUTE. Proceeding with ID only.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await send_safe_reply(update, context, text="Usage: /mute <ID/@username/reply> [duration] [reason]")
        return

    if not target_user:
        await send_safe_reply(update, context, text=f"Skrrrt... I can't find the user.")
        return

    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await send_safe_reply(update, context, text="🧐 Mute can only be applied to users.")
        return
        
    duration_str: str | None = None
    reason: str = "No reason provided."
    if args_after_target:
        potential_duration_td = parse_duration_to_timedelta(args_after_target[0])
        if potential_duration_td:
            duration_str = args_after_target[0]
            if len(args_after_target) > 1:
                reason = " ".join(args_after_target[1:])
        else:
            reason = " ".join(args_after_target)
    if not reason.strip(): reason = "No reason provided."

    if target_user.id == context.bot.id or target_user.id == user_who_mutes.id:
        await send_safe_reply(update, context, text="Nuh uh... This user cannot be muted."); return

    try:
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"]:
            await send_safe_reply(update, context, text="WHAT? Chat Creator and Administrators cannot be muted.")
            return
    except TelegramError as e:
        if "user not found" in str(e).lower():
            user_display = create_user_html_link(target_user)
            await send_safe_reply(update, context, text=f"User {user_display} is not in this chat, cannot be muted.", parse_mode=ParseMode.HTML)
            return
        logger.warning(f"Could not get target's chat member status for /mute: {e}")

    duration_td = parse_duration_to_timedelta(duration_str)
    permissions_to_set_for_mute = ChatPermissions(can_send_messages=False, can_send_audios=False, can_send_documents=False, can_send_photos=False, can_send_videos=False, can_send_video_notes=False, can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False, can_add_web_page_previews=False)
    until_date_dt = datetime.now(timezone.utc) + duration_td if duration_td else None

    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target_user.id, permissions=permissions_to_set_for_mute, until_date=until_date_dt, use_independent_chat_permissions=True)
        user_display_name = create_user_html_link(target_user)

        response_lines = ["Success: User Muted"]
        response_lines.append(f"<b>• User:</b> {user_display_name} (<code>{target_user.id}</code>)")
        response_lines.append(f"<b>• Reason:</b> {safe_escape(reason)}")
        if duration_str and until_date_dt:
            response_lines.append(f"<b>• Duration:</b> <code>{duration_str}</code> (until <code>{until_date_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}</code>)")
        else:
            response_lines.append(f"<b>• Duration:</b> <code>Permanent</code>")
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await send_safe_reply(update, context, text=f"Failed to mute user: {safe_escape(str(e))}")
        
async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't unmute in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in UNMUTE. Proceeding with ID only.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await send_safe_reply(update, context, text="Usage: /unmute <ID/@username/reply>")
        return

    if not target_user:
        await send_safe_reply(update, context, text=f"Skrrrt... I can't find the user.")
        return

    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await send_safe_reply(update, context, text="🧐 Unmute can only be applied to users.")
        return

    permissions_to_restore = ChatPermissions(
        can_send_messages=True, can_send_audios=True, can_send_documents=True,
        can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
        can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
        can_add_web_page_previews=True
    )

    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target_user.id, permissions=permissions_to_restore, use_independent_chat_permissions=True)
        user_display_name = create_user_html_link(target_user)
        response_lines = ["Success: User Unmuted", f"<b>• User:</b> {user_display_name} (<code>{target_user.id}</code>)"]
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await send_safe_reply(update, context, text=f"Failed to unmute user: {safe_escape(str(e))}")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_kicks = update.effective_user
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't kick in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    args_after_target: list[str] = []

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if context.args:
            args_after_target = context.args
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            args_after_target = context.args[1:]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in KICK. Proceeding with ID only.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await send_safe_reply(update, context, text="Usage: /kick <ID/@username/reply> [reason]")
        return

    if not target_user:
        await send_safe_reply(update, context, text=f"Skrrrt... I can't find the user.")
        return

    reason: str = " ".join(args_after_target) or "No reason provided."

    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await send_safe_reply(update, context, text="🧐 Kick can only be applied to users.")
        return

    if target_user.id == context.bot.id or target_user.id == user_who_kicks.id:
        await send_safe_reply(update, context, text="Nuh uh... This user cannot be kicked."); return

    try:
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"]:
            await send_safe_reply(update, context, text="WHAT? Chat Creator and Administrators cannot be kicked.")
            return
    except TelegramError as e:
        if "user not found" in str(e).lower():
            user_display = create_user_html_link(target_user)
            await send_safe_reply(update, context, text=f"User {user_display} is not in this chat, cannot be kicked.", parse_mode=ParseMode.HTML)
            return
        logger.warning(f"Could not get target's chat member status for /kick: {e}")

    try:
        await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_user.id)
        await context.bot.unban_chat_member(chat_id=chat.id, user_id=target_user.id, only_if_banned=True)

        user_display_name = create_user_html_link(target_user)
        response_lines = ["Success: User Kicked", f"<b>• User:</b> {user_display_name} (<code>{target_user.id}</code>)", f"<b>• Reason:</b> {safe_escape(reason)}"]
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await send_safe_reply(update, context, text=f"Failed to kick user: {safe_escape(str(e))}")

async def kickme_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_to_kick = update.effective_user

    if not user_to_kick:
        return

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("Huh? You can't kick yourself in private chat...")
        return

    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if not (bot_member.status == "administrator" and getattr(bot_member, 'can_restrict_members', False)):
            await update.message.reply_text("Error: I can't kick users here because I'm not an admin with ban/kick permissions 🤓.")
            return
    except TelegramError as e:
        logger.error(f"Error checking bot's own permissions in /kickme for chat {chat.id}: {e}")
        await update.message.reply_text("Error: Couldn't verify my own permissions 🤕.")
        return

    try:
        user_chat_member = await context.bot.get_chat_member(chat.id, user_to_kick.id)
        
        if user_chat_member.status == "creator":
            await update.message.reply_text("Hold Up! As the chat Creator, you must use Telegram's native 'Leave group' option.")
            return
        if user_chat_member.status == "administrator":
            await update.message.reply_text("Hold Up! As a chat Administrator, you can't use /kickme. Please use Telegram's 'Leave group' option to prevent accidental self-removal.")
            return
            
    except TelegramError as e:
        if "user not found" in str(e).lower():
            logger.warning(f"User {user_to_kick.id} not found in chat {chat.id} for /kickme, though they sent the command.")
            await update.message.reply_text("🧐 It seems you're not in this chat anymore.")
            return
        else:
            logger.error(f"Error checking your status in this chat for /kickme: {e}")
            await update.message.reply_text("Skrrrt... Couldn't verify your status in this chat to perform /kickme.")
            return

    try:
        user_display_name = create_user_html_link(user_to_kick)
        
        await update.message.reply_text(f"Done! {user_display_name}, as you wish... You have been kicked from the chat.", parse_mode=ParseMode.HTML)
        
        await context.bot.ban_chat_member(chat_id=chat.id, user_id=user_to_kick.id)
        await context.bot.unban_chat_member(chat_id=chat.id, user_id=user_to_kick.id, only_if_banned=True)
        
        logger.info(f"User {user_to_kick.id} ({user_display_name}) self-kicked from chat {chat.id} ('{chat.title}')")
        
    except TelegramError as e:
        logger.error(f"Failed to self-kick user {user_to_kick.id} from chat {chat.id}: {e}")
        await update.message.reply_text(f"Error: I tried to help you leave, but something went wrong: {safe_escape(str(e))}")
    except Exception as e:
        logger.error(f"Unexpected error in /kickme for user {user_to_kick.id}: {e}", exc_info=True)
        await update.message.reply_text("Error: An unexpected error occurred while trying to process your /kickme request.")

async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    if not message: return

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.reply_text("Huh? You can't promote in private chat....")
        return

    if not await _can_user_perform_action(update, context, 'can_promote_members', "Why should I listen to a person with no privileges for this? You need 'can_promote_members' permission.", allow_bot_privileged_override=True):
        return

    target_user: User | None = None
    args_for_title = list(context.args)

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        args_for_title = list(context.args[1:])
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in PROMOTE. Proceeding with ID only.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /promote <ID/@username/reply> [optional admin title]")
        return

    if not target_user:
        await message.reply_text(f"Skrrrt... I can't find the user..")
        return

    provided_custom_title = " ".join(args_for_title) if args_for_title else None
    
    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 Promotion can only be applied to users."); return
    if target_user.id == context.bot.id:
        await message.reply_text("Skrrrt... I'm a bot!!! I can't promote myself."); return
    if target_user.is_bot:
        await message.reply_text("Skrrrt... Bots should be promoted manually with specific rights. So... I can't help you 😱"); return

    try:
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        user_display = create_user_html_link(target_user)

        if target_chat_member.status == "creator":
            await message.reply_html(f"Huh? {user_display} is the chat Creator and cannot be managed.")
            return

        if target_chat_member.status == "administrator":
            if provided_custom_title:
                title_to_set = provided_custom_title[:16]
                await context.bot.set_chat_administrator_custom_title(chat.id, target_user.id, title_to_set)
                await message.reply_html(f"✅ User {user_display}'s title has been updated to '<i>{safe_escape(title_to_set)}</i>'.")
            else:
                await message.reply_html(f"ℹ️ User {user_display} is already an admin.")
            return

    except TelegramError as e:
        if "user not found" not in str(e).lower():
            logger.warning(f"Could not get target's chat member status for /promote: {e}")

    title_to_set = provided_custom_title[:16] if provided_custom_title else "Admin"

    try:
        await context.bot.promote_chat_member(
            chat_id=chat.id, user_id=target_user.id,
            can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
            can_restrict_members=True, can_change_info=True, can_invite_users=True,
            can_pin_messages=True, can_manage_topics=(chat.is_forum if hasattr(chat, 'is_forum') else None)
        )
        await context.bot.set_chat_administrator_custom_title(chat.id, target_user.id, title_to_set)
        
        user_display = create_user_html_link(target_user)
        await message.reply_html(f"✅ User {user_display} has been promoted with the title '<i>{safe_escape(title_to_set)}</i>'.")
    except TelegramError as e:
        await message.reply_text(f"Error: Failed to promote user: {safe_escape(str(e))}")

async def demote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    if not message: return
    
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.reply_text("Huh? You can't demote in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_promote_members', "Why should I listen to a person with no privileges for this? You need 'can_promote_members' permission.", allow_bot_privileged_override=True):
        return
    
    target_user: User | None = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in DEMOTE. Proceeding with ID only.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /demote <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text(f"Skrrrt... I can't find the user..")
        return
        
    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 Demotion can only be applied to users.")
        return
        
    if target_user.id == context.bot.id:
        await message.reply_text("Wait a minute! I can't demote myself. It's a paradox 😱.")
        return

    try:
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        user_display = create_user_html_link(target_user)

        if target_chat_member.status == "creator":
            await message.reply_html(f"WHAT? The chat Creator cannot be demoted."); return
        
        if target_chat_member.status != "administrator":
            await message.reply_html(f"ℹ️ User {user_display} is not an administrator."); return

        await context.bot.promote_chat_member(
            chat_id=chat.id, user_id=target_user.id,
            is_anonymous=False, can_manage_chat=False, can_delete_messages=False,
            can_manage_video_chats=False, can_restrict_members=False, can_promote_members=False,
            can_change_info=False, can_invite_users=False, can_pin_messages=False, can_manage_topics=False
        )
        await message.reply_html(f"✅ User {user_display} has been demoted to a regular member.")

    except TelegramError as e:
        if "user not found" in str(e).lower():
            await message.reply_text("Error: User not found in this chat.")
        else:
            logger.error(f"Error during demotion: {e}")
            await message.reply_text(f"Error: Failed to demote user. Reason: {safe_escape(str(e))}")
            
async def pin_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_pins = update.effective_user
    message_to_pin = update.message.reply_to_message

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        await update.message.reply_text("Huh? You can't pin messages in private chat...")
        return

    if not message_to_pin:
        await update.message.reply_text("Please🙏 use this command by replying to the message you want to pin.")
        return

    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if not (bot_member.status == "administrator" and getattr(bot_member, 'can_pin_messages', False)):
            await update.message.reply_text("Error: I need to be an admin with the 'can_pin_messages' permission in this chat.")
            return
    except TelegramError as e:
        logger.error(f"Error checking bot's own permissions in /pin for chat {chat.id}: {e}")
        await update.message.reply_text("Error: Couldn't verify my own permissions in this chat.")
        return
        
    if not await _can_user_perform_action(update, context, 'can_pin_messages', "Why should I listen to a person with no privileges for this? You need 'can_pin_messages' permission."):
        return

    disable_notification = True
    pin_mode_text = ""

    if context.args and context.args[0].lower() in ["loud", "notify"]:
        disable_notification = False
        pin_mode_text = " with notification"
        logger.info(f"User {user_who_pins.id} requested loud pin in chat {chat.id}")
    else:
        logger.info(f"User {user_who_pins.id} requested silent pin (default) in chat {chat.id}")


    try:
        await context.bot.pin_chat_message(
            chat_id=chat.id,
            message_id=message_to_pin.message_id,
            disable_notification=disable_notification
        )
        logger.info(f"User {user_who_pins.id} pinned message {message_to_pin.message_id} in chat {chat.id}. Notification: {'Disabled' if disable_notification else 'Enabled'}")
        
        await send_safe_reply(update, context, text=f"✅ Message pinned{pin_mode_text}!")

    except TelegramError as e:
        logger.error(f"Failed to pin message in chat {chat.id}: {e}")
        error_message = str(e)
        if "message to pin not found" in error_message.lower():
            await send_safe_reply(update, context, text="Error: I can't find the message you replied to. Maybe it was deleted?")
        elif "not enough rights" in error_message.lower() or "not admin" in error_message.lower():
             await send_safe_reply(update, context, text="Error: It seems I don't have enough rights to pin messages, or the target message cannot be pinned by me.")
        else:
            await send_safe_reply(update, context, text=f"Failed to pin message: {safe_escape(error_message)}")
    except Exception as e:
        logger.error(f"Unexpected error in /pin: {e}", exc_info=True)
        await send_safe_reply(update, context, text="An unexpected error occurred while trying to pin the message.")

async def unpin_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message_to_unpin = update.message.reply_to_message

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        await update.message.reply_text("Huh? You can't unpin messages in private chat...")
        return
        
    if not message_to_unpin:
        await update.message.reply_text("Please reply to a pinned message to unpin it.")
        return

    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if not (bot_member.status == ChatMemberStatus.ADMINISTRATOR and getattr(bot_member, 'can_pin_messages', False)):
            await update.message.reply_text("Error: I need to be an admin with 'can_pin_messages' permission in this chat.")
            return
    except TelegramError as e:
        logger.error(f"Error checking bot's own permissions in /unpin for chat {chat.id}: {e}")
        await update.message.reply_text("Error: Couldn't verify my own permissions in this chat.")
        return

    if not await _can_user_perform_action(update, context, 'can_pin_messages', "Why should I listen to a person with no privileges for this? You need 'can_pin_messages' permission."):
        return

    try:
        await context.bot.unpin_chat_message(
            chat_id=chat.id,
            message_id=message_to_unpin.message_id
        )
        await update.message.reply_text("✅ Message unpinned successfully!", quote=False)
        
    except TelegramError as e:
        logger.error(f"Failed to unpin message {message_to_unpin.message_id} in chat {chat.id}: {e}")
        error_message = str(e)
        if "message not found" in error_message.lower() or "message to unpin not found" in error_message.lower():
             await update.message.reply_text("Error: The message you replied to is not pinned or I can't find it.")
        else:
            await update.message.reply_text(f"Failed to unpin message: {safe_escape(error_message)}")
    except Exception as e:
        logger.error(f"Unexpected error in /unpin: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred while trying to unpin the message.")

async def purge_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_purges = update.effective_user
    command_message = update.message
    replied_to_message = update.message.reply_to_message

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await command_message.reply_text("Huh? You can't purge messages in private chat...")
        return

    if not replied_to_message:
        await context.bot.send_message(chat.id, "Please use this command by replying to the message up to which you want to delete (that message will also be deleted).")
        return

    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if not (bot_member.status == "administrator" and getattr(bot_member, 'can_delete_messages', False)):
            await context.bot.send_message(chat.id, "Error: I need to be an admin with the 'can_delete_messages' permission in this chat.")
            return
    except TelegramError as e:
        logger.error(f"Error checking bot's own permissions in /purge for chat {chat.id}: {e}")
        await context.bot.send_message(chat.id, "Error: Couldn't verify my own permissions in this chat.")
        return

    if not await _can_user_perform_action(update, context, 'can_delete_messages', "Why should I listen to a person with no privileges for this? You need 'can_delete_messages' permission."):
        return

    is_silent_purge = False
    if context.args and context.args[0].lower() == "silent":
        is_silent_purge = True
        logger.info(f"User {user_who_purges.id} initiated silent purge in chat {chat.id} up to message {replied_to_message.message_id}")
    else:
        logger.info(f"User {user_who_purges.id} initiated purge in chat {chat.id} up to message {replied_to_message.message_id}")

    start_message_id = replied_to_message.message_id
    end_message_id = command_message.message_id
    message_ids_to_delete = list(range(start_message_id, end_message_id + 1))

    if not message_ids_to_delete or len(message_ids_to_delete) < 1:
        if not is_silent_purge:
            await context.bot.send_message(chat.id, "No messages found between your reply and this command to delete.")
        return

    errors_occurred = False
    start_time = datetime.now()

    for i in range(0, len(message_ids_to_delete), 100):
        batch_ids = message_ids_to_delete[i:i + 100]
        try:
            success = await context.bot.delete_messages(chat_id=chat.id, message_ids=batch_ids)
            if not success:
                errors_occurred = True
                logger.warning(f"A batch purge in chat {chat.id} failed or partially failed.")
            if len(message_ids_to_delete) > 100 and i + 100 < len(message_ids_to_delete):
                await asyncio.sleep(1.1)
        except TelegramError as e:
            logger.error(f"TelegramError during purge batch in chat {chat.id}: {e}")
            errors_occurred = True
            if not is_silent_purge:
                await context.bot.send_message(chat.id, text=f"Error occurred: {safe_escape(str(e))}. Purge stopped.")
            break
        except Exception as e:
            logger.error(f"Unexpected error during purge batch in chat {chat.id}: {e}", exc_info=True)
            errors_occurred = True
            if not is_silent_purge:
                await context.bot.send_message(chat.id, text="An unexpected error occurred. Purge stopped.")
            break

    end_time = datetime.now()
    duration_secs = (end_time - start_time).total_seconds()

    if not is_silent_purge:
        final_message_text = f"✅ Purge completed in <code>{duration_secs:.2f}s</code>."
        if errors_occurred:
            final_message_text += "\nSome messages may not have been deleted (e.g., older than 48h or service messages)."

        try:
            await context.bot.send_message(chat_id=chat.id, text=final_message_text, parse_mode=ParseMode.HTML)
        except Exception as e_send_final:
            logger.error(f"Purge: Failed to send final purge status message: {e_send_final}")
    else:
        logger.info(f"Silent purge completed in chat {chat.id}. Duration: {duration_secs:.2f}s. Errors occurred: {errors_occurred}")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    reporter = update.effective_user
    message = update.message

    if not message or chat.type == ChatType.PRIVATE:
        return

    try:
        reporter_member = await chat.get_member(reporter.id)
        if reporter_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            logger.info(f"Report command ignored: used by admin {reporter.id} in chat {chat.id}.")
            return
    except TelegramError as e:
        logger.warning(f"Could not get status for reporter {reporter.id} in /report: {e}")

    target_entity: Chat | User | None = None
    args_for_reason = list(context.args)

    if message.reply_to_message:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        args_for_reason = list(context.args[1:])
        target_entity = await resolve_user_with_telethon(context, target_input, update)
    
    if not target_entity:
        return
        
    reason = " ".join(args_for_reason) if args_for_reason else "No specific reason provided."

    try:
        target_member = await chat.get_member(target_entity.id)
        if target_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            logger.info(f"Report command ignored: target {target_entity.id} is an admin in chat {chat.id}.")
            return
    except TelegramError as e:
        if "user not found" not in str(e).lower():
            logger.warning(f"Could not get status for target {target_entity.id} in /report: {e}")

    reporter_mention = create_user_html_link(reporter)
    
    if isinstance(target_entity, User) or (isinstance(target_entity, Chat) and target_entity.type == ChatType.PRIVATE):
        target_display = create_user_html_link(target_entity)
    else:
        target_display = safe_escape(target_entity.title or f"{target_entity.id}")

    report_message = (
        f"📢 <b>Report for @admins</b>\n\n"
        f"<b>Reported User:</b> {target_display} (<code>{target_entity.id}</code>)\n"
        f"<b>Reason:</b> {safe_escape(reason)}\n"
        f"<b>Reported by:</b> {reporter_mention}"
    )

    await context.bot.send_message(chat_id=chat.id, text=report_message, parse_mode=ParseMode.HTML)

    try:
        await message.delete()
    except Exception:
        logger.warning(f"Could not delete report command message in chat {chat.id}.")

async def _find_and_process_zombies(update: Update, context: ContextTypes.DEFAULT_TYPE, dry_run: bool) -> None:
    chat = update.effective_chat
    message = update.message
    telethon_client: TelegramClient = context.bot_data['telethon_client']

    action_text = "Scanning for" if dry_run else "Cleaning"
    status_message = await message.reply_html(f"🔥 <b>{action_text} deleted accounts...</b> This might take a while for large groups.")

    zombie_count = 0
    kicked_count = 0
    failed_count = 0
    
    try:
        async for member in telethon_client.iter_participants(chat.id):
            if member.deleted:
                zombie_count += 1
                
                if not dry_run:
                    try:
                        await context.bot.ban_chat_member(chat.id, member.id)
                        await context.bot.unban_chat_member(chat.id, member.id)
                        kicked_count += 1
                    except Exception as e:
                        failed_count += 1
                    
                    await asyncio.sleep(0.1)

    except Exception as e:
        await status_message.edit_text(f"An error occurred while scanning members: {safe_escape(str(e))}")
        return

    if not dry_run and kicked_count > 0:
        await asyncio.sleep(1)

    if dry_run:
        await status_message.edit_text(
            f"✅ <b>Scan complete!</b> Found <code>{zombie_count}</code> deleted accounts in this chat.\n",
            parse_mode=ParseMode.HTML
        )
    else:
        report = [f"✅ <b>Cleanup complete!</b>"]
        report.append(f"<b>• Found:</b> <code>{zombie_count}</code> deleted accounts.")
        report.append(f"<b>• Successfully kicked:</b> <code>{kicked_count}</code>.")
        if failed_count > 0:
            report.append(f"<b>• Failed to kick:</b> <code>{failed_count}</code> (likely because they are admins).")
        
        await status_message.edit_text("\n".join(report), parse_mode=ParseMode.HTML)

async def zombies_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't scan and delete zombies in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission.", allow_bot_privileged_override=True):
        return

    if 'telethon_client' not in context.bot_data:
        await update.message.reply_text("Error: This feature requires the Telethon client, which is not available.")
        return

    chat = update.effective_chat
    try:
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            await update.message.reply_text("Error: I can't clean zombies here because I'm not an administrator.")
            return
        if not bot_member.can_restrict_members:
            await update.message.reply_text("Error: I can't clean zombies here because I don't have the 'can_restrict_members' permission.")
            return
    except Exception as e:
        await update.message.reply_text(f"Skrrrt... I couldn't verify my own permissions: {e}")
        return
        
    if context.args and context.args[0].lower() == 'clean':
        await _find_and_process_zombies(update, context, dry_run=False)
    else:
        await _find_and_process_zombies(update, context, dry_run=True)

async def format_message_text(text: str, user: User, chat: Chat, context: ContextTypes.DEFAULT_TYPE) -> str:
    if not text:
        return ""
        
    full_name = user.full_name
    first_name = user.first_name
    last_name = user.last_name or first_name
    
    username_or_mention = f"@{user.username}" if user.username else user.mention_html()

    try:
        count = await context.bot.get_chat_member_count(chat.id)
    except Exception:
        count = "N/A"

    replacements = {
        "{first}": safe_escape(first_name),
        "{last}": safe_escape(last_name),
        "{fullname}": safe_escape(full_name),
        "{username}": username_or_mention,
        "{mention}": user.mention_html(),
        "{id}": str(user.id),
        "{count}": str(count),
        "{chatname}": safe_escape(chat.title or "this chat"),
    }
    
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
        
    return text

# --- Welcome/Goodbye Command Handlers ---
async def welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't manage welcome in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return

    if context.args and context.args[0].lower() in ['on', 'off']:
        is_on = context.args[0].lower() == 'on'
        try:
            with sqlite3.connect(DB_NAME) as conn:
                 conn.execute("UPDATE bot_chats SET welcome_enabled = ? WHERE chat_id = ?", (1 if is_on else 0, chat.id))
            status_text = "ENABLED" if is_on else "DISABLED"
            await update.message.reply_html(f"✅ Welcome messages have been <b>{status_text}</b>.")
        except sqlite3.Error as e:
            logger.error(f"Error toggling welcome for chat {chat.id}: {e}")
            await update.message.reply_text("An error occurred while updating the setting.")
        return

    if context.args and context.args[0].lower() == 'noformat':
        _, custom_text = get_welcome_settings(chat.id)
        if custom_text:
            await update.message.reply_text(custom_text)
        else:
            await update.message.reply_text("No custom welcome message is set for this chat.")
        return

    enabled, custom_text = get_welcome_settings(chat.id)
    status = "enabled" if enabled else "disabled"
    
    if custom_text:
        message = f"Welcome messages are currently <b>{status}</b>.\nI will be sending this custom message:\n\n"
        await update.message.reply_html(message)
        await update.message.reply_html(custom_text.format(
            first="John", last="Doe", fullname="John Doe", 
            username="@example", mention="<a href='tg://user?id=1'>John</a>", 
            id=1, count=100, chatname=chat.title
        ))
    else:
        message = f"Welcome messages are currently <b>{status}</b>.\nI will be sending one of my default welcome messages."
        await update.message.reply_html(message)

async def set_welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't set welcome message in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return

    if not context.args:
        await update.message.reply_text("You need to provide a welcome message! See /welcomehelp for formatting help.")
        return
        
    custom_text = update.message.text.split(' ', 1)[1]
    if set_welcome_setting(chat.id, enabled=True, text=custom_text):
        await update.message.reply_html("✅ Custom welcome message has been set!")
    else:
        await update.message.reply_text("Failed to set welcome message.")

async def reset_welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't reset welcome message in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return

    if set_welcome_setting(chat.id, enabled=True, text=None):
        await update.message.reply_text("✅ Welcome message has been reset to default.")
    else:
        await update.message.reply_text("Failed to reset welcome message.")

async def goodbye_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't manage goodbye in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return

    if context.args and context.args[0].lower() in ['on', 'off']:
        is_on = context.args[0].lower() == 'on'
        set_goodbye_setting(chat.id, enabled=is_on)
        status_text = "ENABLED" if is_on else "DISABLED"
        await update.message.reply_html(f"✅ Goodbye messages have been <b>{status_text}</b>.")
        return

    if context.args and context.args[0].lower() == 'noformat':
        _, custom_text = get_goodbye_settings(chat.id)
        if custom_text:
            await update.message.reply_text(custom_text)
        else:
            await update.message.reply_text("No custom goodbye message is set for this chat.")
        return

    enabled, custom_text = get_goodbye_settings(chat.id)
    status = "enabled" if enabled else "disabled"
    
    if custom_text:
        message = f"Goodbye messages are currently <b>{status}</b>.\nI will be sending this custom message:\n\n"
        await update.message.reply_html(message)
        await update.message.reply_html(custom_text.format(
            first="John", last="Doe", fullname="John Doe", 
            username="@example", mention="<a href='tg://user?id=1'>John</a>", 
            id=1, count=100, chatname=chat.title
        ))
    else:
        message = f"Goodbye messages are currently <b>{status}</b>.\nI will be sending one of my default goodbye messages."
        await update.message.reply_html(message)

async def set_goodbye_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't set goodbye message in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return

    if not context.args:
        await update.message.reply_text("You need to provide a goodbye message!")
        return
        
    custom_text = update.message.text.split(' ', 1)[1]
    if set_goodbye_setting(chat.id, enabled=True, text=custom_text):
        await update.message.reply_html("✅ Custom goodbye message has been set!")
    else:
        await update.message.reply_text("Failed to set goodbye message.")
        
async def reset_goodbye_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't reset goodbye message in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return
        
    if set_goodbye_setting(chat.id, enabled=True, text=None):
        await update.message.reply_text("✅ Goodbye message has been reset to default.")
    else:
        await update.message.reply_text("Failed to reset goodbye message.")

async def welcome_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
<b>Welcome Message Help</b>

Your group's welcome/goodbye messages can be personalised in multiple ways.

<b>Placeholders:</b>
You can use these variables in your custom messages. Each variable MUST be surrounded by `{}` to be replaced.
 • <code>{first}</code>: The user's first name.
 • <code>{last}</code>: The user's last name.
 • <code>{fullname}</code>: The user's full name.
 • <code>{username}</code>: The user's username (or a mention if they don't have one).
 • <code>{mention}</code>: A direct mention of the user.
 • <code>{id}</code>: The user's ID.
 • <code>{count}</code>: The new member count of the chat.
 • <code>{chatname}</code>: The current chat's name.

<b>Formatting:</b>
Welcome messages support html, so you can make any elements bold (&lt;b&gt;,&lt;/b&gt;) , italic (&lt;i&gt;,&lt;/i&gt;), etc.
"""
    await update.message.reply_html(help_text, disable_web_page_preview=True)

async def set_clean_service_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't set clean service in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_delete_messages', "Why should I listen to a person with no privileges for this? You need 'can_delete_messages' permission.", allow_bot_privileged_override=False):
        return

    if not context.args:
        is_enabled = should_clean_service(chat.id)
        status = "ENABLED" if is_enabled else "DISABLED"
        await update.message.reply_html(f"Automatic cleaning of service messages is currently <b>{status}</b>.")
        return

    if context.args[0].lower() not in ['on', 'off']:
        await update.message.reply_text("Usage: /cleanservice <on/off>")
        return
        
    is_on = context.args[0].lower() == 'on'
    
    if is_on:
        try:
            bot_member = await chat.get_member(context.bot.id)
            if not bot_member.can_delete_messages:
                await update.message.reply_text("I can't enable this feature because I don't have permission to delete messages in this chat.")
                return
        except Exception as e:
            logger.error(f"Failed to check permissions for cleanservice in {chat.id}: {e}")
            await update.message.reply_text("Could not verify my permissions to enable this feature.")
            return
            
    if set_clean_service(chat.id, enabled=is_on):
        status_text = "ENABLED" if is_on else "DISABLED"
        await update.message.reply_html(f"✅ Automatic cleaning of service messages has been <b>{status_text}</b>.")
    else:
        await update.message.reply_text("An error occurred while saving the setting.")

# --- Notes Command Handlers ---
async def save_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    message = update.message

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't save note in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return
        
    note_name = ""
    content = ""
    replied_message = message.reply_to_message

    if replied_message:
        if not context.args:
            await message.reply_text("You need to provide a name for the note.\nUsage: /addnote <notename> (replying to a message)")
            return
        
        note_name = context.args[0]
        content = replied_message.text_html if replied_message.text_html else replied_message.text

        if replied_message.caption:
            content = replied_message.caption_html if replied_message.caption_html else replied_message.caption

        if not content:
            await message.reply_text("The replied message doesn't seem to have any text content to save.")
            return

    else:
        if len(context.args) < 2:
            await message.reply_text("Usage:\n1. /addnote <notename> <content>\n2. Reply to a message with /addnote <notename>")
            return
            
        note_name = context.args[0]
        command_entity = message.entities[0]
        content = message.text_html[command_entity.offset + command_entity.length:].strip()
        
        if not content:
            await message.reply_text("You need to provide some content for the note.")
            return

    if add_note(chat.id, note_name, content, user.id):
        await message.reply_html(f"✅ Note <code>#{note_name.lower()}</code> has been saved.")
    else:
        await message.reply_text("Failed to save the note due to a database error.")

async def list_notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't list notes in private chat...")
        return

    notes = get_all_notes(update.effective_chat.id)
    
    if not notes:
        await update.message.reply_text("There are no notes in this chat.")
        return

    note_list = [f"<code>#{safe_escape(note)}</code>" for note in notes]
    message = "<b>Notes in this chat:</b>\n" + "\n".join(note_list)
    await update.message.reply_html(message)

async def remove_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't remove notes in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return

    if not context.args:
        await update.message.reply_text("Usage: /delnote <notename>")
        return

    note_name = context.args[0]
    if remove_note(chat.id, note_name):
        await update.message.reply_html(f"✅ Note <code>#{note_name.lower()}</code> has been removed.")
    else:
        await update.message.reply_html(f"Note <code>#{note_name.lower()}</code> not found.")

async def handle_note_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    if not text.startswith('#') or text.startswith('#/'):
        return

    note_name = text.split()[0][1:].lower()
    chat_id = update.effective_chat.id

    content = get_note(chat_id, note_name)
    if content:
        await update.message.reply_html(content, disable_web_page_preview=True)

# --- Warnings Command Handlers ---
async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    warner = update.effective_user
    message = update.message
    
    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    reason_parts: list[str] = []
    
    if message.reply_to_message:
        if not message.reply_to_message.sender_chat:
            target_user = message.reply_to_message.from_user
        reason_parts = context.args
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
        reason_parts = context.args[1:]
    
    if not target_user:
        await message.reply_text("Usage: /warn <ID/@username/reply> [reason]")
        return
    
    if not isinstance(target_user, User):
        await message.reply_text("This command can only be used on users.")
        return
        
    reason = " ".join(reason_parts) or "No reason provided."

    try:
        target_member = await context.bot.get_chat_member(chat.id, target_user.id)
        
        if target_member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            await message.reply_text("Chat Creator and Administrators cannot be warned.")
            return
    except TelegramError as e:
        if "user not found" not in str(e).lower():
            logger.warning(f"Could not get chat member status for warn target {target_user.id}: {e}")

    new_warn_id, warn_count = add_warning(chat.id, target_user.id, reason, warner.id)
    user_display = create_user_html_link(target_user)

    if new_warn_id == -1:
        await message.reply_text("A database error occurred while adding the warning.")
        return

    limit = get_warn_limit(chat.id)


    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Delete Warn", callback_data=f"undo_warn_{new_warn_id}")]]
    )

    await message.reply_html(
        f"User {user_display} (<code>{target_user.id}</code>) has been warned. ({warn_count}/{limit})\n"
        f"<b>Reason:</b> {safe_escape(reason)}",
        reply_markup=keyboard
    )

    if warn_count >= limit:
        try:
            context.bot_data.setdefault('recently_removed_users', set()).add(target_user.id)
            
            await context.bot.ban_chat_member(chat.id, target_user.id)
            await message.reply_html(
                f"🚨 User {user_display} has reached {warn_count}/{limit} warnings and has been banned."
            )
            reset_warnings(chat.id, target_user.id)
        except Exception as e:
            await message.reply_text(f"Failed to ban user after reaching max warnings: {e}")

async def undo_warn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_who_clicked = query.from_user
    
    try:
        member = await context.bot.get_chat_member(query.message.chat_id, user_who_clicked.id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await query.answer("You must be an admin to undo this action.", show_alert=True)
            return
    except Exception:
        await query.answer("Could not verify your permissions.", show_alert=True)
        return

    try:
        warn_id_to_remove = int(query.data.split("_")[2])
    except (IndexError, ValueError):
        await query.edit_message_text("Error: Invalid callback data.")
        return

    if remove_warning_by_id(warn_id_to_remove):
        new_text = query.message.text_html + "\n\n<i>(Warn deleted by " + user_who_clicked.mention_html() + ")</i>"
        await query.edit_message_text(new_text, parse_mode=ParseMode.HTML, reply_markup=None)
    else:
        await query.edit_message_text(query.message.text_html + "\n\n<i>(This warn was already deleted or could not be found.)</i>", parse_mode=ParseMode.HTML, reply_markup=None)

async def warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't check warnings in private chat...")
        return
    
    target_user: User | None = None
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        resolved_entity = await resolve_user_with_telethon(context, target_input, update)
        
        if isinstance(resolved_entity, User):
            target_user = resolved_entity
        else:
            try:
                user_id = int(target_input)
                target_user = User(id=user_id, first_name=f"User {user_id}", is_bot=False)
            except ValueError:
                pass
    else:
        target_user = update.effective_user

    if not target_user:
        await update.message.reply_text("Could not find that user. Please provide a valid User ID, @username, or reply to a message.")
        return
        
    user_warnings = get_warnings(update.effective_chat.id, target_user.id)
    user_display = create_user_html_link(target_user)
    limit = get_warn_limit(update.effective_chat.id)

    if not user_warnings:
        await update.message.reply_html(f"User {user_display} has no warnings in this chat.")
        return

    message_lines = [f"<b>Warnings for {user_display}: ({len(user_warnings)}/{limit})</b>"]
    for i, (reason, admin_id) in enumerate(user_warnings, 1):
        message_lines.append(f"\n{i}. <b>Reason:</b> {safe_escape(reason)}")
    
    await update.message.reply_html("\n".join(message_lines))

async def reset_warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't reset warnings in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
    
    if not target_user:
        await update.message.reply_text("Usage: /resetwarns <ID/@username/reply>")
        return
        
    if reset_warnings(update.effective_chat.id, target_user.id):
        user_display = create_user_html_link(target_user)
        await update.message.reply_html(f"✅ Warnings for {user_display} have been reset.")
    else:
        await update.message.reply_text("Failed to reset warnings (or user had no warnings).")

async def set_warn_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't set warning limit in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission.", allow_bot_privileged_override=False):
        return

    if not context.args:
        limit = get_warn_limit(chat.id)
        await update.message.reply_html(f"The current warning limit in this chat is <b>{limit}</b>.")
        return

    try:
        limit = int(context.args[0])
        if limit < 1:
            await update.message.reply_text("The warning limit must be at least 1.")
            return
            
        if set_warn_limit(chat.id, limit):
            await update.message.reply_html(f"✅ The warning limit for this chat has been set to <b>{limit}</b>.")
        else:
            await update.message.reply_text("Failed to set the warning limit.")
            
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    
    target_user: User | None = None
    
    if message.reply_to_message:
        if message.reply_to_message.sender_chat:
            target_chat = message.reply_to_message.sender_chat
            await message.reply_html(f"<b>The ID of {safe_escape(target_chat.title)} is:</b> <code>{target_chat.id}</code>")
            return
        else:
            target_user = message.reply_to_message.from_user

    elif context.args:
        target_input = context.args[0]
        if target_input.startswith('@'):
            resolved_entity = await resolve_user_with_telethon(context, target_input, update)
            if isinstance(resolved_entity, User):
                target_user = resolved_entity
            else:
                await message.reply_text(f"Could not find a user with the username {safe_escape(target_input)}.")
                return
        else:
            await message.reply_text("Invalid argument. Please use @username or reply to a message to get a user's ID.")
            return

    if target_user:
        await message.reply_html(f"<b>{safe_escape(target_user.first_name)}'s ID is:</b> <code>{target_user.id}</code>")
        return

    if chat.type == ChatType.PRIVATE:
        await message.reply_html(f"<b>Your ID is:</b> <code>{user.id}</code>")
    else:
        await message.reply_html(f"<b>This chat's ID is:</b> <code>{chat.id}</code>")
    
async def _handle_action_command(update, context, texts, gifs, name, req_target=True, msg=""):
    target_mention = None
    if req_target:
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
            if await check_target_protection(target.id, context):
                await update.message.reply_html(random.choice(CANT_TARGET_OWNER_TEXTS if target.id == OWNER_ID else CANT_TARGET_SELF_TEXTS)); return
            target_mention = target.mention_html()
        elif context.args and context.args[0].startswith('@'):
            target_mention = context.args[0]
            is_prot, is_owner = await check_username_protection(target_mention, context)
            if is_prot: await update.message.reply_html(random.choice(CANT_TARGET_OWNER_TEXTS if is_owner else CANT_TARGET_SELF_TEXTS)); return
        else: await update.message.reply_text(msg); return
    
    text = random.choice(texts).format(target=target_mention or "someone")
    gif_url = await get_themed_gif(context, gifs)
    try:
        if gif_url: await update.message.reply_animation(gif_url, caption=text, parse_mode=ParseMode.HTML)
        else: await update.message.reply_html(text)
    except Exception as e: logger.error(f"Error sending {name} action: {e}"); await update.message.reply_html(text)

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, KILL_TEXTS, ["gun", "gun shoting", "anime gun"], "kill", True, "Who to 'kill'?")
async def punch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, PUNCH_TEXTS, ["punch", "hit", "anime punch"], "punch", True, "Who to 'punch'?")
async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, SLAP_TEXTS, ["huge slap", "smack", "anime slap"], "slap", True, "Who to slap?")
async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, PAT_TEXTS, ["pat", "pat anime", "anime pat"], "pat", True, "Who to pat?")
async def bonk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, BONK_TEXTS, ["bonk", "anime bonk"], "bonk", True, "Who to bonk?")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /status attempt by user {user.id}.")
        return

    uptime_delta = datetime.now() - BOT_START_TIME 
    readable_uptime = get_readable_time_delta(uptime_delta)
    
    python_version = platform.python_version()
    sqlite_version = sqlite3.sqlite_version

    neofetch_output = ""
    try:
        process = await asyncio.create_subprocess_shell(
            "neofetch --stdout --config none",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if stdout:
            lines = stdout.decode('utf-8').strip().split('\n')
            filtered_lines = []
            for line in lines:
                if '---' in line or '@' in line:
                    continue
                filtered_lines.append(line)
            
            neofetch_output = "\n".join(filtered_lines)
            
        elif stderr:
            logger.warning(f"Neofetch returned an error: {stderr.decode('utf-8')}")
            neofetch_output = "Neofetch not found or failed to run. Check if you have it installed | pkg install neofetch"

    except FileNotFoundError:
        logger.warning("Neofetch command not found. Skipping.")
        neofetch_output = "Neofetch not installed."
    except Exception as e:
        logger.error(f"Error running neofetch: {e}")
        neofetch_output = "An error occurred while fetching system info."

    status_lines = [
        "<b>Bot Status:</b>",
        "<b>• State:</b> <code>Online and operational</code>",
        f"<b>• Uptime:</b> <code>{readable_uptime}</code>",
        "",
        "<b>System Info:</b>",
        f"<code>{safe_escape(neofetch_output)}</code>",
        "",
        "<b>Software Info:</b>",
        f"<b>• Python:</b> <code>{python_version}</code>",
        f"<b>• python-telegram-bot:</b> <code>{ptb_version}</code>",
        f"<b>• Telethon:</b> <code>{telethon_version}</code>",
        f"<b>• SQLite:</b> <code>{sqlite_version}</code>",
    ]

    status_msg = "\n".join(status_lines)
    await update.message.reply_html(status_msg)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /stats attempt by user {user.id}.")
        return

    known_users_count = "N/A"
    blacklisted_count = "N/A"
    developer_users_count = "N/A"
    sudo_users_count = "N/A"
    support_users_count = "N/A"
    whitelist_users_count = "N/A"
    gban_count = "N/A"
    chat_count = "N/A"

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            known_users_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM blacklist")
            blacklisted_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM dev_users")
            developer_users_count = str(cursor.fetchone()[0])
                
            cursor.execute("SELECT COUNT(*) FROM sudo_users")
            sudo_users_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM support_users")
            support_users_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM whitelist_users")
            whitelist_users_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM global_bans")
            gban_count = str(cursor.fetchone()[0])
                
            cursor.execute("SELECT COUNT(*) FROM bot_chats")
            chat_count = str(cursor.fetchone()[0])
            
    except sqlite3.Error as e:
        logger.error(f"SQLite error fetching counts for /stats: {e}", exc_info=True)
        (known_users_count, blacklisted_count, developer_users_count, sudo_users_count, 
         support_users_count, whitelist_users_count, gban_count, chat_count) = ("DB Error",) * 7

    stats_lines = [
        "<b>📊 Bot Database Stats:</b>\n",
        f" <b>• 💬 Chats:</b> <code>{chat_count}</code>",
        f" <b>• 👀 Known Users:</b> <code>{known_users_count}</code>",
        f" <b>• 🛃 Developer Users:</b> <code>{developer_users_count}</code>",
        f" <b>• 🛡 Sudo Users:</b> <code>{sudo_users_count}</code>",
        f" <b>• 👷‍♂️ Support Users:</b> <code>{support_users_count}</code>",
        f" <b>• 🔰 Whitelist Users:</b> <code>{whitelist_users_count}</code>",
        f" <b>• 🚫 Blacklisted Users:</b> <code>{blacklisted_count}</code>",
        f" <b>• 🌍 Globally Banned Users:</b> <code>{gban_count}</code>"
    ]

    stats_msg = "\n".join(stats_lines)
    await update.message.reply_html(stats_msg)

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_privileged_user(user.id):
        logger.warning(f"Unauthorized /ping attempt by user {user.id}.")
        return
    
    start_time = time.time()
    message = await update.message.reply_html("<b>Pinging...</b>")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await message.edit_text(
        f"🏓 <b>Pong!</b>\n"
        f"<b>Latency:</b> <code>{latency} ms</code>",
        parse_mode=ParseMode.HTML
    )

async def say(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /say attempt by user {user.id}.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /say <optional_chat_id> [your message]")
        return

    target_chat_id_str = args[0]
    message_to_say_list = args
    target_chat_id = update.effective_chat.id
    is_remote_send = False

    try:
        potential_chat_id = int(target_chat_id_str)
        if len(target_chat_id_str) > 5 or potential_chat_id >= -1000:
            try:
                 await context.bot.get_chat(potential_chat_id)
                 if len(args) > 1:
                     target_chat_id = potential_chat_id
                     message_to_say_list = args[1:]
                     is_remote_send = True
                     logger.info(f"Privileged user {user.id} remote send detected. Target: {target_chat_id}")
                 else:
                     await update.message.reply_text("Target chat ID provided, but no message to send.")
                     return
            except TelegramError:
                 logger.info(f"Argument '{target_chat_id_str}' looks like ID but get_chat failed or not a valid target, sending to current chat.")
                 target_chat_id = update.effective_chat.id
                 message_to_say_list = args
                 is_remote_send = False
            except Exception as e:
                 logger.error(f"Unexpected error checking potential chat ID {potential_chat_id}: {e}")
                 target_chat_id = update.effective_chat.id
                 message_to_say_list = args
                 is_remote_send = False
        else:
             logger.info("First argument doesn't look like a chat ID, sending to current chat.")
             target_chat_id = update.effective_chat.id
             message_to_say_list = args
             is_remote_send = False
    except (ValueError, IndexError):
        logger.info("First argument is not numeric, sending to current chat.")
        target_chat_id = update.effective_chat.id
        message_to_say_list = args
        is_remote_send = False

    message_to_say = ' '.join(message_to_say_list)
    if not message_to_say:
        await update.message.reply_text("Cannot send an empty message.")
        return

    chat_title = f"Chat ID {target_chat_id}"
    safe_chat_title = chat_title
    try:
        target_chat_info = await context.bot.get_chat(target_chat_id)
        chat_title = target_chat_info.title or target_chat_info.first_name or f"Chat ID {target_chat_id}"
        safe_chat_title = safe_escape(chat_title)
        logger.info(f"Target chat title for /say resolved to: '{chat_title}'")
    except TelegramError as e:
        logger.warning(f"Could not get chat info for {target_chat_id} for /say confirmation: {e}")
    except Exception as e:
         logger.error(f"Unexpected error getting chat info for {target_chat_id} in /say: {e}", exc_info=True)

    logger.info(f"Privileged user ({user.id}) using /say. Target: {target_chat_id} ('{chat_title}'). Is remote: {is_remote_send}. Msg start: '{message_to_say[:50]}...'")

    try:
        await context.bot.send_message(chat_id=target_chat_id, text=message_to_say)
        if is_remote_send:
            await update.message.reply_text(f"✅ Message sent to <b>{safe_chat_title}</b> (<code>{target_chat_id}</code>).", parse_mode=ParseMode.HTML, quote=False)
    except TelegramError as e:
        logger.error(f"Failed to send message via /say to {target_chat_id} ('{chat_title}'): {e}")
        await update.message.reply_text(f"❌ Couldn't send message to <b>{safe_chat_title}</b> (<code>{target_chat_id}</code>): {e}", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Unexpected error during /say execution: {e}", exc_info=True)
        await update.message.reply_text(f"💥 Oops! An unexpected error occurred while trying to send the message to <b>{safe_chat_title}</b> (<code>{target_chat_id}</code>). Check logs.", parse_mode=ParseMode.HTML)

async def get_gemini_response(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "AI features are not configured by the bot owner."
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error communicating with Gemini AI: {e}", exc_info=True)
        return f"Sorry, I encountered an error while communicating with the AI: {type(e).__name__}"

async def set_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    global PUBLIC_AI_ENABLED
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /setai attempt by user {user.id}.")
        return

    if not context.args or len(context.args) != 1 or context.args[0].lower() not in ['enable', 'disable']:
        await update.message.reply_text("Usage: /setai <enable/disable>")
        return

    choice = context.args[0].lower()
    
    if choice == 'enable':
        PUBLIC_AI_ENABLED = True
        status_text = "ENABLED"
    else:
        PUBLIC_AI_ENABLED = False
        status_text = "DISABLED"
    
    await update.message.reply_html(
        f"✅ Public access to <b>/askai</b> command has been globally <b>{status_text}</b>."
    )
    logger.info(f"Owner {OWNER_ID} toggled public AI access to: {status_text}")

async def ask_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    can_use_ai = False
    is_regular_user = True
    
    if is_privileged_user(user.id):
        can_use_ai = True
        is_regular_user = False
    elif PUBLIC_AI_ENABLED:
        can_use_ai = True
    
    if not can_use_ai and is_regular_user:
        await update.message.reply_html(
            "🧠 My AI brain is currently <b>DISABLED</b> by my Owner for non-SUDO users 😴\n\n"
            "Maybe try again later; ask my Owner to enable the feature, or just ask a human? 😉"
        )
        return
    elif not can_use_ai:
        return

    if not GEMINI_API_KEY:
        await update.message.reply_text("Sorry, the bot owner has not configured the AI features.")
        return
        
    if not context.args:
        await update.message.reply_text("What do you want to ask? 🤔\nUsage: /askai <your question>")
        return

    prompt = " ".join(context.args)
    
    status_message = await update.message.reply_html("🤔 <code>Thinking...</code>")
    
    try:
        ai_response_markdown = await get_gemini_response(prompt)
        
        ai_response_html = markdown_to_html(ai_response_markdown)

        if len(ai_response_html) > 4096:
             for i in range(0, len(ai_response_html), 4096):
                chunk = ai_response_html[i:i+4096]
                if i == 0:
                    await status_message.edit_text(chunk, parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
        else:
            await status_message.edit_text(ai_response_html, parse_mode=ParseMode.HTML)

    except BadRequest as e:
        logger.warning(f"HTML parsing failed for AI response: {e}. Sending as plain text.")
        await status_message.edit_text(ai_response_markdown)
    except Exception as e:
        logger.error(f"Failed to process /askai request: {e}")
        await status_message.edit_text(f"💥 Houston, we have a problem! My AI core malfunctioned: {type(e).__name__}")

async def chat_sinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays basic statistics about the current chat."""
    chat = update.effective_chat
    if not chat:
        await update.message.reply_text("Could not get chat information for some reason.")
        return

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        await update.message.reply_text("This command shows stats for groups, supergroups, or channels.")
        return

    try:
        full_chat_object = await context.bot.get_chat(chat_id=chat.id)
    except TelegramError as e:
        logger.error(f"Failed to get full chat info for /chatstats in chat {chat.id}: {e}")
        await update.message.reply_html(f"Error: Couldn't fetch detailed stats for this chat. Reason: {safe_escape(str(e))}")
        return
    except Exception as e:
        logger.error(f"Unexpected error fetching full chat info for /chatstats in chat {chat.id}: {e}", exc_info=True)
        await update.message.reply_html(f"An unexpected error occurred while fetching chat stats.")
        return

    chat_title_display = full_chat_object.title or full_chat_object.first_name or f"Chat ID {full_chat_object.id}"
    info_lines = [f"🔎 <b>Chat stats for: {safe_escape(chat_title_display)}</b>\n"]

    info_lines.append(f"<b>• ID:</b> <code>{full_chat_object.id}</code>")

    chat_description = getattr(full_chat_object, 'description', None)
    if chat_description:
        desc_preview = chat_description[:70]
        info_lines.append(f"<b>• Description:</b> {safe_escape(desc_preview)}{'...' if len(chat_description) > 70 else ''}")
    else:
        info_lines.append(f"<b>• Description:</b> Not set")
    
    if getattr(full_chat_object, 'photo', None):
        info_lines.append(f"<b>• Chat Photo:</b> <code>Yes</code>")
    else:
        info_lines.append(f"<b>• Chat Photo:</b> <code>No</code>")

    slow_mode_delay_val = getattr(full_chat_object, 'slow_mode_delay', None)
    if slow_mode_delay_val and slow_mode_delay_val > 0:
        info_lines.append(f"<b>• Slow Mode:</b> <code>Enabled</code> ({slow_mode_delay_val}s)")
    else:
        info_lines.append(f"<b>• Slow Mode:</b> <code>Disabled</code>")
    
    try:
        member_count = await context.bot.get_chat_member_count(chat_id=full_chat_object.id)
        info_lines.append(f"<b>• Total Members:</b> <code>{member_count}</code>")
    except TelegramError as e:
        logger.warning(f"Could not get member count for /chatstats in chat {full_chat_object.id}: {e}")
        info_lines.append(f"<b>• Total Members:</b> N/A (Error fetching)")
    except Exception as e:
        logger.error(f"Unexpected error in get_chat_member_count for /chatstats in {full_chat_object.id}: {e}", exc_info=True)
        info_lines.append(f"<b>• Total Members:</b> N/A (Unexpected error)")

    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        status_line = "<b>• Gban Enforcement:</b> "
        
        if not is_gban_enforced(chat.id):
            status_line += "<code>Disabled</code>"
        else:
            try:
                bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
                if bot_member.status == "administrator" and bot_member.can_restrict_members:
                    status_line += "<code>Enabled</code>"
                else:
                    status_line += "<code>Disabled</code>\n<i>Reason: Bot needs 'Ban Users' permission</i>"
            except Exception:
                status_line += "<code>Disabled</code>\n<i>Reason: Could not verify bot permissions</i>"
        
        info_lines.append(status_line)

    message_text = "\n".join(info_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

async def chat_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /cinfo attempt by user {user.id}.")
        return

    target_chat_id: int | None = None
    chat_object_for_details: Chat | None = None

    if context.args:
        try:
            target_chat_id = int(context.args[0])
            logger.info(f"Privileged user {user.id} calling /cinfo with target chat ID: {target_chat_id}")
            try:
                chat_object_for_details = await context.bot.get_chat(chat_id=target_chat_id)
            except TelegramError as e:
                logger.error(f"Failed to get chat info for ID {target_chat_id}: {e}")
                await update.message.reply_html(f"Error: Couldn't fetch info for chat ID <code>{target_chat_id}</code>. Reason: {safe_escape(str(e))}.")
                return
            except Exception as e:
                logger.error(f"Unexpected error fetching chat info for ID {target_chat_id}: {e}", exc_info=True)
                await update.message.reply_html(f"An unexpected error occurred trying to get info for chat ID <code>{target_chat_id}</code>.")
                return
        except ValueError:
            await update.message.reply_text("Invalid chat ID format. Please provide a numeric ID.")
            return
    else:
        effective_chat_obj = update.effective_chat
        if effective_chat_obj:
             target_chat_id = effective_chat_obj.id
             try:
                 chat_object_for_details = await context.bot.get_chat(chat_id=target_chat_id)
                 logger.info(f"Privileged user {user.id} calling /cinfo for current chat: {target_chat_id}")
             except TelegramError as e:
                logger.error(f"Failed to get full chat info for current chat ID {target_chat_id}: {e}")
                await update.message.reply_html(f"Error: Couldn't fetch full info for current chat. Reason: {safe_escape(str(e))}.")
                return
             except Exception as e:
                logger.error(f"Unexpected error fetching full info for current chat ID {target_chat_id}: {e}", exc_info=True)
                await update.message.reply_html(f"An unexpected error occurred trying to get full info for current chat.")
                return
        else:
             await update.message.reply_text("Could not determine current chat.")
             return

    if not chat_object_for_details or target_chat_id is None:
        await update.message.reply_text("Couldn't determine the chat to inspect.")
        return

    if chat_object_for_details.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        await update.message.reply_text("This command provides info about groups, supergroups, or channels.")
        return

    bot_id = context.bot.id
    chat_title_display = chat_object_for_details.title or chat_object_for_details.first_name or f"Chat ID {target_chat_id}"
    info_lines = [f"🔎 <b>Chat Information for: {safe_escape(chat_title_display)}</b>\n"]

    info_lines.append(f"<b>• ID:</b> <code>{target_chat_id}</code>")
    info_lines.append(f"<b>• Type:</b> {chat_object_for_details.type.capitalize()}")

    chat_description = getattr(chat_object_for_details, 'description', None)
    if chat_description:
        desc_preview = chat_description[:200]
        info_lines.append(f"<b>• Description:</b> {safe_escape(desc_preview)}{'...' if len(chat_description) > 200 else ''}")
    
    if getattr(chat_object_for_details, 'photo', None):
        info_lines.append(f"<b>• Chat Photo:</b> Yes")
    else:
        info_lines.append(f"<b>• Chat Photo:</b> No")

    chat_link_line = ""
    if chat_object_for_details.username:
        chat_link = f"https://t.me/{chat_object_for_details.username}"
        chat_link_line = f"<b>• Link:</b> <a href=\"{chat_link}\">@{chat_object_for_details.username}</a>"
    elif chat_object_for_details.type != ChatType.CHANNEL:
        try:
            bot_member = await context.bot.get_chat_member(chat_id=target_chat_id, user_id=bot_id)
            if bot_member.status == "administrator" and bot_member.can_invite_users:
                link_name = f"cinfo_{str(target_chat_id)[-5:]}_{random.randint(100,999)}"
                invite_link_obj = await context.bot.create_chat_invite_link(chat_id=target_chat_id, name=link_name)
                chat_link_line = f"<b>• Generated Invite Link:</b> {invite_link_obj.invite_link} (temporary)"
            else:
                chat_link_line = "<b>• Link:</b> Private group (no public link, bot cannot generate one)"
        except TelegramError as e:
            logger.warning(f"Could not create/check invite link for private chat {target_chat_id}: {e}")
            chat_link_line = f"<b>• Link:</b> Private group (no public link, error: {safe_escape(str(e))})"
        except Exception as e:
            logger.error(f"Unexpected error with invite link for {target_chat_id}: {e}", exc_info=True)
            chat_link_line = "<b>• Link:</b> Private group (no public link, unexpected error)"
    else:
        chat_link_line = "<b>• Link:</b> Private channel (no public/invite link via bot)"
    info_lines.append(chat_link_line)

    pinned_message_obj = getattr(chat_object_for_details, 'pinned_message', None)
    if pinned_message_obj:
        pin_text_preview = pinned_message_obj.text or pinned_message_obj.caption or "[Media/No Text]"
        pin_link = "#" 
        if chat_object_for_details.username:
             pin_link = f"https://t.me/{chat_object_for_details.username}/{pinned_message_obj.message_id}"
        elif str(target_chat_id).startswith("-100"):
             chat_id_for_link = str(target_chat_id).replace("-100","")
             pin_link = f"https://t.me/c/{chat_id_for_link}/{pinned_message_obj.message_id}"
        info_lines.append(f"<b>• Pinned Message:</b> <a href=\"{pin_link}\">'{safe_escape(pin_text_preview[:50])}{'...' if len(pin_text_preview) > 50 else ''}'</a>")
    
    linked_chat_id_val = getattr(chat_object_for_details, 'linked_chat_id', None)
    if linked_chat_id_val:
        info_lines.append(f"<b>• Linked Chat ID:</b> <code>{linked_chat_id_val}</code>")
    
    slow_mode_delay_val = getattr(chat_object_for_details, 'slow_mode_delay', None)
    if slow_mode_delay_val and slow_mode_delay_val > 0:
        info_lines.append(f"<b>• Slow Mode:</b> Enabled ({slow_mode_delay_val}s)")

    member_count_val: int | str = "N/A"; admin_count_val: int | str = 0
    try:
        member_count_val = await context.bot.get_chat_member_count(chat_id=target_chat_id)
        info_lines.append(f"<b>• Total Members:</b> {member_count_val}")
    except Exception as e:
        logger.error(f"Error get_chat_member_count for {target_chat_id}: {e}")
        info_lines.append(f"<b>• Total Members:</b> Error fetching")

    admin_list_str_parts = ["<b>• Administrators:</b>"]
    admin_details_list = []
    try:
        administrators = await context.bot.get_chat_administrators(chat_id=target_chat_id)
        admin_count_val = len(administrators)
        admin_list_str_parts.append(f"  <b>• Total:</b> {admin_count_val}")
        for admin_member in administrators:
            admin_user = admin_member.user
            admin_name_display = f"ID: {admin_user.id if admin_user else 'N/A'}"
            if admin_user:
                admin_name_display = admin_user.mention_html() if admin_user.username else safe_escape(admin_user.full_name or admin_user.first_name or f"ID: {admin_user.id}")
            detail_line = f"    • {admin_name_display}"
            current_admin_status_str = getattr(admin_member, 'status', None)
            if current_admin_status_str == "creator":
                detail_line += " (Creator 👑)"
            admin_details_list.append(detail_line)
        if admin_details_list:
            admin_list_str_parts.append("  <b>• List:</b>")
            admin_list_str_parts.extend(admin_details_list)
    except Exception as e:
        admin_list_str_parts.append("  <b>• Error fetching admin list.</b>")
        admin_count_val = "Error"
        logger.error(f"Error get_chat_administrators for {target_chat_id}: {e}", exc_info=True)
    info_lines.append("\n".join(admin_list_str_parts))

    if isinstance(member_count_val, int) and isinstance(admin_count_val, int) and admin_count_val >=0:
         other_members_count = member_count_val - admin_count_val
         info_lines.append(f"<b>• Other Members:</b> {other_members_count if other_members_count >= 0 else 'N/A'}")

    bot_status_lines = ["\n<b>• Bot Status in this Chat:</b>"]
    try:
        bot_member_on_chat = await context.bot.get_chat_member(chat_id=target_chat_id, user_id=bot_id)
        bot_current_status_str = bot_member_on_chat.status
        bot_status_lines.append(f"  <b>• Status:</b> {bot_current_status_str.capitalize()}")
        if bot_current_status_str == "administrator":
            bot_status_lines.append(f"  <b>• Can invite users:</b> {'Yes' if bot_member_on_chat.can_invite_users else 'No'}")
            bot_status_lines.append(f"  <b>• Can restrict members:</b> {'Yes' if bot_member_on_chat.can_restrict_members else 'No'}")
            bot_status_lines.append(f"  <b>• Can pin messages:</b> {'Yes' if getattr(bot_member_on_chat, 'can_pin_messages', None) else 'No'}")
            bot_status_lines.append(f"  <b>• Can manage chat:</b> {'Yes' if getattr(bot_member_on_chat, 'can_manage_chat', None) else 'No'}")
        else:
            bot_status_lines.append("  <b>• Note:</b> Bot is not an admin here.")
    except TelegramError as e:
        if "user not found" in str(e).lower() or "member not found" in str(e).lower():
             bot_status_lines.append("  <b>• Status:</b> Not a member")
        else:
            bot_status_lines.append(f"  <b>• Error fetching bot status:</b> {safe_escape(str(e))}")
    except Exception as e:
        bot_status_lines.append("  <b>• Unexpected error fetching bot status.")
        logger.error(f"Unexpected error getting bot status in {target_chat_id}: {e}", exc_info=True)
    info_lines.append("\n".join(bot_status_lines))
    
    chat_permissions = getattr(chat_object_for_details, 'permissions', None)
    if chat_permissions:
        perms = chat_permissions
        perm_lines = ["\n<b>• Default Member Permissions:</b>"]
        perm_lines.append(f"  <b>• Send Messages:</b> {'Yes' if getattr(perms, 'can_send_messages', False) else 'No'}")
        
        can_send_any_media = (
            getattr(perms, 'can_send_audios', False) or
            getattr(perms, 'can_send_documents', False) or
            getattr(perms, 'can_send_photos', False) or 
            getattr(perms, 'can_send_videos', False) or
            getattr(perms, 'can_send_video_notes', False) or
            getattr(perms, 'can_send_voice_notes', False) or
            getattr(perms, 'can_send_media_messages', False)
        )
        perm_lines.append(f"  <b>• Send Media:</b> {'Yes' if can_send_any_media else 'No'}")
        perm_lines.append(f"  <b>• Send Polls:</b> {'Yes' if getattr(perms, 'can_send_polls', False) else 'No'}")
        perm_lines.append(f"  <b>• Send Other Messages:</b> {'Yes' if getattr(perms, 'can_send_other_messages', False) else 'No'}")
        perm_lines.append(f"  <b>• Add Web Page Previews:</b> {'Yes' if getattr(perms, 'can_add_web_page_previews', False) else 'No'}")
        perm_lines.append(f"  <b>• Change Info:</b> {'Yes' if getattr(perms, 'can_change_info', False) else 'No'}")
        perm_lines.append(f"  <b>• Invite Users:</b> {'Yes' if getattr(perms, 'can_invite_users', False) else 'No'}")
        perm_lines.append(f"  <b>• Pin Messages:</b> {'Yes' if getattr(perms, 'can_pin_messages', False) else 'No'}")
        if hasattr(perms, 'can_manage_topics'):
            perm_lines.append(f"  <b>• Manage Topics:</b> {'Yes' if perms.can_manage_topics else 'No'}")
        info_lines.extend(perm_lines)

    message_text = "\n".join(info_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

def run_speed_test_blocking():
    try:
        logger.info("Starting blocking speed test...")
        s = speedtest.Speedtest()
        s.get_best_server()
        logger.info("Getting download speed...")
        s.download()
        logger.info("Getting upload speed...")
        s.upload()
        results_dict = s.results.dict()
        logger.info("Speed test finished successfully (blocking part).")
        return results_dict
    except speedtest.ConfigRetrievalError as e:
        logger.error(f"Speedtest config retrieval error: {e}")
        return {"error": f"Config retrieval error: {str(e)}"}
    except speedtest.NoMatchedServers as e:
        logger.error(f"Speedtest no matched servers: {e}")
        return {"error": f"No suitable test servers found: {str(e)}"}
    except Exception as e:
        logger.error(f"General error during blocking speedtest function: {e}", exc_info=True)
        return {"error": f"A general error occurred during test: {type(e).__name__}"}

async def speedtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /speedtest attempt by user {user.id}.")
        return

    message = await update.message.reply_text("Starting speed test... this might take a moment.")
    
    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, run_speed_test_blocking)
        await asyncio.sleep(4)

        if results and "error" not in results:
            ping_val = results.get("ping", 0.0)
            download_bps = results.get("download", 0)
            upload_bps = results.get("upload", 0)
            
            download_mbps_val = download_bps / 1000 / 1000
            upload_mbps_val = upload_bps / 1000 / 1000

            bytes_sent_val = results.get("bytes_sent", 0)
            bytes_received_val = results.get("bytes_received", 0)
            data_sent_mb_val = bytes_sent_val / 1024 / 1024
            data_received_mb_val = bytes_received_val / 1024 / 1024
            
            timestamp_str_val = results.get("timestamp", "N/A")
            formatted_time_val = "N/A"
            if timestamp_str_val != "N/A":
                try:
                    dt_obj = datetime.fromisoformat(timestamp_str_val.replace("Z", "+00:00"))
                    formatted_time_val = dt_obj.strftime('%Y-%m-%d %H:%M:%S %Z') 
                except ValueError:
                    formatted_time_val = safe_escape(timestamp_str_val)

            server_info_dict = results.get("server", {})
            server_name_val = server_info_dict.get("name", "N/A")
            server_country_val = server_info_dict.get("country", "N/A")
            server_cc_val = server_info_dict.get("cc", "N/A")
            server_sponsor_val = server_info_dict.get("sponsor", "N/A")
            server_lat_val = server_info_dict.get("lat", "N/A")
            server_lon_val = server_info_dict.get("lon", "N/A")

            info_lines = [
                "<b>🌐 Ookla SPEEDTEST:</b>\n",
                "<b>📊 RESULTS:</b>",
                f" <b>• 📤 Upload:</b> <code>{upload_mbps_val:.2f} Mbps</code>",
                f" <b>• 📥 Download:</b> <code>{download_mbps_val:.2f} Mbps</code>",
                f" <b>• ⏳️ Ping:</b> <code>{ping_val:.2f} ms</code>",
                f" <b>• 🕒 Time:</b> <code>{formatted_time_val}</code>",
                f" <b>• 📨 Data Sent:</b> <code>{data_sent_mb_val:.2f} MB</code>",
                f" <b>• 📩 Data Received:</b> <code>{data_received_mb_val:.2f} MB</code>\n",
                "<b>🖥 SERVER INFO:</b>",
                f" <b>• 🪪 Name:</b> <code>{safe_escape(server_name_val)}</code>",
                f" <b>• 🌍 Country:</b> <code>{safe_escape(server_country_val)} ({safe_escape(server_cc_val)})</code>",
                f" <b>• 🛠 Sponsor:</b> <code>{safe_escape(server_sponsor_val)}</code>",
                f" <b>• 🧭 Latitude:</b> <code>{server_lat_val}</code>",
                f" <b>• 🧭 Longitude:</b> <code>{server_lon_val}</code>"
            ]
            
            result_message = "\n".join(info_lines)
            await context.bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text=result_message, parse_mode=ParseMode.HTML)
        
        elif results and "error" in results:
            error_msg = results["error"]
            await context.bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text=f"Error: Speed test failed: {safe_escape(error_msg)}")
        else:
            await context.bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text="Error: Speed test failed to return results or returned an unexpected format.")

    except Exception as e:
        logger.error(f"Error in speedtest_command outer try-except: {e}", exc_info=True)
        try:
            await context.bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text=f"An unexpected error occurred during the speed test: {safe_escape(str(e))}")
        except Exception:
            pass

async def leave_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /leave attempt by user {user.id}.")
        return

    target_chat_id_to_leave: int | None = None
    chat_where_command_was_called_id = update.effective_chat.id
    is_leaving_current_chat = False

    if context.args:
        try:
            target_chat_id_to_leave = int(context.args[0])
            if target_chat_id_to_leave >= -100:
                await update.message.reply_text("Invalid Group/Channel ID format for leaving.")
                return
            logger.info(f"Privileged user {user.id} initiated remote leave for chat ID: {target_chat_id_to_leave}")
            if target_chat_id_to_leave == chat_where_command_was_called_id:
                is_leaving_current_chat = True
        except (ValueError, IndexError):
            await update.message.reply_text("Invalid chat ID format for leaving.")
            return
    else:
        if update.effective_chat.type == ChatType.PRIVATE:
            await update.message.reply_text("I can't leave a private chat.")
            return
        target_chat_id_to_leave = update.effective_chat.id
        is_leaving_current_chat = True
        logger.info(f"Privileged user {user.id} initiated leave for current chat: {target_chat_id_to_leave}")

    if target_chat_id_to_leave is None:
        await update.message.reply_text("Could not determine which chat to leave.")
        return

    owner_mention_for_farewell = f"<code>{OWNER_ID}</code>"
    try:
        owner_chat_info = await context.bot.get_chat(OWNER_ID)
        owner_mention_for_farewell = owner_chat_info.mention_html()
    except Exception as e:
        logger.warning(f"Could not fetch owner mention for /leave farewell message: {e}")

    chat_title_to_leave = f"Chat ID {target_chat_id_to_leave}"
    safe_chat_title_to_leave = chat_title_to_leave
    
    try:
        target_chat_info = await context.bot.get_chat(target_chat_id_to_leave)
        chat_title_to_leave = target_chat_info.title or target_chat_info.first_name or f"Chat ID {target_chat_id_to_leave}"
        safe_chat_title_to_leave = safe_escape(chat_title_to_leave)
    except TelegramError as e:
        logger.error(f"Could not get chat info for {target_chat_id_to_leave} before leaving: {e}")
        reply_to_chat_id_for_error = chat_where_command_was_called_id
        if is_leaving_current_chat and OWNER_ID: reply_to_chat_id_for_error = OWNER_ID
        
        error_message_text = f"❌ Cannot interact with chat <b>{safe_chat_title_to_leave}</b> (<code>{target_chat_id_to_leave}</code>): {safe_escape(str(e))}. I might not be a member there."
        if "bot is not a member" in str(e).lower() or "chat not found" in str(e).lower():
            pass 
        else:
            error_message_text = f"⚠️ Couldn't get chat info for <code>{target_chat_id_to_leave}</code>: {safe_escape(str(e))}. Will attempt to leave anyway."
        
        if reply_to_chat_id_for_error:
            try: await context.bot.send_message(chat_id=reply_to_chat_id_for_error, text=error_message_text, parse_mode=ParseMode.HTML)
            except Exception as send_err: logger.error(f"Failed to send error about get_chat to {reply_to_chat_id_for_error}: {send_err}")
        if "bot is not a member" in str(e).lower() or "chat not found" in str(e).lower(): return
        
    except Exception as e:
         logger.error(f"Unexpected error getting chat info for {target_chat_id_to_leave}: {e}", exc_info=True)
         reply_to_chat_id_for_error = chat_where_command_was_called_id
         if is_leaving_current_chat and OWNER_ID: reply_to_chat_id_for_error = OWNER_ID
         if reply_to_chat_id_for_error:
             try: await context.bot.send_message(chat_id=reply_to_chat_id_for_error, text=f"⚠️ Unexpected error getting chat info for <code>{target_chat_id_to_leave}</code>. Will attempt to leave anyway.", parse_mode=ParseMode.HTML)
             except Exception as send_err: logger.error(f"Failed to send error about get_chat to {reply_to_chat_id_for_error}: {send_err}")

    if LEAVE_TEXTS:
        farewell_message = random.choice(LEAVE_TEXTS).format(owner_mention=owner_mention_for_farewell, chat_title=f"<b>{safe_chat_title_to_leave}</b>")
        try:
            await context.bot.send_message(chat_id=target_chat_id_to_leave, text=farewell_message, parse_mode=ParseMode.HTML)
            logger.info(f"Sent farewell message to {target_chat_id_to_leave}")
        except TelegramError as e:
            logger.error(f"Failed to send farewell message to {target_chat_id_to_leave}: {e}.")
            if "forbidden: bot is not a member" in str(e).lower() or "chat not found" in str(e).lower():
                logger.warning(f"Bot is not a member of {target_chat_id_to_leave} or chat not found. Cannot send farewell.")
                reply_to_chat_id_for_error = chat_where_command_was_called_id
                if is_leaving_current_chat and OWNER_ID: reply_to_chat_id_for_error = OWNER_ID
                if reply_to_chat_id_for_error:
                    try: await context.bot.send_message(chat_id=reply_to_chat_id_for_error, text=f"❌ Failed to send farewell to <b>{safe_chat_title_to_leave}</b> (<code>{target_chat_id_to_leave}</code>): {safe_escape(str(e))}. Bot is not a member.", parse_mode=ParseMode.HTML)
                    except Exception as send_err: logger.error(f"Failed to send error about farewell to {reply_to_chat_id_for_error}: {send_err}")
                return 
        except Exception as e:
             logger.error(f"Unexpected error sending farewell message to {target_chat_id_to_leave}: {e}", exc_info=True)
    elif not LEAVE_TEXTS:
        logger.warning("LEAVE_TEXTS list is empty! Skipping farewell message.")

    try:
        success = await context.bot.leave_chat(chat_id=target_chat_id_to_leave)
        
        confirmation_target_chat_id = chat_where_command_was_called_id
        if is_leaving_current_chat:
            if OWNER_ID:
                confirmation_target_chat_id = OWNER_ID
            else:
                confirmation_target_chat_id = None 

        if success:
            logger.info(f"Successfully left chat {target_chat_id_to_leave} ('{chat_title_to_leave}')")
            if confirmation_target_chat_id:
                await context.bot.send_message(chat_id=confirmation_target_chat_id, 
                                               text=f"✅ Successfully left chat: <b>{safe_chat_title_to_leave}</b> (<code>{target_chat_id_to_leave}</code>)", 
                                               parse_mode=ParseMode.HTML)
        else:
            logger.warning(f"leave_chat returned False for {target_chat_id_to_leave}. Bot might not have been a member.")
            if confirmation_target_chat_id:
                await context.bot.send_message(chat_id=confirmation_target_chat_id,
                                               text=f"🤔 Attempted to leave <b>{safe_chat_title_to_leave}</b> (<code>{target_chat_id_to_leave}</code>), but the operation indicated I might not have been there or lacked permission.", 
                                               parse_mode=ParseMode.HTML)
    except TelegramError as e:
        logger.error(f"Failed to leave chat {target_chat_id_to_leave}: {e}")
        confirmation_target_chat_id = chat_where_command_was_called_id
        if is_leaving_current_chat:
            if OWNER_ID: confirmation_target_chat_id = OWNER_ID
            else: confirmation_target_chat_id = None
        if confirmation_target_chat_id:
            await context.bot.send_message(chat_id=confirmation_target_chat_id,
                                           text=f"❌ Failed to leave chat <b>{safe_chat_title_to_leave}</b> (<code>{target_chat_id_to_leave}</code>): {safe_escape(str(e))}", 
                                           parse_mode=ParseMode.HTML)
    except Exception as e:
         logger.error(f"Unexpected error during leave process for {target_chat_id_to_leave}: {e}", exc_info=True)
         confirmation_target_chat_id = chat_where_command_was_called_id
         if is_leaving_current_chat:
            if OWNER_ID: confirmation_target_chat_id = OWNER_ID
            else: confirmation_target_chat_id = None
         if confirmation_target_chat_id:
            await context.bot.send_message(chat_id=confirmation_target_chat_id,
                                           text=f"💥 Unexpected error leaving chat <b>{safe_chat_title_to_leave}</b> (<code>{target_chat_id_to_leave}</code>). Check logs.", 
                                           parse_mode=ParseMode.HTML)

async def handle_new_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.new_chat_members:
        return
    chat = update.effective_chat
    
    if any(member.id == context.bot.id for member in update.message.new_chat_members):
        logger.info(f"Bot joined chat: {chat.title} ({chat.id})")
        add_chat_to_db(chat.id, chat.title or f"Untitled Chat {chat.id}")
        if OWNER_ID:
            safe_chat_title = html.escape(chat.title or f"Chat ID {chat.id}")
            link_line = f"\n<b>Link:</b> @{chat.username}" if chat.username else ""
            pm_text = (f"<b>#ADDEDTOGROUP</b>\n\n<b>Name:</b> {safe_chat_title}\n<b>ID:</b> <code>{chat.id}</code>{link_line}")
            try:
                await context.bot.send_message(chat_id=OWNER_ID, text=pm_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to send join notification to owner for group {chat.id}: {e}")
        try:
            bot_username = context.bot.username
            
            welcome_message_to_group = (
                f"👋 Hello! I'm <b>Zenthron</b>, your new group assistant.\n\n"
                f"I'm here to help you manage the chat and have some fun. "
                f"To see what I can do, click button 'Get Help in PM'.\n\n"
                f"I was added by {update.message.from_user.mention_html()}.\n"
                f"<i>I'm Still a Work In Progress [WIP]. Various bugs and security holes may appear for which Bot creators are not responsible [You add at your own risk]. For any questions or issues, please contact our support team at {APPEAL_CHAT_USERNAME}.</i>"
            )
            
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="📬 Get Help in PM", url=f"https://t.me/{bot_username}?start=help")]]
            )

            await context.bot.send_message(
                chat_id=chat.id,
                text=welcome_message_to_group,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send introduction message to new group {chat.id}: {e}")
        return

    welcome_enabled, custom_text = get_welcome_settings(chat.id)

    for member in update.message.new_chat_members:
        base_text = ""
        is_privileged_join = True

        if member.id == OWNER_ID and OWNER_WELCOME_TEXTS:
            base_text = random.choice(OWNER_WELCOME_TEXTS)
        elif is_dev_user(member.id) and DEV_WELCOME_TEXTS:
            base_text = random.choice(DEV_WELCOME_TEXTS)
        elif is_sudo_user(member.id) and SUDO_WELCOME_TEXTS:
            base_text = random.choice(SUDO_WELCOME_TEXTS)
        elif is_support_user(member.id) and SUPPORT_WELCOME_TEXTS:
            base_text = random.choice(SUPPORT_WELCOME_TEXTS)
        else:
            is_privileged_join = False

        if not is_privileged_join:
            if not welcome_enabled:
                continue
            
            if custom_text:
                base_text = custom_text
            elif GENERIC_WELCOME_TEXTS:
                base_text = random.choice(GENERIC_WELCOME_TEXTS)
        
        if not base_text:
            continue

        user_mention = member.mention_html()
        owner_mention = f"<code>{OWNER_ID}</code>"
        if OWNER_ID:
            try:
                owner_chat = await context.bot.get_chat(OWNER_ID)
                owner_mention = owner_chat.mention_html()
            except Exception:
                pass
        
        try:
            count = await context.bot.get_chat_member_count(chat.id)
        except Exception:
            count = "N/A"

        final_message = base_text.format(
            first=safe_escape(member.first_name),
            last=safe_escape(member.last_name or member.first_name),
            fullname=safe_escape(member.full_name),
            username=f"@{member.username}" if member.username else user_mention,
            mention=user_mention,
            user_mention=user_mention,
            owner_mention=owner_mention,
            id=member.id,
            count=count,
            chatname=safe_escape(chat.title or "this chat")
        )

        if final_message:
            try:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=final_message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Failed to send welcome message for user {member.id} in chat {chat.id}: {e}")

    if should_clean_service(chat.id):
        try:
            await update.message.delete()
        except Exception:
            pass
            
async def handle_left_group_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.left_chat_member:
        return
    
    chat = update.effective_chat
    left_member = update.message.left_chat_member

    if left_member.id == context.bot.id:
        logger.info(f"Bot removed from group cache {chat.id}.")
        remove_chat_from_db(chat.id)
        return

    if should_clean_service(chat.id):
        try:
            await update.message.delete()
        except Exception:
            pass

    is_enabled, custom_text = get_goodbye_settings(chat.id)
    if not is_enabled:
        return

    base_text = ""
    if custom_text:
        base_text = custom_text
    elif GENERIC_GOODBYE_TEXTS:
        user_mention = left_member.mention_html()
        base_text = random.choice(GENERIC_GOODBYE_TEXTS).format(user_mention=user_mention)
    
    if base_text:
        final_message = await format_message_text(base_text, left_member, chat, context)
        if final_message:
            try:
                await context.bot.send_message(chat.id, final_message, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to send goodbye message in chat {chat.id}: {e}")

async def send_operational_log(context: ContextTypes.DEFAULT_TYPE, message: str, parse_mode: str = ParseMode.HTML) -> None:
    """
    Sends an operational log message to LOG_CHAT_ID if configured,
    otherwise falls back to OWNER_ID.
    """
    target_id_for_log = LOG_CHAT_ID

    if not target_id_for_log and OWNER_ID:
        target_id_for_log = OWNER_ID
        logger.info("LOG_CHAT_ID not set, sending operational log to OWNER_ID.")
    elif not target_id_for_log and not OWNER_ID:
        logger.error("Neither LOG_CHAT_ID nor OWNER_ID are set. Cannot send operational log.")
        return

    if target_id_for_log:
        try:
            await context.bot.send_message(chat_id=target_id_for_log, text=message, parse_mode=parse_mode)
            logger.info(f"Sent operational log to chat_id: {target_id_for_log}")
        except TelegramError as e:
            logger.error(f"Failed to send operational log to {target_id_for_log}: {e}")
            if LOG_CHAT_ID and target_id_for_log == LOG_CHAT_ID and OWNER_ID and LOG_CHAT_ID != OWNER_ID:
                logger.info(f"Falling back to send operational log to OWNER_ID ({OWNER_ID}) after failure with LOG_CHAT_ID.")
                try:
                    await context.bot.send_message(chat_id=OWNER_ID, text=f"[Fallback from LogChat]\n{message}", parse_mode=parse_mode)
                    logger.info(f"Sent operational log to OWNER_ID as fallback.")
                except Exception as e_owner:
                    logger.error(f"Failed to send operational log to OWNER_ID as fallback: {e_owner}")
        except Exception as e:
            logger.error(f"Unexpected error sending operational log to {target_id_for_log}: {e}", exc_info=True)

async def blacklist_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /blist attempt by user {user.id}.")
        return

    target_entity: User | Chat | None = None
    reason: str = "No reason provided."

    if message.reply_to_message:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
        if context.args:
            reason = " ".join(context.args)
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            reason = " ".join(context.args[1:])
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        if not target_entity and target_input.isdigit():
            target_entity = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /blist <ID/@username/reply> [reason]"); return
    
    if not target_entity:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    if isinstance(target_entity, Chat) and target_entity.type != ChatType.PRIVATE:
        await message.reply_text("🧐 This action can only be applied to users.")
        return
    if is_privileged_user(target_entity.id) or target_entity.id == context.bot.id:
        await message.reply_text("LoL, looks like... Someone tried blacklist privileged user. Nice Try.")
        return
    if is_whitelisted(target_entity.id):
        await message.reply_text("This user is on the whitelist and cannot be blacklisted.")
        return

    user_display = create_user_html_link(target_entity)

    existing_blist_reason = get_blacklist_reason(target_entity.id)
    if existing_blist_reason:
        await message.reply_html(
            f"ℹ️ User {user_display} (<code>{target_entity.id}</code>) is already on the blacklist.\n"
            f"<b>Reason:</b> {safe_escape(existing_blist_reason)}"
        )
        return

    if add_to_blacklist(target_entity.id, user.id, reason):
        user_display = create_user_html_link(target_entity)
        await message.reply_html(f"✅ User {user_display} (<code>{target_entity.id}</code>) has been added to the blacklist.\n<b>Reason:</b> {safe_escape(reason)}")
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_user_display = create_user_html_link(target_entity)
            admin_link = create_user_html_link(user)

            pm_message = (
                f"<b>#BLACKLISTED</b>\n\n"
                f"<b>User:</b> {log_user_display}\n"
                f"<b>User ID:</b> <code>{target_entity.id}</code>\n"
                f"<b>Reason:</b> {safe_escape(reason)}\n"
                f"<b>Admin:</b> {admin_link}\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, pm_message)
        except Exception as e:
            logger.error(f"Error preparing/sending #BLACKLISTED operational log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to the blacklist. Check logs.")

async def unblacklist_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /unblist attempt by user {user.id}.")
        return

    target_entity: User | Chat | None = None
    if message.reply_to_message:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        if not target_entity and target_input.isdigit():
            target_entity = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Specify a user ID/@username (or reply) to unblacklist."); return
        
    if not target_entity:
        await message.reply_text("Skrrrt... I can't find the user."); return
    
    if isinstance(target_entity, Chat) and target_entity.type != ChatType.PRIVATE:
        await message.reply_text("🧐 This action can only be applied to users."); return
    if target_entity.id == OWNER_ID:
        await message.reply_text("WHAT? The Owner is never on the blacklist."); return

    user_display = create_user_html_link(target_entity)

    if not is_user_blacklisted(target_entity.id):
        await message.reply_html(f"ℹ️ User {user_display} (<code>{target_entity.id}</code>) is not on the blacklist.")
        return

    if remove_from_blacklist(target_entity.id):
        await message.reply_html(f"✅ User {user_display} (<code>{target_entity.id}</code>) has been removed from the blacklist.")
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_user_display = create_user_html_link(target_entity)
            admin_link = create_user_html_link(user)

            log_message_to_send = (
                f"<b>#UNBLACKLISTED</b>\n\n"
                f"<b>User:</b> {log_user_display}\n"
                f"<b>User ID:</b> <code>{target_entity.id}</code>\n"
                f"<b>Admin:</b> {admin_link}\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, log_message_to_send)
        except Exception as e:
            logger.error(f"Error preparing/sending #UNBLACKLISTED operational log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to remove user from the blacklist. Check logs.")

async def check_gban_on_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    new_members = update.message.new_chat_members if update.message else []
    chat = update.effective_chat

    if not new_members or not chat or not is_gban_enforced(chat.id):
        return

    for member in new_members:
        gban_reason = get_gban_reason(member.id)
        if gban_reason and not is_privileged_user(member.id):
            logger.info(f"Gbanned user {member.id} detected in {chat.id}. Enforcing ban.")
            try:
                await context.bot.ban_chat_member(chat_id=chat.id, user_id=member.id)
                
                message_text = (
                    f"⚠️ <b>Alert!</b> This user is globally banned.\n"
                    f"<i>Enforcing ban in this chat.</i>\n\n"
                    f"<b>User ID:</b> <code>{member.id}</code>\n"
                    f"<b>Reason:</b> {safe_escape(gban_reason)}\n"
                    f"<b>Appeal Chat:</b> {APPEAL_CHAT_USERNAME}"
                )
                await context.bot.send_message(chat.id, text=message_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Failed to enforce gban on new member {member.id} in {chat.id}: {e}")

async def check_gban_on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or update.effective_chat.type == ChatType.PRIVATE:
        return
    
    chat = update.effective_chat
    
    if not is_gban_enforced(chat.id):
        return

    user = update.effective_user
    if not user or is_privileged_user(user.id):
        return
        
    gban_reason = get_gban_reason(user.id)
    if gban_reason:
        message = update.effective_message
        
        try:
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            user_member = await context.bot.get_chat_member(chat.id, user.id)

            if user_member.status in ["creator", "administrator"]:
                return

            if bot_member.status == "administrator" and bot_member.can_restrict_members:
                
                await context.bot.ban_chat_member(chat.id, user.id)
                
                if bot_member.can_delete_messages:
                    try:
                        await message.delete()
                    except Exception: pass
                
                message_text = (
                    f"⚠️ <b>Alert!</b> This user is globally banned.\n"
                    f"<i>Enforcing ban in this chat.</i>\n\n"
                    f"<b>User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Reason:</b> {safe_escape(gban_reason)}\n"
                    f"<b>Appeal Chat:</b> {APPEAL_CHAT_USERNAME}"
                )
                await context.bot.send_message(chat.id, text=message_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Failed to take gban action on message for user {user.id} in chat {chat.id}: {e}")
        
        raise ApplicationHandlerStop

async def gban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_who_gbans = update.effective_user
    chat = update.effective_chat
    message = update.message
    if not message: return

    if not is_privileged_user(user_who_gbans.id):
        logger.warning(f"Unauthorized /gban attempt by user {user_who_gbans.id}.")
        return

    target_entity: User | Chat | None = None
    reason: str = "No reason provided."

    if message.reply_to_message:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
        if context.args:
            reason = " ".join(context.args)
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            reason = " ".join(context.args[1:])
        
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_entity and target_input.isdigit():
            target_entity = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /gban <ID/@username/reply> [reason]"); return
    
    if not target_entity:
        await message.reply_text(f"Skrrrt... I can't find the user.");
        return

    if isinstance(target_entity, Chat) and target_entity.type != ChatType.PRIVATE:
        await message.reply_text("🧐 This action can only be applied to users.")
        return
    if is_privileged_user(target_entity.id) or target_entity.id == context.bot.id:
        await message.reply_text("LoL, looks like... Someone tried global ban privileged user. Nice Try.")
        return
    if is_whitelisted(target_entity.id):
        await message.reply_text("This user is on the whitelist and cannot be globally banned.")
        return

    user_display = create_user_html_link(target_entity)
    existing_gban_reason = get_gban_reason(target_entity.id)
    if existing_gban_reason:
        await message.reply_html(
            f"ℹ️ User {user_display} (<code>{target_entity.id}</code>) is already globally banned.\n"
            f"<b>Reason:</b> {safe_escape(existing_gban_reason)}"
        )
        return

    add_to_gban(target_entity.id, user_who_gbans.id, reason)
    if chat.type != ChatType.PRIVATE and is_gban_enforced(chat.id):
        try:
            await context.bot.ban_chat_member(chat.id, target_entity.id)
        except Exception as e:
            logger.warning(f"Could not enforce local ban for gban in chat {chat.id}: {e}")

    await message.reply_html(f"✅ User {user_display} (<code>{target_entity.id}</code>) has been globally banned.\n<b>Reason:</b> {safe_escape(reason)}")
    
    try:
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        log_user_display = create_user_html_link(target_entity)
        
        chat_name_display = safe_escape(chat.title or f"PM with {user_who_gbans.first_name}")
        if chat.type != ChatType.PRIVATE and chat.username:
            message_link = f"https://t.me/{chat.username}/{message.message_id}"
            chat_name_display = f"<a href='{message_link}'>{safe_escape(chat.title)}</a>"

        reason_display = safe_escape(reason)
        admin_link = create_user_html_link(user_who_gbans)

        log_message = (
            f"<b>#GBANNED</b>\n"
            f"<b>Initiated From:</b> {chat_name_display} (<code>{chat.id}</code>)\n\n"
            f"<b>User:</b> {log_user_display}\n"
            f"<b>User ID:</b> <code>{target_entity.id}</code>\n"
            f"<b>Reason:</b> {reason_display}\n"
            f"<b>Admin:</b> {admin_link}\n"
            f"<b>Date:</b> <code>{current_time}</code>"
        )
        await send_operational_log(context, log_message)
    except Exception as e:
        logger.error(f"Error preparing/sending #GBANNED operational log: {e}", exc_info=True)

async def ungban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_who_ungbans = update.effective_user
    chat = update.effective_chat
    message = update.message
    if not message: return

    if not is_privileged_user(user_who_ungbans.id):
        logger.warning(f"Unauthorized /ungban attempt by user {user_who_ungbans.id}.")
        return

    target_entity: User | Chat | None = None
    if message.reply_to_message:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        if not target_entity and target_input.isdigit():
            target_entity = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /ungban <ID/@username/reply>"); return
        
    if not target_entity:
        await message.reply_text("Skrrrt... I can't find the user."); return

    if isinstance(target_entity, Chat) and target_entity.type != ChatType.PRIVATE:
        await message.reply_text("🧐 This action can only be applied to users."); return

    user_display = create_user_html_link(target_entity)

    if not get_gban_reason(target_entity.id):
        await message.reply_html(f"User {user_display} (<code>{target_entity.id}</code>) is not globally banned.")
        return

    remove_from_gban(target_entity.id)

    await message.reply_html(f"✅ User {user_display} (<code>{target_entity.id}</code>) has been globally unbanned.\n\n<i>Propagating unban...</i>")
    
    if context.job_queue:
        context.job_queue.run_once(propagate_unban, 1, data={'target_user_id': target_entity.id, 'command_chat_id': chat.id})

    try:
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        log_user_display = create_user_html_link(target_entity)
        
        chat_name_display = safe_escape(chat.title or f"PM with {user_who_ungbans.first_name}")
        if chat.type != ChatType.PRIVATE and chat.username:
            message_link = f"https://t.me/{chat.username}/{message.message_id}"
            chat_name_display = f"<a href='{message_link}'>{safe_escape(chat.title)}</a>"
            
        admin_link = create_user_html_link(user_who_ungbans)

        log_message = (
            f"<b>#UNGBANNED</b>\n"
            f"<b>Initiated From:</b> {chat_name_display} (<code>{chat.id}</code>)\n\n"
            f"<b>User:</b> {log_user_display}\n"
            f"<b>User ID:</b> <code>{target_entity.id}</code>\n"
            f"<b>Admin:</b> {admin_link}\n"
            f"<b>Date:</b> <code>{current_time}</code>"
        )
        await send_operational_log(context, log_message)
    except Exception as e:
        logger.error(f"Error preparing/sending #UNGBANNED operational log: {e}", exc_info=True)

async def propagate_unban(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    target_user_id = job_data['target_user_id']
    command_chat_id = job_data['command_chat_id']

    chats_to_scan = []
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            chats_to_scan = [row[0] for row in cursor.execute("SELECT chat_id FROM bot_chats")]
    except sqlite3.Error as e:
        logger.error(f"Failed to get chat list for unban propagation: {e}")
        await context.bot.send_message(chat_id=command_chat_id, text="Error fetching chat list from database.")
        return

    if not chats_to_scan:
        await context.bot.send_message(chat_id=command_chat_id, text="I don't seem to be in any chats to propagate the unban.")
        return

    successful_unbans = 0
    
    logger.info(f"Starting unban propagation for {target_user_id} across {len(chats_to_scan)} chats.")
    
    for chat_id in chats_to_scan:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=target_user_id)
            
            if chat_member.status == 'kicked':
                success = await context.bot.unban_chat_member(chat_id=chat_id, user_id=target_user_id)
                if success:
                    successful_unbans += 1
                    logger.info(f"Successfully unbanned {target_user_id} from chat {chat_id}.")
            
        except telegram.error.BadRequest as e:
            if "user not found" not in str(e).lower():
                logger.warning(f"Could not process unban for {target_user_id} in {chat_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during unban propagation in {chat_id}: {e}")
            
        await asyncio.sleep(0.2)

    logger.info(f"Unban propagation finished for {target_user_id}. Succeeded in {successful_unbans} chats.")
    
    final_message = f"✅ Correctly unbanned <code>{target_user_id}</code> on {successful_unbans} chats."
    
    await context.bot.send_message(
        chat_id=command_chat_id,
        text=final_message,
        parse_mode=ParseMode.HTML
    )

async def enforce_gban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("Huh? You can't set enforcement gban in private chat.")
        return

    try:
        member = await chat.get_member(user.id)
        if member.status != "creator":
            await update.message.reply_text("Only the chat Creator can use this command.")
            return
    except Exception as e:
        logger.error(f"Could not verify creator status for /enforcegban: {e}")
        return

    if not context.args or len(context.args) != 1 or context.args[0].lower() not in ['yes', 'no']:
        await update.message.reply_text("Usage: /enforcegban <yes/no>")
        return
    
    choice = context.args[0].lower()
    current_status_bool = is_gban_enforced(chat.id)

    if choice == 'yes':
        permission_notice = ""
        try:
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if not (bot_member.status == "administrator" and bot_member.can_restrict_members):
                permission_notice = (
                    "\n\n<b>⚠️ Notice:</b> I do not have the 'Ban Users' permission in this chat. "
                    "The feature is enabled in settings, but I cannot enforce it until I'm granted this right."
                )
        except Exception:
            permission_notice = "\n\n<b>⚠️ Notice:</b> Could not verify my own permissions in this chat."

        if current_status_bool:
            await update.message.reply_html(
                f"ℹ️ Global Ban enforcement is already <b>ENABLED</b> for this chat."
                f"{permission_notice}"
            )
            return
        
        setting = 1
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE bot_chats SET enforce_gban = ? WHERE chat_id = ?", (setting, chat.id))
                if cursor.rowcount == 0:
                    add_chat_to_db(chat.id, chat.title or f"Chat {chat.id}")
                    cursor.execute("UPDATE bot_chats SET enforce_gban = ? WHERE chat_id = ?", (setting, chat.id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update gban enforcement for chat {chat.id}: {e}")
            await update.message.reply_text("An error occurred while updating the setting.")
            return

        await update.message.reply_html(
            f"✅ <b>Global Ban enforcement is now ENABLED for this chat.</b>\n\n"
            f"I will now automatically remove any user from the global ban list who tries to join or speak here."
            f"{permission_notice}"
        )
        return

    if choice == 'no':
        if not current_status_bool:
            await update.message.reply_html("ℹ️ Global Ban enforcement is already <b>DISABLED</b> for this chat.")
            return
        
        setting = 0
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE bot_chats SET enforce_gban = ? WHERE chat_id = ?", (setting, chat.id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update gban enforcement for chat {chat.id}: {e}")
            await update.message.reply_text("An error occurred while updating the setting.")
            return
        
        await update.message.reply_html(
            "❌ <b>Global Ban enforcement is now DISABLED for this chat.</b>\n\n"
            "<b>Notice:</b> This means users on the global ban list will be able to join and participate here. "
            "This may expose your community to users banned for severe offenses like spam, harassment, or illegal activities."
        )

async def whitelist_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /whitelist attempt by user {user.id}.")
        return

    target_user: User | None = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
        if not target_user and target_input.isdigit():
            target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /addsupport <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return
        
    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 Added to Whitelist can only be users.")
        return

    user_display = create_user_html_link(target_user)

    if is_privileged_user(target_user.id):
        await message.reply_html(f"User {user_display} already has a privileged or protected role and cannot be whitelisted.")
        return

    gban_reason = get_gban_reason(target_user.id)
    blist_reason = get_blacklist_reason(target_user.id)

    gban_reason = get_gban_reason(target_user.id)
    if gban_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} (<code>{target_user.id}</code>) cannot be on <code>Whitelist</code> because they are <b>Globally Bannned</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(gban_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove global ban first using /ungban if you wish to proceed.</i>"
        )
        return
    blist_reason = get_blacklist_reason(target_user.id)
    if blist_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} (<code>{target_user.id}</code>) cannot be on <code>Whitelist</code> because they are on the <b>Blacklist</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(blist_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove the user from the blacklist first using /unblist if you wish to proceed.</i>"
        )
        return

    if add_to_whitelist(target_user.id, user.id):
        await message.reply_html(f"✅ User {user_display} (<code>{target_user.id}</code>) has been added to the whitelist.")
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            admin_link = create_user_html_link(user)

            log_message = (
                f"<b>#WHITELISTED</b>\n\n"
                f"<b>User:</b> {user_display}\n"
                f"<b>User ID:</b> <code>{target_user.id}</code>\n"
                f"<b>Admin:</b> {admin_link}\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #WHITELISTED log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to whitelist (they might be already on it).")

async def unwhitelist_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /unwhitelist attempt by user {user.id}.")
        return

    target_user: User | None = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
        if not target_user and target_input.isdigit():
            target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /delsupport <ID/@username/reply>")
        return
        
    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 Deleted from Whitelist can only be users.")
        return

    if not is_whitelisted(target_user.id):
        await update.message.reply_html(f"User {target_user.mention_html()} is not on the whitelist.")
        return
        
    if remove_from_whitelist(target_user.id):
        user_display = create_user_html_link(target_user)
        await update.message.reply_html(f"✅ User {user_display} (<code>{target_user.id}</code>) has been removed from the whitelist.")

        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            admin_link = create_user_html_link(user)

            log_message = (
                f"<b>#UNWHITELISTED</b>\n\n"
                f"<b>User:</b> {user_display}\n"
                f"<b>User ID:</b> <code>{target_user.id}</code>\n"
                f"<b>Admin:</b> {admin_link}\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #UNWHITELISTED log: {e}", exc_info=True)
    else:
        await update.message.reply_text("Failed to remove user from the whitelist.")

async def addsupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /addsupport attempt by user {user.id}.")
        return

    target_user: User | None = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
        if not target_user and target_input.isdigit():
            target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /addsupport <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    user_display = create_user_html_link(target_user)
    if is_privileged_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} (<code>{target_user.id}</code>) already has a privileged role. Use /setrank if want change it.")
        return
    
    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 This role can only be granted to users.")
        return

    if target_user.id == OWNER_ID or target_user.id == context.bot.id or target_user.is_bot:
        await message.reply_text("This user cannot be a Support.")
        return
    
    gban_reason = get_gban_reason(target_user.id)
    if gban_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} (<code>{target_user.id}</code>) cannot be promoted to <code>Support</code> because they are <b>Globally Bannned</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(gban_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove global ban first using /ungban if you wish to proceed.</i>"
        )
        return
    blist_reason = get_blacklist_reason(target_user.id)
    if blist_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} (<code>{target_user.id}</code>) cannot be promoted to <code>Sudo</code> because they are on the <b>Blacklist</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(blist_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove the user from the blacklist first using /unblist if you wish to proceed.</i>"
        )
        return

    if add_support_user(target_user.id, user.id):
        await message.reply_html(f"✅ User {user_display} (<code>{target_user.id}</code>) has been granted <b>Support</b> powers.")
        
        try:
            await context.bot.send_message(target_user.id, "You have been added to the Support team.")
        except Exception as e:
            logger.warning(f"Failed to send PM to new Support user {target_user.id}: {e}")

        admin_link = create_user_html_link(user)
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#SUPPORT</b>\n\n"
                f"<b>User:</b> {user_display}\n"
                f"<b>User ID:</b> <code>{target_user.id}</code>\n"
                f"<b>Admin:</b> {admin_link}\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #SUPPORT log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to Support list. Check logs.")

async def delsupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /delsupport attempt by user {user.id}.")
        return

    target_user: User | None = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
        if not target_user and target_input.isdigit():
            target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /delsupport <ID/@username/reply>")
        return
        
    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 This role can only be revoked from users.")
        return
    
    user_display = create_user_html_link(target_user)

    if not is_support_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} (<code>{target_user.id}</code>) is not in Support.")
        return

    if remove_support_user(target_user.id):
        await message.reply_html(f"✅ <b>Support</b> role for user {user_display} (<code>{target_user.id}</code>) has been revoked.")
        
        try:
            await context.bot.send_message(target_user.id, "You have been removed from the Support team.")
        except Exception as e:
            logger.warning(f"Failed to send PM to revoked Support user {target_user.id}: {e}")

        admin_link = create_user_html_link(user)

        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#UNSUPPORT</b>\n\n"
                f"<b>User:</b> {user_display}\n"
                f"<b>User ID:</b> <code>{target_user.id}</code>\n"
                f"<b>Admin:</b> {admin_link}\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #UNSUPPORT log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to remove user from Support list. Check logs.")

async def addsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /addsudo attempt by user {user.id}.")
        return

    target_user: User | None = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in ADDSUDO. Creating a minimal User object.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /addsudo <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    user_display = create_user_html_link(target_user)
    if is_privileged_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} (<code>{target_user.id}</code>) already has a privileged role. Use /setrank if want change it.")
        return
    
    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 Sudo can only be granted to users.")
        return

    if target_user.id == OWNER_ID or target_user.id == context.bot.id or target_user.is_bot:
        await message.reply_text("This user cannot be a sudo.")
        return
    
    gban_reason = get_gban_reason(target_user.id)
    blist_reason = get_blacklist_reason(target_user.id)

    if gban_reason:
        error_message = (
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} (<code>{target_user.id}</code>) cannot be promoted to <code>Sudo</code> because they are <b>Globally Bannned</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(gban_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove global ban first using /ungban if you wish to proceed.</i>"
        )
        await message.reply_html(error_message)
        return

    if blist_reason:
        error_message = (
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} (<code>{target_user.id}</code>) cannot be promoted to <code>Sudo</code> because they are on the <b>Blacklist</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(blist_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove the user from the blacklist first using /unblist if you wish to proceed.</i>"
        )
        await message.reply_html(error_message)
        return

    if add_sudo_user(target_user.id, user.id):
        await message.reply_html(f"✅ User {user_display} (<code>{target_user.id}</code>) has been granted <b>Sudo</b> powers.")
        
        try:
            await context.bot.send_message(target_user.id, "You have been granted Sudo privileges.")
        except Exception as e:
            logger.warning(f"Failed to send PM to new sudo user {target_user.id}: {e}")

        admin_link = create_user_html_link(user)
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#SUDO</b>\n\n"
                f"<b>User:</b> {user_display}\n"
                f"<b>User ID:</b> <code>{target_user.id}</code>\n"
                f"<b>Admin:</b> {admin_link}\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #SUDO log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to sudo list. Check logs.")

async def delsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /delsudo attempt by user {user.id}.")
        return

    target_user: User | None = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in DELSUDO. Creating a minimal User object.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /delsudo <ID/@username/reply>")
        return
        
    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user..")
        return

    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 Sudo can only be revoked from users.")
        return

    if target_user.id == OWNER_ID:
        await message.reply_text("The Owner's powers cannot be revoked.")
        return
    
    user_display = create_user_html_link(target_user)

    if not is_sudo_user(target_user.id):
        await message.reply_html(f"User {user_display} (<code>{target_user.id}</code>) does not have sudo powers.")
        return

    if remove_sudo_user(target_user.id):
        await message.reply_html(f"✅ <b>Sudo</b> powers for user {user_display} (<code>{target_user.id}</code>) have been revoked.")
        
        try:
            await context.bot.send_message(target_user.id, "Your sudo privileges have been revoked.")
        except Exception as e:
            logger.warning(f"Failed to send PM to revoked sudo user {target_user.id}: {e}")

        admin_link = create_user_html_link(user)

        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#UNSUDO</b>\n\n"
                f"<b>User:</b> {user_display}\n"
                f"<b>User ID:</b> <code>{target_user.id}</code>\n"
                f"<b>Admin:</b> {admin_link}\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #UNSUDO log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to remove user from sudo list. Check logs.")

async def setrank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /setrank attempt by user {user.id}.")
        return

    target_user: User | None = None
    args_for_role: list[str] = []

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        args_for_role = context.args
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
        if not target_user and target_input.isdigit():
            target_user = User(id=int(target_input), first_name="", is_bot=False)
        args_for_role = context.args[1:]
    
    if not target_user or not args_for_role:
        await message.reply_text("Usage: /setrank <ID/@username/reply> [support/sudo/dev]")
        return

    new_role_shortcut = args_for_role[0].lower()

    role_map = {
        "support": "Support",
        "sudo": "Sudo",
        "dev": "Developer"
    }

    if new_role_shortcut not in role_map:
        await message.reply_text(f"Invalid role '{safe_escape(new_role_shortcut)}'. Please use one of: support, sudo, dev.")
        return

    new_role_full_name = role_map[new_role_shortcut]

    if target_user.id == OWNER_ID:
        await message.reply_text("Owner cannot have his rank changed because he has the ultimate authority.")
        return

    if not is_privileged_user(target_user.id):
        await message.reply_text("This command can only be used on users who already have a role (Support, Sudo, or Developer).")
        return

    if is_dev_user(user.id):
        if user.id == target_user.id:
            await message.reply_text("You cannot change your own rank.")
            return
        if is_dev_user(target_user.id):
            await message.reply_text("As a Developer, you cannot change the rank of other Developers.")
            return
        if new_role_shortcut == "dev":
            await message.reply_text("As a Developer, you cannot promote others to the Developer role.")
            return

    current_role_shortcut = ""
    if is_dev_user(target_user.id): current_role_shortcut = "dev"
    elif is_sudo_user(target_user.id): current_role_shortcut = "sudo"
    elif is_support_user(target_user.id): current_role_shortcut = "support"
    
    current_role_full_name = role_map.get(current_role_shortcut, "Unknown")

    if new_role_shortcut == current_role_shortcut:
        await message.reply_text(f"User is already a {new_role_full_name}. No changes made.")
        return

    remove_support_user(target_user.id)
    remove_sudo_user(target_user.id)
    remove_dev_user(target_user.id)

    success = False
    if new_role_shortcut == "support":
        success = add_support_user(target_user.id, user.id)
    elif new_role_shortcut == "sudo":
        success = add_sudo_user(target_user.id, user.id)
    elif new_role_shortcut == "dev":
        success = add_dev_user(target_user.id, user.id)

    if success:
        user_display = create_user_html_link(target_user)
        admin_link = create_user_html_link(user)
        
        feedback_message = f"✅ User {user_display} (<code>{target_user.id}</code>) rank has been changed from <b>{current_role_full_name}</b> to <b>{new_role_full_name}</b>."
        await message.reply_html(feedback_message)

        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        log_message = (f"<b>#ROLECHANGED</b>\n\n"
                       f"<b>User:</b> {user_display}\n"
                       f"<b>User ID:</b> <code>{target_user.id}</code>\n"
                       f"<b>Old Role:</b> <code>{current_role_full_name}</code>\n"
                       f"<b>New Role:</b> <code>{new_role_full_name}</code>\n"
                       f"<b>Admin:</b> {admin_link}\n"
                       f"<b>Date:</b> <code>{current_time}</code>")
        await send_operational_log(context, log_message)
    else:
        await message.reply_text("An error occurred while changing the rank. Check logs.")

async def adddev_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /adddev attempt by user {user.id}.")
        return

    target_user: User | None = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
        if not target_user and target_input.isdigit():
            target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /adddev <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    user_display = create_user_html_link(target_user)
    if is_privileged_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} (<code>{target_user.id}</code>) already has a privileged role. Use /setrank if want change it.")
        return
    
    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 This role can only be granted to users.")
        return

    if target_user.id == OWNER_ID or target_user.id == context.bot.id or target_user.is_bot:
        await message.reply_text("This user cannot be a Developer.")
        return
    
    gban_reason = get_gban_reason(target_user.id)
    if gban_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} (<code>{target_user.id}</code>) cannot be promoted to <code>Developer</code> because they are <b>Globally Bannned</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(gban_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove global ban first using /ungban if you wish to proceed.</i>"
        )
        return
    blist_reason = get_blacklist_reason(target_user.id)
    if blist_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} (<code>{target_user.id}</code>) cannot be promoted to <code>Developer</code> because they are on the <b>Blacklist</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(blist_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove the user from the blacklist first using /unblist if you wish to proceed.</i>"
        )
        return

    if add_dev_user(target_user.id, user.id):
        await message.reply_html(f"✅ User {user_display} (<code>{target_user.id}</code>) has been granted <b>Developer</b> powers.")
        
        try:
            await context.bot.send_message(target_user.id, "You have been promoted to Developer by the Bot Owner.")
        except Exception as e:
            logger.warning(f"Failed to send PM to new Dev user {target_user.id}: {e}")
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#DEVELOPER</b>\n\n"
                f"<b>User:</b> {user_display}\n"
                f"<b>User ID:</b> <code>{target_user.id}</code>\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #DEVELOPER log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to Developer list. Check logs.")

async def deldev_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /deldev attempt by user {user.id}.")
        return

    target_user: User | None = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
        if not target_user and target_input.isdigit():
            target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /deldev <ID/@username/reply>")
        return
        
    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    if isinstance(target_user, Chat) and target_user.type != ChatType.PRIVATE:
        await message.reply_text("🧐 This role can only be revoked from users.")
        return
    
    user_display = create_user_html_link(target_user)

    if not is_dev_user(target_user.id):
        await message.reply_html(f"User {user_display} (<code>{target_user.id}</code>) is not a Developer.")
        return

    if remove_dev_user(target_user.id):
        await message.reply_html(f"✅ <b>Developer</b> role for user {user_display} (<code>{target_user.id}</code>) has been revoked.")
        
        try:
            await context.bot.send_message(target_user.id, "Your Developer role has been revoked by the Bot Owner.")
        except Exception as e:
            logger.warning(f"Failed to send PM to revoked Dev user {target_user.id}: {e}")

        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#UNDEVELOPER</b>\n\n"
                f"<b>User:</b> {user_display}\n"
                f"<b>User ID:</b> <code>{target_user.id}</code>\n"
                f"<b>Date:</b> <code>{current_time}</code>"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #UNDEVELOPER log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to remove user from Developer list. Check logs.")

async def sudo_commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    
    if not is_privileged_user(user.id):
        return

    help_parts = []

    if is_sudo_user(user.id) or is_dev_user(user.id) or user.id == OWNER_ID:
        help_parts.append(ADMIN_NOTE_TEXT)

    if is_support_user(user.id) or is_sudo_user(user.id) or is_dev_user(user.id) or user.id == OWNER_ID:
        help_parts.append(SUPPORT_COMMANDS_TEXT)

    if is_sudo_user(user.id) or is_dev_user(user.id) or user.id == OWNER_ID:
        help_parts.append(SUDO_COMMANDS_TEXT)

    if is_dev_user(user.id) or user.id == OWNER_ID:
        help_parts.append(DEVELOPER_COMMANDS_TEXT)
    
    if user.id == OWNER_ID:
        help_parts.append(OWNER_COMMANDS_TEXT)
    
    final_help_text = "".join(help_parts)
    
    if chat.type == ChatType.PRIVATE:
        if final_help_text:
            await update.message.reply_html(final_help_text, disable_web_page_preview=True)
    else:
        bot_username = context.bot.username
        deep_link_url = f"https://t.me/{bot_username}?start=sudocmds"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="🛡️ Get Privileged Commands (PM)", url=deep_link_url)]]
        )
        await send_safe_reply(update, context, text="The list of privileged commands has been sent to your private chat.", reply_markup=keyboard)

async def listdevs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        return

    dev_user_tuples = get_all_dev_users_from_db()

    if not dev_user_tuples:
        await update.message.reply_text("There are currently no users with Developer role.")
        return

    response_lines = [f"<b>🛃 Developer Users List:</b>\n"]
    
    for user_id, timestamp_str in dev_user_tuples:
        user_display_name = f"<code>{user_id}</code>"

        try:
            chat_info = await context.bot.get_chat(user_id)
            name_parts = []
            if chat_info.first_name: name_parts.append(safe_escape(chat_info.first_name))
            if chat_info.last_name: name_parts.append(safe_escape(chat_info.last_name))
            if chat_info.username: name_parts.append(f"(@{safe_escape(chat_info.username)})")
            
            if name_parts:
                user_display_name = " ".join(name_parts) + f" (<code>{user_id}</code>)"
        except Exception:
            user_obj_from_db = get_user_from_db_by_username(str(user_id))
            if user_obj_from_db:
                display_name_parts = []
                if user_obj_from_db.first_name: display_name_parts.append(safe_escape(user_obj_from_db.first_name))
                if user_obj_from_db.last_name: display_name_parts.append(safe_escape(user_obj_from_db.last_name))
                if user_obj_from_db.username: display_name_parts.append(f"(@{safe_escape(user_obj_from_db.username)})")
                if display_name_parts:
                    user_display_name = " ".join(display_name_parts) + f" (<code>{user_id}</code>)"

        formatted_added_time = timestamp_str
        try:
            dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp '{timestamp_str}' for dev user {user_id}")

        response_lines.append(f"• {user_display_name}\n<b>Added:</b> <code>{formatted_added_time}</code>\n")

    message_text = "\n".join(response_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

async def list_sudo_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listsudo attempt by user {user.id}.")
        return

    sudo_user_tuples = get_all_sudo_users_from_db()

    if not sudo_user_tuples:
        await update.message.reply_text("There are currently no users with sudo privileges.")
        return

    response_lines = ["<b>🛡️ Sudo Users List:</b>\n"]
    
    for user_id, timestamp_str in sudo_user_tuples:
        user_display_name = f"<code>{user_id}</code>"

        try:
            chat_info = await context.bot.get_chat(user_id)
            name_parts = []
            if chat_info.first_name: name_parts.append(safe_escape(chat_info.first_name))
            if chat_info.last_name: name_parts.append(safe_escape(chat_info.last_name))
            if chat_info.username: name_parts.append(f"(@{safe_escape(chat_info.username)})")
            
            if name_parts:
                user_display_name = " ".join(name_parts) + f" (<code>{user_id}</code>)"
        except Exception:
            user_obj_from_db = get_user_from_db_by_username(str(user_id))
            if user_obj_from_db:
                display_name_parts = []
                if user_obj_from_db.first_name: display_name_parts.append(safe_escape(user_obj_from_db.first_name))
                if user_obj_from_db.last_name: display_name_parts.append(safe_escape(user_obj_from_db.last_name))
                if user_obj_from_db.username: display_name_parts.append(f"(@{safe_escape(user_obj_from_db.username)})")
                if display_name_parts:
                    user_display_name = " ".join(display_name_parts) + f" (<code>{user_id}</code>)"

        formatted_added_time = timestamp_str
        try:
            dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp '{timestamp_str}' for sudo user {user_id}")

        response_lines.append(f"• {user_display_name}\n<b>Added:</b> <code>{formatted_added_time}</code>\n")

    message_text = "\n".join(response_lines)
    if len(message_text) > 4000:
        message_text = "\n".join(response_lines[:15])
        message_text += f"\n\n...and {len(sudo_user_tuples) - 15} more (list too long to display fully)."
        logger.info(f"Sudo list too long, truncated for display. Total: {len(sudo_user_tuples)}")

    await update.message.reply_html(message_text, disable_web_page_preview=True)

async def listsupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listsupport attempt by user {user.id}.")
        return

    support_user_tuples = get_all_support_users_from_db()

    if not support_user_tuples:
        await update.message.reply_text("There are currently no users in the Support team.")
        return

    response_lines = [f"<b>👷‍♂️ Support Users List:</b>\n"]
    
    for user_id, timestamp_str in support_user_tuples:
        user_display_name = f"<code>{user_id}</code>"

        try:
            chat_info = await context.bot.get_chat(user_id)
            name_parts = []
            if chat_info.first_name: name_parts.append(safe_escape(chat_info.first_name))
            if chat_info.last_name: name_parts.append(safe_escape(chat_info.last_name))
            if chat_info.username: name_parts.append(f"(@{safe_escape(chat_info.username)})")
            
            if name_parts:
                user_display_name = " ".join(name_parts) + f" (<code>{user_id}</code>)"
        except Exception:
            user_obj_from_db = get_user_from_db_by_username(str(user_id))
            if user_obj_from_db:
                display_name_parts = []
                if user_obj_from_db.first_name: display_name_parts.append(safe_escape(user_obj_from_db.first_name))
                if user_obj_from_db.last_name: display_name_parts.append(safe_escape(user_obj_from_db.last_name))
                if user_obj_from_db.username: display_name_parts.append(f"(@{safe_escape(user_obj_from_db.username)})")
                if display_name_parts:
                    user_display_name = " ".join(display_name_parts) + f" (<code>{user_id}</code>)"

        formatted_added_time = timestamp_str
        try:
            dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp '{timestamp_str}' for support user {user_id}")

        response_lines.append(f"• {user_display_name}\n<b>Added:</b> <code>{formatted_added_time}</code>\n")

    message_text = "\n".join(response_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

async def listwhitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listwhitelist attempt by user {user.id}.")
        return

    whitelist_user_tuples = get_all_whitelist_users_from_db()

    if not whitelist_user_tuples:
        await update.message.reply_text("There are currently no users in the Whitelist.")
        return

    response_lines = [f"<b>🔰 Whitelist Users List:</b>\n"]
    
    for user_id, timestamp_str in whitelist_user_tuples:
        user_display_name = f"<code>{user_id}</code>"

        try:
            chat_info = await context.bot.get_chat(user_id)
            name_parts = []
            if chat_info.first_name: name_parts.append(safe_escape(chat_info.first_name))
            if chat_info.last_name: name_parts.append(safe_escape(chat_info.last_name))
            if chat_info.username: name_parts.append(f"(@{safe_escape(chat_info.username)})")
            
            if name_parts:
                user_display_name = " ".join(name_parts) + f" (<code>{user_id}</code>)"
        except Exception:
            user_obj_from_db = get_user_from_db_by_username(str(user_id))
            if user_obj_from_db:
                display_name_parts = []
                if user_obj_from_db.first_name: display_name_parts.append(safe_escape(user_obj_from_db.first_name))
                if user_obj_from_db.last_name: display_name_parts.append(safe_escape(user_obj_from_db.last_name))
                if user_obj_from_db.username: display_name_parts.append(f"(@{safe_escape(user_obj_from_db.username)})")
                if display_name_parts:
                    user_display_name = " ".join(display_name_parts) + f" (<code>{user_id}</code>)"

        formatted_added_time = timestamp_str
        try:
            dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp '{timestamp_str}' for support user {user_id}")

        response_lines.append(f"• {user_display_name}\n<b>Added:</b> <code>{formatted_added_time}</code>\n")

    message_text = "\n".join(response_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

async def list_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listgroups attempt by user {user.id}.")
        return

    bot_chats = get_all_bot_chats_from_db()

    if not bot_chats:
        await update.message.reply_text("The bot is not currently in any known groups.")
        return

    response_lines = [f"<b>📊 List of all known groups; <code>{len(bot_chats)}</code> total:</b>\n\n"]
    
    for chat_id, chat_title, added_at_str in bot_chats:
        display_title = safe_escape(chat_title or "Untitled Group")
        
        try:
            dt_obj = datetime.fromisoformat(added_at_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            formatted_added_time = added_at_str[:16] if added_at_str else "N/A"

        response_lines.append(
            f"• <b>{display_title}</b> (<code>{chat_id}</code>)\n"
            f"<b>Added:</b> <code>{formatted_added_time}</code>\n\n"
        )

    final_message = ""
    for line in response_lines:
        if len(final_message) + len(line) > 4096:
            await update.message.reply_html(final_message, disable_web_page_preview=True)
            final_message = ""
        final_message += line

    if final_message:
        await update.message.reply_html(final_message, disable_web_page_preview=True)

async def del_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /delgroup attempt by user {user.id}.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delchat <ID_1> [ID_2] ...")
        return

    deleted_chats = []
    failed_chats = []

    for chat_id_str in context.args:
        try:
            chat_id_to_delete = int(chat_id_str)
            if remove_chat_from_db_by_id(chat_id_to_delete):
                deleted_chats.append(f"<code>{chat_id_to_delete}</code>")
            else:
                failed_chats.append(f"<code>{chat_id_to_delete}</code> (not found)")
        except ValueError:
            failed_chats.append(f"<i>{safe_escape(chat_id_str)}</i> (invalid ID)")

    response_lines = []
    if deleted_chats:
        response_lines.append(f"✅ Successfully removed <code>{len(deleted_chats)}</code> entries from the chat cache:")
        response_lines.append(", ".join(deleted_chats))
    
    if failed_chats:
        if response_lines: response_lines.append("")
        response_lines.append(f"❌ Failed to remove <code>{len(failed_chats)}</code> entries:")
        response_lines.append(", ".join(failed_chats))
    
    if not response_lines:
        await update.message.reply_text("No valid IDs were provided.")
        return

    await update.message.reply_html("\n".join(response_lines))

async def clean_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /cleangroups attempt by user {user.id}.")
        return

    status_message = await update.message.reply_html("🧹 Starting group cache cleanup... This may take a while. Please wait.")

    all_chat_ids_from_db = [chat[0] for chat in get_all_bot_chats_from_db()]
    
    if not all_chat_ids_from_db:
        await status_message.edit_text("✅ Chat cache is already empty. Nothing to do.")
        return

    logger.info(f"Starting cleanup for {len(all_chat_ids_from_db)} chats...")
    
    removed_chats_count = 0
    checked_chats_count = 0
    
    chunk_size = 50 
    for i in range(0, len(all_chat_ids_from_db), chunk_size):
        chunk = all_chat_ids_from_db[i:i + chunk_size]
        
        status_text = (
            f"🧹 Checking chats <code>{checked_chats_count+1}-{checked_chats_count+len(chunk)} / {len(all_chat_ids_from_db)}</code>\n"
            f"🗑️ Removed so far: <code>{removed_chats_count}</code>"
        )
        try:
            await status_message.edit_text(status_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.warning(f"Could not edit status message: {e}")

        for chat_id in chunk:
            try:
                await context.bot.get_chat(chat_id)
            except TelegramError as e:
                if "not found" in str(e).lower() or "forbidden" in str(e).lower() or "chat not found" in str(e).lower():
                    logger.info(f"Chat {chat_id} not found or access is forbidden. Removing from cache.")
                    if remove_chat_from_db_by_id(chat_id):
                        removed_chats_count += 1
                else:
                    logger.warning(f"Unexpected API error while checking chat {chat_id}: {e}")
            
            checked_chats_count += 1
            await asyncio.sleep(0.2)

    final_report = (
        f"✅ <b>Cleanup complete!</b>\n\n"
        f"• Checked: <code>{checked_chats_count}</code> chats\n"
        f"• Removed: <code>{removed_chats_count}</code> inactive/invalid entries"
    )
    
    try:
        await status_message.edit_text(final_report, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Could not edit final report message: {e}")

async def shell_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /shell attempt by user {user.id}.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /shell <command>")
        return

    command = " ".join(context.args)
    status_message = await update.message.reply_html(f"🔩 Executing: <code>{html.escape(command)}</code>")

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)

        result_text = ""
        if stdout:
            result_text += f"<code>{html.escape(stdout.decode('utf-8', errors='ignore'))}</code>\n"
        if stderr:
            result_text += f"<code>{html.escape(stderr.decode('utf-8', errors='ignore'))}</code>\n"
        if not stdout and not stderr:
            result_text = "✅ Command executed with no output."
            
        if len(result_text) > 4096:
            await status_message.edit_text("Output is too long. Sending as a file.")
            with io.BytesIO(str.encode(result_text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", ""))) as f:
                f.name = "shell_output.txt"
                await update.message.reply_document(document=f)
        else:
            await status_message.edit_text(result_text, parse_mode=ParseMode.HTML)

    except asyncio.TimeoutError:
        await status_message.edit_text("<b>Error:</b> Command timed out after 60 seconds.")
    except Exception as e:
        logger.error(f"Error executing shell command '{command}': {e}", exc_info=True)
        await status_message.edit_text(f"<b>Error:</b> {html.escape(str(e))}")

async def execute_script_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /execute attempt by user {user.id}.")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /execute <script_path> [args...]")
        return
    
    await shell_command(update, context)

# --- Main Function ---
async def main() -> None:
    init_db()
    
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as telethon_client:
        logger.info("Telethon client started.")
    
        custom_request_settings = HTTPXRequest(connect_timeout=20.0, read_timeout=80.0, write_timeout=80.0, pool_timeout=20.0)
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .request(custom_request_settings)
            .job_queue(JobQueue())
            .build()
        )

        application.bot_data['telethon_client'] = telethon_client
        logger.info("Telethon client has been injected into bot_data.")

        application.add_handler(ChatMemberHandler(handle_bot_permission_changes, ChatMemberHandler.MY_CHAT_MEMBER))
        application.add_handler(MessageHandler(filters.COMMAND, check_blacklist_handler), group=-1)
        application.add_handler(MessageHandler(filters.ALL & (~filters.UpdateType.EDITED_MESSAGE), log_user_from_interaction), group=10)
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & filters.ChatType.GROUPS, check_gban_on_message), group=-2)
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("github", github))
        application.add_handler(CommandHandler("owner", owner_info))
        application.add_handler(CommandHandler("info", entity_info_command))
        application.add_handler(CommandHandler("id", id_command))
        application.add_handler(CommandHandler("chatinfo", chat_sinfo_command))
        application.add_handler(CommandHandler("cinfo", chat_info_command))
        application.add_handler(CommandHandler("ban", ban_command))
        application.add_handler(CommandHandler("unban", unban_command))
        application.add_handler(CommandHandler("mute", mute_command))
        application.add_handler(CommandHandler("unmute", unmute_command))
        application.add_handler(CommandHandler("kick", kick_command))
        application.add_handler(CommandHandler("kickme", kickme_command))
        application.add_handler(CommandHandler("promote", promote_command))
        application.add_handler(CommandHandler("demote", demote_command))
        application.add_handler(CommandHandler("pin", pin_message_command))
        application.add_handler(CommandHandler("unpin", unpin_message_command))
        application.add_handler(CommandHandler("purge", purge_messages_command))
        application.add_handler(CommandHandler("report", report_command))
        application.add_handler(CommandHandler(["listadmins", "admins"], list_admins_command))
        application.add_handler(CommandHandler("zombies", zombies_command))
        application.add_handler(CommandHandler("welcome", welcome_command))
        application.add_handler(CommandHandler("setwelcome", set_welcome_command))
        application.add_handler(CommandHandler("resetwelcome", reset_welcome_command))
        application.add_handler(CommandHandler("goodbye", goodbye_command))
        application.add_handler(CommandHandler("setgoodbye", set_goodbye_command))
        application.add_handler(CommandHandler("resetgoodbye", reset_goodbye_command))
        application.add_handler(CommandHandler("welcomehelp", welcome_help_command))
        application.add_handler(CommandHandler("cleanservice", set_clean_service_command))
        application.add_handler(CommandHandler(["addnote", "savenote"], save_note_command))
        application.add_handler(CommandHandler("notes", list_notes_command))
        application.add_handler(CommandHandler(["delnote", "rmnote"], remove_note_command))
        application.add_handler(CommandHandler("warn", warn_command))
        application.add_handler(CallbackQueryHandler(undo_warn_callback, pattern=r"^undo_warn_"))
        application.add_handler(CommandHandler(["warnings", "warns"], warnings_command))
        application.add_handler(CommandHandler("resetwarns", reset_warnings_command))
        application.add_handler(CommandHandler("setwarnlimit", set_warn_limit_command))
        application.add_handler(CommandHandler("kill", kill))
        application.add_handler(CommandHandler("punch", punch))
        application.add_handler(CommandHandler("slap", slap))
        application.add_handler(CommandHandler("pat", pat))
        application.add_handler(CommandHandler("bonk", bonk))
        application.add_handler(CommandHandler("touch", damnbroski))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("ping", ping_command))
        application.add_handler(CommandHandler("say", say))
        application.add_handler(CommandHandler("leave", leave_chat))
        application.add_handler(CommandHandler("speedtest", speedtest_command))
        application.add_handler(CommandHandler("blist", blacklist_user_command))
        application.add_handler(CommandHandler("unblist", unblacklist_user_command))
        application.add_handler(CommandHandler("gban", gban_command))
        application.add_handler(CommandHandler("ungban", ungban_command))
        application.add_handler(CommandHandler("enforcegban", enforce_gban_command))
        application.add_handler(CommandHandler("setai", set_ai_command))
        application.add_handler(CommandHandler("askai", ask_ai_command))
        application.add_handler(CommandHandler("listsudo", list_sudo_users_command))
        application.add_handler(CommandHandler("listgroups", list_groups_command))
        application.add_handler(CommandHandler("delgroup", del_groups_command))
        application.add_handler(CommandHandler("cleangroups", clean_groups_command))
        application.add_handler(CommandHandler("sudocmds", sudo_commands_command))
        application.add_handler(CommandHandler("addsudo", addsudo_command))
        application.add_handler(CommandHandler("delsudo", delsudo_command))
        application.add_handler(CommandHandler("adddev", adddev_command))
        application.add_handler(CommandHandler("deldev", deldev_command))
        application.add_handler(CommandHandler("listdevs", listdevs_command))
        application.add_handler(CommandHandler("whitelist", whitelist_user_command))
        application.add_handler(CommandHandler("unwhitelist", unwhitelist_user_command))
        application.add_handler(CommandHandler("addsupport", addsupport_command))
        application.add_handler(CommandHandler("delsupport", delsupport_command))
        application.add_handler(CommandHandler("setrank", setrank_command))
        application.add_handler(CommandHandler("listsupport", listsupport_command))
        application.add_handler(CommandHandler("listwhitelist", listwhitelist_command))
        application.add_handler(CommandHandler("shell", shell_command))
        application.add_handler(CommandHandler("execute", execute_script_command))

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_note_trigger), group=0)

        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, check_gban_on_entry), group=-1)
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_group_members))
        application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_group_member))

        if application.job_queue:
            application.job_queue.run_once(send_startup_log, when=1)
            logger.info("Startup message job scheduled to run in 1 second.")
        else:
            logger.warning("JobQueue not available, cannot schedule startup message.")
        
        logger.info(f"Bot starting polling... Owner ID: {OWNER_ID}")
        print(f"Bot starting polling... Owner ID: {OWNER_ID}")
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        await telethon_client.run_until_disconnected()

        await application.updater.stop()
        await application.stop()
        logger.info("Bot shutdown process completed.")
        print("Bot shut down.")


# --- Script Execution ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user (Ctrl+C).")
        print("\nBot stopped by user.")
    except Exception as e:
        logger.critical(f"CRITICAL: Bot crashed unexpectedly at top level: {e}", exc_info=True)
        print(f"\n--- FATAL ERROR ---\nBot crashed: {e}")
        exit(1)
