import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.database import disable_command_in_chat, enable_command_in_chat, get_disabled_commands_in_chat
from ..core.utils import safe_escape, _can_user_perform_action
from ..core.decorators import check_module_enabled

logger = logging.getLogger(__name__)

@check_module_enabled("disables")
async def disable_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    can_disable = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission."
    )
    if not can_disable:
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_html("<b>Usage:</b> /disable &lt:command name&gt;")
        return

    command_name = context.args[0].lower().lstrip('/')
    if disable_command_in_chat(update.effective_chat.id, command_name):
        await update.message.reply_text(
            f"✅ Command <code>/{safe_escape(command_name)}</code> is now disabled for non-admins in this chat.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("This command was already disabled or an error occurred.")

@check_module_enabled("disables")
async def enable_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    can_enable = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission."
    )
    if not can_enable:
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_html("<b>Usage:</b> /enable &lt:command name&gt;")
        return
        
    command_name = context.args[0].lower().lstrip('/')
    if enable_command_in_chat(update.effective_chat.id, command_name):
        await update.message.reply_text(
            f"✅ Command <code>/{safe_escape(command_name)}</code> is now enabled for everyone in this chat.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("This command was already enabled or an error occurred.")

@check_module_enabled("disables")
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    can_see_settings = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Only chat admins can see chat settings."
    )
    if not can_see_settings:
        return

    disabled_commands = get_disabled_commands_in_chat(update.effective_chat.id)
    
    if not disabled_commands:
        message = f"<b>Settings for {safe_escape(update.effective_chat.title)}:</b>\n\nAll commands are currently enabled for everyone."
    else:
        message = f"<b>Settings for {safe_escape(update.effective_chat.title)}:</b>\n\nThe following commands are <b>disabled</b> for non-admins:\n"
        for cmd in sorted(disabled_commands):
            message += f"• <code>/{cmd}</code>\n"
        
    await update.message.reply_html(message)


def load_handlers(application: Application):
    application.add_handler(CommandHandler("disable", disable_command))
    application.add_handler(CommandHandler("enable", enable_command))
    application.add_handler(CommandHandler("settings", settings_command))
