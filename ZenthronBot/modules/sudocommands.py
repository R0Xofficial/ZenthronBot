import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, ContextTypes

from modules.utils import is_privileged_user
from modules.database import is_dev_user, is_sudo_user, is_support_user
from modules.utils import is_owner_or_dev, send_safe_reply
from constants import (
    ADMIN_NOTE_TEXT, SUPPORT_COMMANDS_TEXT, SUDO_COMMANDS_TEXT,
    DEVELOPER_COMMANDS_TEXT, OWNER_COMMANDS_TEXT
)

logger = logging.getLogger(__name__)


# --- SUDO COMMANDS LIST FUNCTION ---
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


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("sudocmds", sudo_commands_command))
