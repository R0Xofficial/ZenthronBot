import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.database import disable_command_in_chat, enable_command_in_chat, get_disabled_commands_in_chat
from ..core.utils import safe_escape, _can_user_perform_action
from ..core.registry import MANAGEABLE_COMMANDS

logger = logging.getLogger(__name__)

async def disable_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    can_disable = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=False
    )
    if not can_disable:
        return

    command_name_to_disable = context.args[0].lower().lstrip('/') if context.args else ""
    
    if not command_name_to_disable or command_name_to_disable not in MANAGEABLE_COMMANDS:
        await update.message.reply_html(
            f"<b>Usage:</b> /disable &lt;command name&gt;\n"
            f"This command doesn't exist or cannot be managed."
        )
        return

    if disable_command_in_chat(update.effective_chat.id, command_name_to_disable):
        await update.message.reply_text(
            f"✅ Command <code>/{safe_escape(command_name_to_disable)}</code> is now disabled for non-admins in this chat.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("This command was already disabled or an error occurred.")

async def enable_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    can_enable = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=False
    )
    if not can_enable:
        return
    
    command_name_to_enable = context.args[0].lower().lstrip('/') if context.args else ""
    
    if not command_name_to_enable or command_name_to_enable not in MANAGEABLE_COMMANDS:
        await update.message.reply_html("<b>Usage:</b> /enable &lt;command name&gt;\nThat command doesn't exist or isn't managed.")
        return
        
    if enable_command_in_chat(update.effective_chat.id, command_name_to_enable):
        await update.message.reply_text(
            f"✅ Command <code>/{safe_escape(command_name_to_enable)}</code> is now enabled for everyone in this chat.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("This command was already enabled or an error occurred.")

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    can_see_settings = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission."
    )
    if not can_see_settings:
        return

    disabled_commands = get_disabled_commands_in_chat(update.effective_chat.id)
    
    message = f"<b>Settings for {safe_escape(update.effective_chat.title)}:</b>\n\n"
    
    for cmd in sorted(list(MANAGEABLE_COMMANDS)):
        status = "🔴 Disabled (for non-admins)" if cmd in disabled_commands else "🟢 Enabled"
        message += f"• <code>/{cmd}</code>: {status}\n"
        
    await update.message.reply_html(message)


def load_handlers(application: Application):
    application.add_handler(CommandHandler("disable", disable_command))
    application.add_handler(CommandHandler("enable", enable_command))
    application.add_handler(CommandHandler("settings", settings_command))
