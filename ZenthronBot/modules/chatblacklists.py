import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

from ..core.database import blacklist_chat, unblacklist_chat, get_blacklisted_chats, is_chat_blacklisted
from ..core.utils import is_owner_or_dev, safe_escape
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)

@check_module_enabled("chatblacklists")
async def check_blacklisted_chat_on_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.my_chat_member:
        return

    new_member_status = update.my_chat_member.new_chat_member
    chat = update.my_chat_member.chat
    
    was_added = new_member_status.status in ["member", "administrator"]

    if was_added and is_chat_blacklisted(chat.id):
        logger.warning(f"Bot was added to a blacklisted chat: {chat.title} ({chat.id}). Leaving immediately.")
        try:
            await context.bot.leave_chat(chat.id)
        except Exception as e:
            logger.error(f"Failed to leave blacklisted chat {chat.id}: {e}")

@check_module_enabled("chatblacklists")
@custom_handler("blchat")
async def blacklist_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id): 
      logger.warning(f"Unauthorized /blchat attempt by user {user.id}.")
      return

    chat_id_to_bl = update.effective_chat.id
    if context.args:
        try:
            chat_id_to_bl = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid chat ID.")
            return

    if blacklist_chat(chat_id_to_bl):
        await update.message.reply_html(f"✅ Chat <code>{chat_id_to_bl}</code> has been blacklisted.")
        try:
            await context.bot.leave_chat(chat_id_to_bl)
            await update.message.reply_text("Bot was in that chat and has now left.")
        except TelegramError:
            pass
    else:
        await update.message.reply_html("This chat is already blacklisted.")

@check_module_enabled("chatblacklists")
@custom_handler("unblchat")
async def unblacklist_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id): 
      logger.warning(f"Unauthorized /unblchat attempt by user {user.id}.")
      return
    
    chat_id_to_unbl = update.effective_chat.id
    if context.args:
        try:
            chat_id_to_unbl = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid chat ID.")
            return

    if unblacklist_chat(chat_id_to_unbl):
        await update.message.reply_html(f"✅ Chat <code>{chat_id_to_unbl}</code> has been unblacklisted.")
    else:
        await update.message.reply_html("This chat was not on the blacklist.")

@check_module_enabled("chatblacklists")
@custom_handler("blchats")
async def list_blacklisted_chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id): 
      logger.warning(f"Unauthorized /blchats attempt by user {user.id}.")
      return

    blacklisted = get_blacklisted_chats()
    if not blacklisted:
        await update.message.reply_text("No chats are currently blacklisted.")
        return
        
    message = "<b>Blacklisted Chats:</b>\n\n"
    for chat_id in blacklisted:
        message += f"• <code>{chat_id}</code>\n"
    await update.message.reply_html(message)


def load_handlers(application: Application):
    application.add_handler(CommandHandler("blchat", blacklist_chat_command))
    application.add_handler(CommandHandler("unblchat", unblacklist_chat_command))
    application.add_handler(CommandHandler("blchats", list_blacklisted_chats_command))
