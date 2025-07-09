import logging
import random
import sqlite3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import config
from modules.database import (
    set_welcome_setting, get_welcome_settings, set_goodbye_setting, get_goodbye_settings,
    set_clean_service, should_clean_service, add_chat_to_db, remove_chat_from_db,
    is_dev_user, is_sudo_user, is_support_user
)
from modules.utils import (
    _can_user_perform_action, send_safe_reply, safe_escape,
    format_message_text, send_critical_log
)
from .constants import (
    OWNER_WELCOME_TEXTS, DEV_WELCOME_TEXTS, SUDO_WELCOME_TEXTS,
    SUPPORT_WELCOME_TEXTS, GENERIC_WELCOME_TEXTS, GENERIC_GOODBYE_TEXTS
)

logger = logging.getLogger(__name__)


# --- WELCOME/GOODBYE COMMAND AND HANDLER FUNCTIONS ---
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


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("welcome", welcome_command))
    application.add_handler(CommandHandler("setwelcome", set_welcome_command))
    application.add_handler(CommandHandler("resetwelcome", reset_welcome_command))
    application.add_handler(CommandHandler("goodbye", goodbye_command))
    application.add_handler(CommandHandler("setgoodbye", set_goodbye_command))
    application.add_handler(CommandHandler("resetgoodbye", reset_goodbye_command))
    application.add_handler(CommandHandler("welcomehelp", welcome_help_command))
    application.add_handler(CommandHandler("cleanservice", set_clean_service_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_group_members))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_group_member))
