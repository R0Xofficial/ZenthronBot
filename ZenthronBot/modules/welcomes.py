import logging
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..config import OWNER_ID, DB_NAME, APPEAL_CHAT_USERNAME
from ..core.database import (
    set_welcome_setting, get_welcome_settings, set_goodbye_setting, get_goodbye_settings,
    set_clean_service, should_clean_service, add_chat_to_db, remove_chat_from_db,
    is_dev_user, is_sudo_user, is_support_user, is_chat_blacklisted, update_user_in_db,
    is_gban_enforced, get_gban_reason
)
from ..core.utils import _can_user_perform_action, send_safe_reply, safe_escape, format_message_text, send_critical_log
from ..core.constants import OWNER_WELCOME_TEXTS, DEV_WELCOME_TEXTS, SUDO_WELCOME_TEXTS, SUPPORT_WELCOME_TEXTS, GENERIC_WELCOME_TEXTS, GENERIC_GOODBYE_TEXTS
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- WELCOME/GOODBYE COMMAND AND HANDLER FUNCTIONS ---
@check_module_enabled("welcomes")
@custom_handler("welcome")
async def welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't manage welcome in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return

    if context.args and context.args[0].lower() in ['yes', 'on', 'off', 'no']:
        is_on = context.args[0].lower() == 'on' or context.args[0].lower() == 'yes'
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

@check_module_enabled("welcomes")
@custom_handler("setwelcome")
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

@check_module_enabled("welcomes")
@custom_handler("resetwelcome")
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

@check_module_enabled("welcomes")
@custom_handler("goodbye")
async def goodbye_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't manage goodbye in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return

    if context.args and context.args[0].lower() in ['yes', 'on', 'off', 'no']:
        is_on = context.args[0].lower() == 'on' or context.args[0].lower() == 'yes'
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

@check_module_enabled("welcomes")
@custom_handler("setgoodbye")
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

@check_module_enabled("welcomes")
@custom_handler("resetgoodbye")
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

@check_module_enabled("welcomes")
@command_control("welcomehelp")
@custom_handler("welcomehelp")
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

@check_module_enabled("welcomes")
@custom_handler("cleanservice")
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

    if context.args and context.args[0].lower() not in ['yes', 'on', 'off', 'no']:
        await update.message.reply_text("Usage: /cleanservice <yes/on/off/no>")
        return
        
    is_on = context.args[0].lower() == 'on' or context.args[0].lower() == 'yes'
    
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

@check_module_enabled("welcomes")
async def handle_new_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.new_chat_members:
        return
    chat = update.effective_chat

    if is_chat_blacklisted(chat.id):
        return
    
    if any(member.id == context.bot.id for member in update.message.new_chat_members):
        logger.info(f"Bot joined chat: {chat.title} ({chat.id})")
        add_chat_to_db(chat.id, chat.title or f"Untitled Chat {chat.id}")
        if OWNER_ID:
            safe_chat_title = safe_escape(chat.title or f"Chat ID {chat.id}")
            link_line = f"\n<b>Link:</b> @{chat.username}" if chat.username else ""
            log_text = (f"<b>#ADDEDTOGROUP</b>\n\n<b>Name:</b> {safe_chat_title}\n<b>ID:</b> <code>{chat.id}</code>{link_line}")
            await send_critical_log(context, log_text)
        try:
            bot_username = context.bot.username
            
            welcome_message_to_group = (
                f"👋 Hello! I'm <b>Zenthron</b>, your new group assistant.\n\n"
                f"I'm here to help you manage the chat and have some fun. "
                f"To see what I can do, click button 'Get Help in PM'.\n\n"
                f"<b>I was added by {update.message.from_user.mention_html()}</b>.\n"
                f"<i>For any questions or issues, please contact our support team at {APPEAL_CHAT_USERNAME}.</i>"
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

    if should_clean_service(chat.id):
        try:
            await update.message.delete()
        except Exception:
            pass

    welcome_enabled, custom_text = get_welcome_settings(chat.id)

    for member in update.message.new_chat_members:
        update_user_in_db(member)
        if is_gban_enforced(chat.id) and get_gban_reason(member.id):
            continue

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

@check_module_enabled("welcomes")
async def handle_left_group_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.left_chat_member:
        return
    
    chat = update.effective_chat
    left_member = update.message.left_chat_member
    update_user_in_db(left_member)

    if left_member.id == context.bot.id:
        logger.info(f"Bot removed from group cache {chat.id}.")
        remove_chat_from_db(chat.id)
        return

    if should_clean_service(chat.id):
        try:
            await update.message.delete()
        except Exception:
            pass

    if is_gban_enforced(chat.id) and get_gban_reason(left_member.id):
        return

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
