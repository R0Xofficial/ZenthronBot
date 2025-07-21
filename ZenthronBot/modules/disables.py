import logging
from telegram import Update
from telegram.constants import ParseMode, ChatType
from telegram.ext import Application, CommandHandler, ContextTypes
from collections import defaultdict

from ..core.constants import DISABLES_HELP_TEXT
from ..core.database import disable_command_in_chat, enable_command_in_chat, get_disabled_commands_in_chat
from ..core.utils import safe_escape, _can_user_perform_action, send_safe_reply
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)

@check_module_enabled("disables")
@custom_handler("disable")
async def disable_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't disable command in private chat...")
        return
    
    can_disable = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=False
    )
    if not can_disable:
        return

    command_to_disable = context.args[0].lower().lstrip('') if context.args else ""
    if command_to_disable == 'all':
        manageable_commands = context.bot_data.get("manageable_commands", set())
        if not manageable_commands:
            await update.message.reply_text("There are no manageable commands to disable.")
            return

        disabled_count = 0
        for command_name in manageable_commands:
            if disable_command_in_chat(chat.id, command_name):
                disabled_count += 1
        
        await update.message.reply_html(
            f"✅ Disabled <b>{disabled_count}</b> command(s) for non-admins in this chat."
        )
        return

    manageable_commands = context.bot_data.get("manageable_commands", set())
    if not command_to_disable or command_to_disable not in manageable_commands:
        await update.message.reply_html(
            f"Usage: /disable &lt;command name&gt;\n"
            f"This command/commands doesn't exist or cannot be managed."
        )
        return

    if disable_command_in_chat(update.effective_chat.id, command_to_disable):
        await update.message.reply_text(
            f"✅ <code>{safe_escape(command_to_disable)}</code> is now disabled for non-admins in this chat.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("This command was already disabled or an error occurred.")

@check_module_enabled("disables")
@custom_handler("enable")
async def enable_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't enable command in private chat...")
        return
    
    can_enable = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=False
    )
    if not can_enable:
        return
    
    command_to_enable = context.args[0].lower().lstrip('') if context.args else ""
    if command_to_enable == 'all':
        disabled_in_chat = get_disabled_commands_in_chat(chat.id)
        if not disabled_in_chat:
            await update.message.reply_text("All manageable commands are already enabled.")
            return

        enabled_count = 0
        for command_name in disabled_in_chat:
            if enable_command_in_chat(chat.id, command_name):
                enabled_count += 1
        
        await update.message.reply_html(
            f"✅ Enabled <b>{enabled_count}</b> command(s) for everyone in this chat."
        )
        return
    
    manageable_commands = context.bot_data.get("manageable_commands", set())
    if not command_to_enable or command_to_enable not in manageable_commands:
        await update.message.reply_html("Usage: /enable &lt;command name&gt;\nThat command doesn't exist or isn't managed.")
        return
        
    if enable_command_in_chat(update.effective_chat.id, command_to_enable):
        await update.message.reply_text(
            f"✅ <code>{safe_escape(command_to_enable)}</code> is now enabled for everyone in this chat.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("This command was already enabled or an error occurred.")

@check_module_enabled("disables")
@custom_handler("settings")
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't check settings in private chat...")
        return
    
    can_see_settings = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission."
    )
    if not can_see_settings:
        return

    manageable_commands = context.bot_data.get("manageable_commands", set())
    disabled_commands = get_disabled_commands_in_chat(update.effective_chat.id)
    
    message = f"<b>Settings for {safe_escape(update.effective_chat.title)}:</b>\n\n"
    
    if not manageable_commands:
        message += "No manageable commands found."
    else:
        for cmd in sorted(list(manageable_commands)):
            status = "🔴 Disabled" if cmd in disabled_commands else "🟢 Enabled"
            message += f"• <code>{cmd}</code>: {status}\n"
        
    await update.message.reply_html(message)

@check_module_enabled("disables")
@command_control("disableshelp")
@custom_handler("disableshelp")
async def disables_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(DISABLES_HELP_TEXT)


def load_handlers(application: Application):
    application.add_handler(CommandHandler("disable", disable_command))
    application.add_handler(CommandHandler("enable", enable_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("disableshelp", disables_help_command))
