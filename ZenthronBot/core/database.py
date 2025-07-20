import sqlite3
import logging
import json
from datetime import datetime, timezone
from typing import List, Tuple
from telegram import User

from ..config import DB_NAME, MAX_WARNS

logger = logging.getLogger(__name__)

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
                warn_limit INTEGER,
                rules_text TEXT
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS afk_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                afk_since TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disabled_modules (
                module_name TEXT PRIMARY KEY
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disabled_commands_per_chat (
                chat_id INTEGER,
                command_name TEXT,
                PRIMARY KEY (chat_id, command_name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_join_settings (
                chat_id INTEGER PRIMARY KEY,
                filters TEXT,
                action TEXT NOT NULL DEFAULT 'kick'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                reply_text TEXT,
                reply_type TEXT NOT NULL DEFAULT 'text', -- 'text', 'photo', 'sticker', 'audio', 'document', 'animation', 'video', 'voice'
                file_id TEXT,
                filter_type TEXT NOT NULL DEFAULT 'keyword', -- 'keyword', 'wildcard', 'regex'
                buttons TEXT,
                UNIQUE (chat_id, keyword)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_blacklist (
                chat_id INTEGER PRIMARY KEY,
                chat_name TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        logger.info(f"Database '{DB_NAME}' initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"SQLite error during DB initialization: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

# --- DATABASE HELPER FUNCTIONS ---
# --- MODULES ---
def is_module_disabled(module_name: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT module_name FROM disabled_modules WHERE module_name = ?", (module_name,))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Błąd SQLite przy sprawdzaniu modułu {module_name}: {e}")
        return False

def disable_module(module_name: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT OR IGNORE INTO disabled_modules (module_name) VALUES (?)", (module_name,))
            return conn.total_changes > 0
    except sqlite3.Error as e:
        logger.error(f"Błąd SQLite przy wyłączaniu modułu {module_name}: {e}")
        return False

def enable_module(module_name: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM disabled_modules WHERE module_name = ?", (module_name,))
            return conn.total_changes > 0
    except sqlite3.Error as e:
        logger.error(f"Błąd SQLite przy włączaniu modułu {module_name}: {e}")
        return False

def get_disabled_modules() -> list:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT module_name FROM disabled_modules")
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Błąd SQLite przy pobieraniu wyłączonych modułów: {e}")
        return []

# --- DISABLERS ---
def is_command_disabled_in_chat(chat_id: int, command_name: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM disabled_commands_per_chat WHERE chat_id = ? AND command_name = ?",
                (chat_id, command_name.lower())
            )
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"SQLite error checking disabled command '{command_name}' in chat {chat_id}: {e}")
        return False

def disable_command_in_chat(chat_id: int, command_name: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO disabled_commands_per_chat (chat_id, command_name) VALUES (?, ?)",
                (chat_id, command_name.lower())
            )
            return conn.total_changes > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error disabling command '{command_name}' in chat {chat_id}: {e}")
        return False

def enable_command_in_chat(chat_id: int, command_name: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                "DELETE FROM disabled_commands_per_chat WHERE chat_id = ? AND command_name = ?",
                (chat_id, command_name.lower())
            )
            return conn.total_changes > 0
    except sqlite3.Error as e:
        logger.error(f"SQLite error enabling command '{command_name}' in chat {chat_id}: {e}")
        return False

def get_disabled_commands_in_chat(chat_id: int) -> list[str]:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT command_name FROM disabled_commands_per_chat WHERE chat_id = ?",
                (chat_id,)
            )
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"SQLite error getting disabled commands for chat {chat_id}: {e}")
        return []

# --- BLACKLIST ---
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

# --- WHITELIST ---
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

# --- SUPPORT ---
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

# --- SUDO ---
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

# --- DEVELOPER ---
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

# --- GLOBAL BANS ---
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

# --- USERS ---
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

def delete_user_from_db(user_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error deleting user {user_id} from DB: {e}")
        return False

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

# --- CHATS ---
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

# --- CHAT SETTINGS ---
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

def set_rules(chat_id: int, rules: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT OR IGNORE INTO bot_chats (chat_id, added_at) VALUES (?, ?)",
                         (chat_id, datetime.now(timezone.utc).isoformat()))
            conn.execute("UPDATE bot_chats SET rules_text = ? WHERE chat_id = ?", (rules, chat_id))
        return True
    except sqlite3.Error as e:
        logger.error(f"Error setting rules for chat {chat_id}: {e}")
        return False

def get_rules(chat_id: int) -> str | None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.cursor().execute("SELECT rules_text FROM bot_chats WHERE chat_id = ?", (chat_id,)).fetchone()
            return res[0] if res else None
    except sqlite3.Error:
        return None

def clear_rules(chat_id: int) -> bool:
    return set_rules(chat_id, None)

# --- NOTES ---
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

# --- WARNINGS ---
def add_warning(chat_id: int, user_id: int, reason: str, admin_id: int) -> Tuple[int, int]:
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

# --- AFK ---
def set_afk(user_id: int, reason: str | None) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            timestamp = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO afk_users (user_id, reason, afk_since) VALUES (?, ?, ?)",
                (user_id, reason, timestamp)
            )
        return True
    except sqlite3.Error as e:
        logger.error(f"Error setting AFK status for user {user_id}: {e}")
        return False

def get_afk_status(user_id: int) -> Tuple[str, str] | None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.cursor().execute(
                "SELECT reason, afk_since FROM afk_users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return res if res else None
    except sqlite3.Error:
        return None

def clear_afk(user_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM afk_users WHERE user_id = ?", (user_id,))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error clearing AFK status for user {user_id}: {e}")
        return False

# --- JOINFILTERS ---
def get_chat_join_settings(chat_id: int) -> tuple[list[str], str]:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT filters, action FROM chat_join_settings WHERE chat_id = ?", (chat_id,))
            row = cursor.fetchone()
            if row:
                filters_json, action = row
                filters_list = json.loads(filters_json) if filters_json else []
                return filters_list, action
            else:
                return [], 'kick'
    except (sqlite3.Error, json.JSONDecodeError) as e:
        logger.error(f"Error getting join settings for chat {chat_id}: {e}")
        return [], 'kick'

def update_chat_join_settings(chat_id: int, filters: list[str] | None = None, action: str | None = None) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            current_filters, current_action = get_chat_join_settings(chat_id)

            new_filters = filters if filters is not None else current_filters
            new_action = action if action is not None else current_action

            filters_json = json.dumps(sorted(list(set(new_filters))))

            cursor.execute(
                "INSERT OR REPLACE INTO chat_join_settings (chat_id, filters, action) VALUES (?, ?, ?)",
                (chat_id, filters_json, new_action)
            )
        return True
    except (sqlite3.Error, json.JSONDecodeError) as e:
        logger.error(f"Error updating join settings for chat {chat_id}: {e}")
        return False

# --- FILTERS ---
def add_or_update_filter(chat_id: int, keyword: str, data: dict) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO chat_filters 
                (chat_id, keyword, reply_text, reply_type, file_id, filter_type, buttons) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    keyword.lower(),
                    data.get('reply_text'),
                    data.get('reply_type', 'text'),
                    data.get('file_id'),
                    data.get('filter_type', 'keyword'),
                    json.dumps(data.get('buttons')) if data.get('buttons') else None,
                )
            )
            return True
    except sqlite3.Error as e:
        logger.error(f"SQLite error adding/updating filter '{keyword}' in chat {chat_id}: {e}")
        return False

def remove_filter(chat_id: int, keyword: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_filters WHERE chat_id = ? AND keyword = ?", (chat_id, keyword.lower()))
            return cursor.rowcount > 0
    except sqlite3.Error: return False
    
def get_all_filters_for_chat(chat_id: int) -> list[dict]:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_filters WHERE chat_id = ?", (chat_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error: return []

# --- BLACKLIST CHAT ---
def blacklist_chat(chat_id: int, chat_name: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            current_timestamp = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT OR IGNORE INTO chat_blacklist (chat_id, chat_name, timestamp) VALUES (?, ?, ?)",
                (chat_id, chat_name, current_timestamp)
            )
            return conn.total_changes > 0
    except sqlite3.Error: return False

def unblacklist_chat(chat_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM chat_blacklist WHERE chat_id = ?", (chat_id,))
            return conn.total_changes > 0
    except sqlite3.Error: return False

def is_chat_blacklisted(chat_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM chat_blacklist WHERE chat_id = ?", (chat_id,))
            return cursor.fetchone() is not None
    except sqlite3.Error: return False

def get_blacklisted_chats() -> list[tuple[int, str, str]]:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT chat_id, chat_name, timestamp FROM chat_blacklist ORDER BY timestamp DESC")
            return cursor.fetchall()
    except sqlite3.Error: return []
