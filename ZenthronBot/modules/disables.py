import logging
from telegram import Update
from telegram.constants import ParseMode, ChatType
from telegram.ext import Application, CommandHandler, ContextTypes
from collections import defaultdict

from ..core.database import disable_command_in_chat, enable_command_in_chat, get_disabled_commands_in_chat
from ..core.utils import safe_escape, _can_user_perform_action, send_safe_reply
from ..core.decorators import check_module_enabled

logger = logging.getLogger(__name__)

@check_module_enabled("disables")
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

    manageable_commands = context.bot_data.get("manageable_commands", set())
    command_to_disable = context.args[0].lower().lstrip('') if context.args else ""
    
    if not command_to_disable or command_to_disable not in manageable_commands:
        await update.message.reply_html(
            f"<b>Usage:</b> /disable &lt;command name&gt;\n"
            f"This command doesn't exist or cannot be managed."
        )
        return

    if disable_command_in_chat(update.effective_chat.id, command_to_disable):
        await update.message.reply_text(
            f"✅ Command <code>{safe_escape(command_to_disable)}</code> is now disabled for non-admins in this chat.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("This command was already disabled or an error occurred.")

@check_module_enabled("disables")
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
    
    manageable_commands = context.bot_data.get("manageable_commands", set())
    command_to_enable = context.args[0].lower().lstrip('') if context.args else ""
    
    if not command_to_enable or command_to_enable not in manageable_commands:
        await update.message.reply_html("<b>Usage:</b> /enable &lt;command name&gt;\nThat command doesn't exist or isn't managed.")
        return
        
    if enable_command_in_chat(update.effective_chat.id, command_to_enable):
        await update.message.reply_text(
            f"✅ Command <code>{safe_escape(command_to_enable)}</code> is now enabled for everyone in this chat.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("This command was already enabled or an error occurred.")

@check_module_enabled("disables")
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
            status = "🔴 Disabled (for non-admins)" if cmd in disabled_commands else "🟢 Enabled"
            message += f"• <code>{cmd}</code>: {status}\n"
        
    await update.message.reply_html(message)

async def disables_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    can_see_help = await _can_user_perform_action(
        update, context, 'can_manage_chat', "You must be an admin to see this help."
    )
    if not can_see_help:
        return

    command_registry = context.bot_data.get("manageable_commands", {})
    
    if not command_registry:
        await update.message.reply_html("No manageable commands found to describe.")
        return

    commands_by_module = defaultdict(list)
    for cmd_name, meta in command_registry.items():
        module_name = meta.get("module", "unknown")
        description = meta.get("description", "No description.")
        commands_by_module[module_name].append(f"<code>/{cmd_name}</code> - {safe_escape(description)}")

    help_message = "<b>Help for manageable commands</b>\n\n"
    help_message += "You can disable commands for non-admins in this chat using /disable <command_name>.\nHere's what each command does:\n\n"

    for module_name in sorted(commands_by_module.keys()):
        help_message += f"<b>🔹 Module: {safe_escape(module_name)}</b>\n"
        
        for command_line in sorted(commands_by_module[module_name]):
            help_message += f"  {command_line}\n"
        
        help_message += "\n"

    await update.message.reply_html(help_message)


def load_handlers(application: Application):
    application.add_handler(CommandHandler("disable", disable_command))
    application.add_handler(CommandHandler("enable", enable_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("disableshelp", disables_help_command))
