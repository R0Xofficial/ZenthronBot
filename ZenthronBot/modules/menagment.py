# ZenthronBot/modules/management.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core import database
from ..core.utils import is_owner_or_dev

logger = logging.getLogger(__name__)

MANAGEABLE_MODULES = [
    "afk", "ai", "bans", "blacklists", "chatadmins", "core", "fun", "globalbans", "kicks", "misc", "mutes", "notes", "pins", "promotes", "purges", "reports", "rules", "sudocommands", "userlogger", "warns", "welcomes", "zombies"
]

async def disable_module_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id):
        return

    if not context.args or context.args[0] not in MANAGEABLE_MODULES:
        await update.message.reply_text(f"Usage: /disablemodule <module_name>\nAvailable: {', '.join(MANAGEABLE_MODULES)}")
        return

    module_name = context.args[0]
    if database.disable_module(module_name):
        await update.message.reply_text(f"✅ Module '{module_name}' has been disabled.")
    else:
        await update.message.reply_text(f"Module '{module_name}' was already disabled or an error occurred.")

async def enable_module_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id):
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /enablemodule <module_name>")
        return
        
    module_name = context.args[0]
    if database.enable_module(module_name):
        await update.message.reply_text(f"✅ Module '{module_name}' has been enabled.")
    else:
        await update.message.reply_text(f"Module '{module_name}' was already enabled or an error occurred.")

async def list_modules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id):
        return
        
    disabled_modules = database.get_disabled_modules()
    
    message = "<b>Module Status:</b>\n\n"
    for module in MANAGEABLE_MODULES:
        status = "🔴 Disabled" if module in disabled_modules else "🟢 Enabled"
        message += f"• <code>{module}</code>: {status}\n"
        
    await update.message.reply_html(message)

def load_handlers(application: Application):
    application.add_handler(CommandHandler("disablemodule", disable_module_command))
    application.add_handler(CommandHandler("enablemodule", enable_module_command))
    application.add_handler(CommandHandler("listmodules", list_modules_command))
