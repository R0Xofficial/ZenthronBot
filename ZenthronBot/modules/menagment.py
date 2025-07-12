import logging
import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..config import OWNER_ID
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
    user = update.effective_user
    
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /disablemodule attempt by user {user.id}.")
        return

    PROTECTED_MODULES = ['management']

    if not context.args or len(context.args) != 1:
        await update.message.reply_html("<b>Usage:</b> /disablemodule &lt;module name&gt;")
        return

    module_name_to_disable = context.args[0]

    if module_name_to_disable in PROTECTED_MODULES:
        await update.message.reply_text(f"Module '<code>{module_name}</code>' is protected and cannot be disabled.", parse_mode=ParseMode.HTML)
        return
        
    available_modules = _get_available_modules()
    if module_name_to_disable not in available_modules:
        await update.message.reply_html(
            f"Unknown module '<code>{safe_escape(module_name_to_disable)}</code>'.\n"
            f"<b>Available to disable:</b> <code>{', '.join(available_modules)}</code>"
        )
        return

    if disable_module(module_name_to_disable):
        await update.message.reply_text(f"✅ Module '<code>{safe_escape(module_name_to_disable)}</code>' has been disabled. Commands from this module will not work.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"Module '<code>{safe_escape(module_name_to_disable)}</code>' was already disabled or an error occurred.", parse_mode=ParseMode.HTML)

async def enable_module_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /enablemodule attempt by user {user.id}.")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /enablemodule <module name>")
        return
        
    module_name = context.args[0]
    if enable_module(module_name):
        await update.message.reply_text(f"✅ Module '<code>{safe_escape(module_name)}</code>' has been enabled.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"Module '<code>{safe_escape(module_name)}</code>' was already enabled or an error occurred.", parse_mode=ParseMode.HTML)

async def list_modules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listmodules attempt by user {user.id}.")
        return
        
    disabled_modules = get_disabled_modules()
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
