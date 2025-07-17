import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.constants import ChatType, ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.utils import _can_user_perform_action, safe_escape
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- PURGE COMMAND FUNCTION ---
@check_module_enabled("purges")
@custom_handler("purge")
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


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("purge", purge_messages_command))
