import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes

from ..config import GEMINI_API_KEY, OWNER_ID
from ..core.utils import is_privileged_user, is_owner_or_dev, markdown_to_html, get_gemini_response

logger = logging.getLogger(__name__)


# --- AI COMMAND FUNCTIONS ---
async def set_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    global PUBLIC_AI_ENABLED
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /setai attempt by user {user.id}.")
        return

    if not context.args or len(context.args) != 1 or context.args[0].lower() not in ['enable', 'disable']:
        await update.message.reply_text("Usage: /setai <enable/disable>")
        return

    choice = context.args[0].lower()
    
    if choice == 'enable':
        PUBLIC_AI_ENABLED = True
        status_text = "ENABLED"
    else:
        PUBLIC_AI_ENABLED = False
        status_text = "DISABLED"
    
    await update.message.reply_html(
        f"✅ Public access to <b>/askai</b> command has been globally <b>{status_text}</b>."
    )
    logger.info(f"Owner {OWNER_ID} toggled public AI access to: {status_text}")

async def ask_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    can_use_ai = False
    is_regular_user = True
    
    if is_privileged_user(user.id):
        can_use_ai = True
        is_regular_user = False
    elif PUBLIC_AI_ENABLED:
        can_use_ai = True
    
    if not can_use_ai and is_regular_user:
        await update.message.reply_html(
            "🧠 My AI brain is currently <b>DISABLED</b> by my Owner for non-SUDO users 😴\n\n"
            "Maybe try again later; ask my Owner to enable the feature, or just ask a human? 😉"
        )
        return
    elif not can_use_ai:
        return

    if not GEMINI_API_KEY:
        await update.message.reply_text("Sorry, the bot owner has not configured the AI features.")
        return
        
    if not context.args:
        await update.message.reply_text("What do you want to ask? 🤔\nUsage: /askai <your question>")
        return

    prompt = " ".join(context.args)
    
    status_message = await update.message.reply_html("🤔 <code>Thinking...</code>")
    
    try:
        ai_response_markdown = await get_gemini_response(prompt)
        
        ai_response_html = markdown_to_html(ai_response_markdown)

        if len(ai_response_html) > 4096:
             for i in range(0, len(ai_response_html), 4096):
                chunk = ai_response_html[i:i+4096]
                if i == 0:
                    await status_message.edit_text(chunk, parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
        else:
            await status_message.edit_text(ai_response_html, parse_mode=ParseMode.HTML)

    except BadRequest as e:
        logger.warning(f"HTML parsing failed for AI response: {e}. Sending as plain text.")
        await status_message.edit_text(ai_response_markdown)
    except Exception as e:
        logger.error(f"Failed to process /askai request: {e}")
        await status_message.edit_text(f"💥 Houston, we have a problem! My AI core malfunctioned: {type(e).__name__}")


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("setai", set_ai_command))
    application.add_handler(CommandHandler("askai", ask_ai_command))
