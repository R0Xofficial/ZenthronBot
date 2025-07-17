import logging
from telegram import Update
from telegram.constants import ChatType, ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.utils import _can_user_perform_action, send_safe_reply, safe_escape
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- PIN/UNPIN COMMAND FUNCTIONS ---
@check_module_enabled("pins")
@custom_handler("pin")
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

@check_module_enabled("pins")
@custom_handler("unpin")
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


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("pin", pin_message_command))
    application.add_handler(CommandHandler("unpin", unpin_message_command))
