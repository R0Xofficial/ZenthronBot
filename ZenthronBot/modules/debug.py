# ZenthronBot/modules/debug.py
import logging
from telegram import Update, User, Chat
from telegram.constants import ChatType, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from ..core.utils import resolve_user_with_telethon, is_entity_a_user, is_owner_or_dev

logger = logging.getLogger(__name__)

async def test_resolve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id): return
    if not context.args: await update.message.reply_text("Usage: /testresolve <ID>"); return
    
    target_input = context.args[0]
    message = update.effective_message
    await message.reply_text(f"Running resolver for: '{target_input}'...")

    target_entity = await resolve_user_with_telethon(context, target_input, update)

    if not target_entity:
        await message.reply_text("Resolver zwrócił: None.")
        return

    debug_message = "<b>--- WYNIK DIAGNOSTYCZNY ---</b>\n\n"
    debug_message += f"<b>Input:</b> <code>{target_input}</code>\n"
    debug_message += f"<b>Typ obiektu (wg Pythona):</b> <code>{type(target_entity).__name__}</code>\n\n"
    
    debug_message += f"<b>isinstance(target, User):</b> <code>{isinstance(target_entity, User)}</code>\n"
    debug_message += f"<b>isinstance(target, Chat):</b> <code>{isinstance(target_entity, Chat)}</code>\n\n"
    
    debug_message += "<b>Kluczowe atrybuty:</b>\n"
    debug_message += f" • Wartość .id: <code>{getattr(target_entity, 'id', 'Brak')}</code>\n"
    debug_message += f" • Wartość .type: <code>{getattr(target_entity, 'type', 'Brak')}</code>\n"
    debug_message += f" • Wartość .first_name: <code>{getattr(target_entity, 'first_name', 'Brak')}</code>\n\n"
    
    verification_result = is_entity_a_user(target_entity)
    debug_message += f"<b>Wynik `is_entity_a_user`:</b> <code>{verification_result}</code>\n"
    
    await message.reply_html(debug_message)

def load_handlers(application: Application):
    application.add_handler(CommandHandler("testresolve", test_resolve_command))
