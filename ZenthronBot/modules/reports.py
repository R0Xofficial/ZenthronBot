import logging
from telegram import Update, Chat, User
from telegram.constants import ChatType, ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.utils import resolve_user_with_telethon, create_user_html_link, safe_escape
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- REPORT COMMAND FUNCTION ---
@check_module_enabled("reports")
@command_control("reports")
@custom_handler("report")
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    reporter = update.effective_user
    message = update.message

    if not message or chat.type == ChatType.PRIVATE:
        return

    try:
        reporter_member = await chat.get_member(reporter.id)
        if reporter_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            logger.info(f"Report command ignored: used by admin {reporter.id} in chat {chat.id}.")
            return
    except TelegramError as e:
        logger.warning(f"Could not get status for reporter {reporter.id} in /report: {e}")

    target_entity: Chat | User | None = None
    args_for_reason = list(context.args)

    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        args_for_reason = list(context.args[1:])
        target_entity = await resolve_user_with_telethon(context, target_input, update)
    
    if not target_entity:
        return
        
    reason = " ".join(args_for_reason) if args_for_reason else "No specific reason provided."

    try:
        target_member = await chat.get_member(target_entity.id)
        if target_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            logger.info(f"Report command ignored: target {target_entity.id} is an admin in chat {chat.id}.")
            return
    except TelegramError as e:
        if "user not found" not in str(e).lower():
            logger.warning(f"Could not get status for target {target_entity.id} in /report: {e}")

    reporter_mention = create_user_html_link(reporter)
    
    if isinstance(target_entity, User) or (isinstance(target_entity, Chat) and target_entity.type == ChatType.PRIVATE):
        target_display = create_user_html_link(target_entity)
    else:
        target_display = safe_escape(target_entity.title or f"{target_entity.id}")

    report_message = (
        f"📢 <b>Report for @admins</b>\n\n"
        f"<b>Reported User:</b> {target_display} [<code>{target_entity.id}</code>]\n"
        f"<b>Reason:</b> {safe_escape(reason)}\n"
        f"<b>Reported by:</b> {reporter_mention} [<code>{reporter.id}</code>]"
    )

    await context.bot.send_message(chat_id=chat.id, text=report_message, parse_mode=ParseMode.HTML)

    try:
        await message.delete()
    except Exception:
        logger.warning(f"Could not delete report command message in chat {chat.id}.")


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("report", report_command))
