import logging
from datetime import datetime, timezone
from telegram import Update, constants
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ApplicationHandlerStop

from ..core.database import set_afk, get_afk_status, clear_afk, get_user_from_db_by_username
from ..core.utils import send_safe_reply, get_readable_time_delta, create_user_html_link, safe_escape
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- AFK COMMAND AND HANDLER FUNCTIONS ---
@check_module_enabled("afk")
@command_control("afk")
@custom_handler("afk")
async def afk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    if message.sender_chat:
        await send_safe_reply(update, context, text="🧐 Channels cannot be AFK.")
        return

    reason = " ".join(context.args) if context.args else "No reason"
    user_display_name = safe_escape(user.full_name or user.first_name)
    if set_afk(user.id, reason):
        await message.reply_html(f"{user_display_name} is now AFK!\n<b>Reason:</b> {safe_escape(reason)}")
    else:
        await message.reply_text("Could not set AFK status due to a database error.")

@check_module_enabled("afk")
@command_control("afk")
async def afk_brb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message or not message.text:
        return

    if message.sender_chat:
        await send_safe_reply(update, context, text="🧐 Channels cannot be AFK.")
        return

    words = message.text.lower().split()

    if words and words[0] == 'brb':
        parts = message.text.split(' ', 1)
        reason = parts[1] if len(parts) > 1 else "No reason"
        user_display_name = safe_escape(user.full_name or user.first_name)
        if set_afk(user.id, reason):
            await message.reply_html(f"{user_display_name} is now AFK!\n<b>Reason:</b> {safe_escape(reason)}")
            
            raise ApplicationHandlerStop
        else:
            await message.reply_text("Could not set AFK status due to a database error.")

@check_module_enabled("afk")
@command_control("afk")
async def check_afk_return(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    afk_status = get_afk_status(user.id)
    if afk_status:
        clear_afk(user.id)
        user_display_name = safe_escape(user.full_name or user.first_name)
        afk_since_str = afk_status[1]
        try:
            afk_start_time = datetime.fromisoformat(afk_since_str)
            duration = datetime.now(timezone.utc) - afk_start_time
            duration_str = get_readable_time_delta(duration)
            time_info = f"You've been AFK for: <code>{duration_str}</code>"
        except (ValueError, TypeError):
            time_info = ""

        await message.reply_html(f"Welcome back, {user_display_name}!\n{time_info}.")

@check_module_enabled("afk")
@command_control("afk")
async def afk_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if not message:
        return
    
    users_to_check = set()

    if message.reply_to_message and message.reply_to_message.from_user:
        users_to_check.add(message.reply_to_message.from_user.id)
        
    if message.entities:
        for entity in message.entities:
            if entity.type == constants.MessageEntityType.TEXT_MENTION and entity.user:
                users_to_check.add(entity.user.id)
            elif entity.type == constants.MessageEntityType.MENTION:
                username = message.text[entity.offset:entity.offset + entity.length]
                mentioned_user = get_user_from_db_by_username(username)
                if mentioned_user:
                    users_to_check.add(mentioned_user.id)

    if not users_to_check:
        return

    for user_id in users_to_check:
        afk_status = get_afk_status(user_id)
        if afk_status:
            try:
                member = await chat.get_member(user_id)
                if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                    continue
            except TelegramError:
                continue
            try:
                user = await context.bot.get_chat(user_id)
                reason = afk_status[0]
                afk_since_str = afk_status[1]
                
                afk_start_time = datetime.fromisoformat(afk_since_str)
                duration = datetime.now(timezone.utc) - afk_start_time
                duration_str = get_readable_time_delta(duration)
                user_display_name = safe_escape(user.full_name or user.first_name)
                await message.reply_html(
                    f"Hey! {user_display_name} is currently AFK!\nLast seen: <code>{duration_str}</code> ago.\n"
                    f"<b>Reason:</b> {safe_escape(reason)}"
                )
            except Exception as e:
                logger.warning(f"Could not send AFK notification for user {user_id}: {e}")


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("afk", afk_command))
