import logging
import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.database import disable_module, enable_module, get_disabled_modules
from ..core.utils import is_owner_or_dev, safe_escape

logger = logging.getLogger(__name__)

def _get_available_modules():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        all_files = os.listdir(current_dir)
        
        modules = [
            f[:-3] for f in all_files 
            if f.endswith('.py') and not f.startswith('_')
        ]
        
        if 'management' in modules:
            modules.remove('management')
            
        return sorted(modules)
    except Exception as e:
        logger.error(f"Could not scan for available modules: {e}")
        return []

async def disable_module_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id):
        return

    available_modules = _get_available_modules()
    if not context.args or context.args[0] not in available_modules:
        await update.message.reply_html(
            f"<b>Usage:</b> /disablemodule <module_name>\n"
            f"<b>Available:</b> <code>{', '.join(available_modules)}</code>"
        )
        return

    module_name = context.args[0]
    if database.disable_module(module_name):
        await update.message.reply_text(f"✅ Module '<code>{safe_escape(module_name)}</code>' has been disabled.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"Module '<code>{safe_escape(module_name)}</code>' was already disabled or an error occurred.", parse_mode="HTML")

async def enable_module_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id):
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /enablemodule <module_name>")
        return
        
    module_name = context.args[0]
    if database.enable_module(module_name):
        await update.message.reply_text(f"✅ Module '<code>{safe_escape(module_name)}</code>' has been enabled.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"Module '<code>{safe_escape(module_name)}</code>' was already enabled or an error occurred.", parse_mode="HTML")

async def list_modules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id):
        return
        
    disabled_modules = database.get_disabled_modules()
    available_modules = _get_available_modules()
    
    message = "<b>Module Status:</b>\n\n"
    for module in available_modules:
        status = "🔴 Disabled" if module in disabled_modules else "🟢 Enabled"
        message += f"• <code>{module}</code>: {status}\n"
        
    await update.message.reply_html(message)


def load_handlers(application: Application):
    application.add_handler(CommandHandler("disablemodule", disable_module_command))
    application.add_handler(CommandHandler("enablemodule", enable_module_command))
    application.add_handler(CommandHandler("listmodules", list_modules_command))
