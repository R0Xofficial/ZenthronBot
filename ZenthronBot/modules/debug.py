import logging
import traceback
import html
from telegram import Update, User, Chat
from telegram.constants import ChatType, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.utils import is_owner_or_dev, resolve_user_with_telethon, is_entity_a_user
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)

@check_module_enabled("debug")
@custom_handler("testresolve")
async def test_resolve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id): return
    if not context.args: await update.message.reply_text("Usage: /testresolve <ID or @username>"); return
    
    target_input = context.args[0]
    message = update.effective_message
    await message.reply_text(f"Running resolver for: '{target_input}'...")

    target_entity = await resolve_user_with_telethon(context, target_input, update)

    if not target_entity:
        await message.reply_text("Resolver returned: None.")
        return

    debug_message = "<b>--- DIAGNOSTIC REPORT: Resolver ---</b>\n\n"
    debug_message += f"<b>Input:</b> <code>{target_input}</code>\n"
    debug_message += f"<b>Object Type:</b> <code>{type(target_entity).__name__}</code>\n\n"
    
    debug_message += f"<b>isinstance(User):</b> <code>{isinstance(target_entity, User)}</code>\n"
    debug_message += f"<b>isinstance(Chat):</b> <code>{isinstance(target_entity, Chat)}</code>\n\n"
    
    debug_message += "<b>Key Attributes:</b>\n"
    debug_message += f" • .id: <code>{getattr(target_entity, 'id', 'N/A')}</code>\n"
    debug_message += f" • .type: <code>{getattr(target_entity, 'type', 'N/A')}</code>\n"
    debug_message += f" • .first_name: <code>{html.escape(str(getattr(target_entity, 'first_name', 'N/A')))}</code>\n\n"
    
    verification_result = is_entity_a_user(target_entity)
    debug_message += f"<b>Result of `is_entity_a_user`:</b> <code>{verification_result}</code>\n"
    
    await message.reply_html(debug_message)


@check_module_enabled("debug")
@custom_handler("getupdate")
async def get_update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id): return
    
    message = update.effective_message
    
    if message.reply_to_message:
        update_to_show = message.reply_to_message
        header = "<b>--- Replied-to Message Object ---</b>\n\n"
    else:
        update_to_show = update
        header = "<b>--- Full Update Object ---</b>\n\n"

    try:
        update_json = update_to_show.to_json()
        
        if len(update_json) > 4000:
            import io
            with io.BytesIO(str.encode(update_json)) as file:
                file.name = "update.json"
                await message.reply_document(document=file)
        else:
            await message.reply_html(f"{header}<pre>{html.escape(update_json)}</pre>")
            
    except Exception as e:
        await message.reply_text(f"Error getting update object: {e}")


@check_module_enabled("debug")
@custom_handler("testerror")
async def test_error_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id): return
    await update.message.reply_text("Raising a test exception now...")
    raise ValueError("This is a test exception to check the error handler.")


# --- Handler Loader ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("testresolve", test_resolve_command))
    application.add_handler(CommandHandler("getupdate", get_update_command))
    application.add_handler(CommandHandler("testerror", test_error_command))
