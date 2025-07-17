import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.database import set_rules, get_rules, clear_rules
from ..core.utils import _can_user_perform_action
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- RULES COMMAND FUNCTIONS ---
@check_module_enabled("rules")
@custom_handler("setrules")
async def set_rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await message.reply_text("Huh? You can't set rules in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_members' permission."):
        return

    if message.reply_to_message:
        rules_text = message.reply_to_message.text_html
    else:
        if not context.args:
            await message.reply_text("Usage: /setrules <text of the rules> or reply to a message with the rules.")
            return
        command_entity = message.entities[0]
        rules_text = message.text_html[command_entity.offset + command_entity.length:].strip()

    if not rules_text:
        await message.reply_text("The rules text cannot be empty.")
        return

    if set_rules(chat.id, rules_text):
        await message.reply_html("✅ The rules for this group have been set successfully.")
    else:
        await message.reply_text("A database error occurred while setting the rules.")

@check_module_enabled("rules")
@custom_handler("clearrules")
async def clear_rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await message.reply_text("Huh? You can't clear rules in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_members' permission."):
        return

    if clear_rules(chat.id):
        await message.reply_html("✅ The rules for this group have been cleared.")
    else:
        await message.reply_text("A database error occurred while clearing the rules.")

@check_module_enabled("rules")
@command_control("rules")
@custom_handler("rules")
async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if not message: return

    if chat.type == ChatType.PRIVATE and not context.args:
        await message.reply_text("Huh? You can't check rules in private chat... This command shows group rules. Please use it inside a group.")
        return

    if chat.type != ChatType.PRIVATE:
        rules_text = get_rules(chat.id)
        if rules_text:
            bot_username = context.bot.username
            deep_link_url = f"https://t.me/{bot_username}?start=rules_{chat.id}"
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="📜 Show Rules (PM)", url=deep_link_url)]]
            )
            await message.reply_text("Click the button below to see the group rules in a private message.", reply_markup=keyboard)
        else:
            await message.reply_text("The rules for this group have not been set yet. An admin can set them using /setrules.")


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("setrules", set_rules_command))
    application.add_handler(CommandHandler("clearrules", clear_rules_command))
