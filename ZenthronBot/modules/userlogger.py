import logging
import sqlite3
from telegram import Update
from telegram.constants import ChatType
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from ..config import DB_NAME
from ..core.database import update_user_in_db, add_chat_to_db
from ..core.decorators import check_module_enabled

logger = logging.getLogger(__name__)


# --- PASSIVE USER AND CHAT LOGGING FUNCTION ---
@check_module_enabled("userlogger")
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


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    pass
