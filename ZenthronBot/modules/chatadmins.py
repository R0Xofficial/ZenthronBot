import logging
import io
import re
from telegram import Update
from telegram.constants import ChatType
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.utils import safe_escape
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- LIST ADMINS COMMAND FUNCTION ---
@check_module_enabled("chatadmins")
@command_control("chatadmins")
@custom_handler("chatadmins")
async def list_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        await update.message.reply_text("Huh? This command can only be used in chats.")
        return

    try:
        administrators = await context.bot.get_chat_administrators(chat_id=chat.id)
    except TelegramError as e:
        logger.error(f"Failed to get admin list for chat {chat.id} ('{chat.title}'): {e}")
        await update.message.reply_text(f"Skrrrt... Some supernatural force is preventing me from getting a list of administrators for this chat. Reason: {safe_escape(str(e))}")
        return
    except Exception as e:
        logger.error(f"Unexpected error getting admin list for chat {chat.id}: {e}", exc_info=True)
        await update.message.reply_text(f"BOMBOCLAT! There was a problem retrieving the administrator list.")
        return

    if not administrators:
        await update.message.reply_text("There seem to be no admins in this chat. Unless I'm blind and need glasses 👓")
        return

    chat_title_display = safe_escape(chat.title or chat.first_name or f"Chat ID {chat.id}")
    response_lines = [f"<b>🛡️ Admin list in {chat_title_display}:</b>\n"]

    creator_line: str | None = None

    for admin_member in administrators:
        admin_user = admin_member.user
        
        user_display_name = ""
        if admin_user.username:
            user_display_name = f"<a href=\"tg://user?id={admin_user.id}\">@{safe_escape(admin_user.username)}</a>"
        elif admin_user.full_name:
            user_display_name = f"<a href=\"tg://user?id={admin_user.id}\">{safe_escape(admin_user.full_name)}</a>"
        elif admin_user.first_name:
            user_display_name = f"<a href=\"tg://user?id={admin_user.id}\">{safe_escape(admin_user.first_name)}</a>"
        else:
            user_display_name = f"<a href=\"tg://user?id={admin_user.id}\">User {admin_user.id}</a>"

        admin_info_line = f"• {user_display_name}"

        custom_title = getattr(admin_member, 'custom_title', None)
        is_anonymous = getattr(admin_member, 'is_anonymous', False)

        if is_anonymous:
            admin_info_line += " <i>(Anonymous Admin)</i>"
        
        if custom_title:
            admin_info_line += f" (<code>{safe_escape(custom_title)}</code>)"
        
        if admin_member.status == "creator":
            admin_info_line += " 👑"
            creator_line = admin_info_line
        else:
            response_lines.append(admin_info_line)

    if creator_line:
        response_lines.insert(1, creator_line)

    message_text = "\n".join(response_lines)
    
    if len(message_text) > 4090:
        logger.info(f"Admin list for chat {chat.id} is too long, attempting to send as a file.")
        try:
            import io
            file_content = "\n".join(response_lines).replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")
            file_content = file_content.replace("</a>", "").replace("✨", "").replace("🛡️", "")
            file_content = re.sub(r'<a href="[^"]*">', '', file_content)

            bio = io.BytesIO(file_content.encode('utf-8'))
            bio.name = f"admin_list_{chat.id}.txt"
            await update.message.reply_document(document=bio, caption=f"🛡️ Admin list for {chat_title_display} is too long to display directly. See the attached file.")
        except Exception as e_file:
            logger.error(f"Failed to send long admin list as file: {e_file}")
            await update.message.reply_text("Error: The admin list is too long to display, and I couldn't send it as a file.")
    else:
        await update.message.reply_html(message_text, disable_web_page_preview=True)


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler(["listadmins", "admins"], list_admins_command))
