import asyncio
import html
import io
import json
import logging
import random
import re
import sqlite3
import subprocess
from datetime import timedelta, datetime, timezone
from typing import List, Tuple

import google.generativeai as genai
import requests
import speedtest
import telegram
from telegram import Update, User, Chat, constants, ChatPermissions
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import TelegramError, BadRequest
from telegram.ext import ContextTypes
from telethon import TelegramClient
from telethon.tl.types import User as TelethonUser

from ..config import OWNER_ID, TENOR_API_KEY, GEMINI_API_KEY, LOG_CHAT_ID, ADMIN_LOG_CHAT_ID, DB_NAME
from .database import (
    is_dev_user, is_sudo_user, is_support_user,
    get_user_from_db_by_id, get_user_from_db_by_username,
    update_user_in_db
)
from .async_utils import aioify

logger = logging.getLogger(__name__)


# --- UTILITY AND HELPER FUNCTIONS ---
# --- HTML DICTIONARY ---
def safe_escape(text: str) -> str:
    escaped_text = html.escape(str(text))
    return escaped_text.replace("&#x27;", "’")

# --- TARGET CHECKING AND PROTECT ---
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

# --- THEMED GIFS ---
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
        "limit": 15, 
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

# --- CREATE PROFILE LINK ---
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

# --- MARKDOWN TRANSLATOR ---
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

# --- UTILITY ---
def telethon_entity_to_ptb_user(entity) -> User | Chat | None:
    if isinstance(entity, TelethonUser):
        return User(
            id=entity.id,
            first_name=entity.first_name or "",
            is_bot=entity.bot or False,
            last_name=entity.last_name,
            username=entity.username,
            language_code=getattr(entity, 'lang_code', None)
        )
    
    elif hasattr(entity, 'id') and hasattr(entity, 'type'):
        return Chat(
            id=entity.id,
            type=entity.type,
            first_name=getattr(entity, 'first_name', None),
            title=getattr(entity, 'title', None),
            username=getattr(entity, 'username', None)
        )
    return None

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
        logger.info(f"Resolving '{target_input}' using DB...")
        entity_from_db = get_user_from_db_by_id(identifier)
    else:
        entity_from_db = get_user_from_db_by_username(identifier)
    
    if entity_from_db:
        return entity_from_db
    else:
        logger.warning(f"DB failed for '{target_input}': User not found.")

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

def is_entity_a_user(entity: object | None) -> bool:
    if not entity:
        return False
        
    if hasattr(entity, 'type'):
        return getattr(entity, 'type') == 'private'
        
    if isinstance(entity, User):
        return True
        
    return False
    
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
    failure_message: str | None, 
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

    if failure_message is not None:
        await send_safe_reply(update, context, text=failure_message)
        
    return False

# --- LOG ---
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

async def send_critical_log(context: ContextTypes.DEFAULT_TYPE, message: str, parse_mode: str = ParseMode.HTML) -> None:
    target_id = ADMIN_LOG_CHAT_ID or OWNER_ID

    if not target_id:
        logger.error("Neither ADMIN_LOG_CHAT_ID nor OWNER_ID are set. Cannot send critical log.")
        return

    try:
        await context.bot.send_message(chat_id=target_id, text=message, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Failed to send critical log to target {target_id}: {e}")
        if target_id == ADMIN_LOG_CHAT_ID and OWNER_ID:
            logger.warning(f"Falling back to send critical log to OWNER_ID ({OWNER_ID}).")
            try:
                fallback_message = f"<b>[Fallback from Log Chat]</b>\n\n{message}"
                await context.bot.send_message(chat_id=OWNER_ID, text=fallback_message, parse_mode=parse_mode)
            except Exception as e_owner:
                logger.critical(f"CRITICAL: Failed to send critical log even to OWNER_ID: {e_owner}")

# --- PERMISSIONS ---
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

# --- TEXT FORMATING ---
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

# --- AI ---
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

# --- SPEEDTEST ---
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

@aioify
def run_speed_test_async() -> str:
    return run_speed_test_blocking()

# --- UNGBAN ---
async def propagate_unban(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    target_user_id = job_data['target_user_id']
    command_chat_id = job_data['command_chat_id']
    user_display = job_data['user_display']
    command_message_id = job_data['command_message_id']

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

    success_message = f"✅ Done! {user_display} [<code>{target_user_id}</code>] has been <b>globally unbanned</b>."
    
    try:
        await context.bot.send_message(
            chat_id=command_chat_id,
            text=success_message,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=command_message_id
        )
    except Exception as e:
        logger.warning(f"Failed to send messages as reply: {e}.")
        try:
            await context.bot.send_message(
                chat_id=command_chat_id,
                text=success_message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e2:
            logger.warning(f"Failed to send as normal message: {e2}.")
