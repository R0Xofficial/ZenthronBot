import logging
from telegram import Update, User, Chat
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode, ChatType

from ..core.utils import resolve_user_with_telethon, is_entity_a_user, is_owner_or_dev

logger = logging.getLogger(__name__)

async def test_resolve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_dev(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /testresolve <ID or @username>")
        return

    target_input = context.args[0]
    message = update.effective_message

    await message.reply_text(f"Running resolver for: '{target_input}'...")

    target_entity = await resolve_user_with_telethon(context, target_input, update)

    if not target_entity:
        await message.reply_text("Resolver nie zwrócił żadnego obiektu (zwrócił None).")
        return

    debug_message = "<b>--- WYNIK DIAGNOSTYCZNY RESOLVERA ---</b>\n\n"
    debug_message += f"<b>Input:</b> <code>{target_input}</code>\n"
    debug_message += f"<b>Typ obiektu:</b> <code>{type(target_entity).__name__}</code>\n\n"
    
    debug_message += f"<b>Sprawdzenie `isinstance`:</b>\n"
    debug_message += f" • isinstance(target, User): <code>{isinstance(target_entity, User)}</code>\n"
    debug_message += f" • isinstance(target, Chat): <code>{isinstance(target_entity, Chat)}</code>\n\n"
    
    debug_message += "<b>Dostępne atrybuty:</b>\n"
    debug_message += f" • Posiada .id: <code>{hasattr(target_entity, 'id')}</code> (Wartość: <code>{getattr(target_entity, 'id', 'N/A')}</code>)\n"
    debug_message += f" • Posiada .type: <code>{hasattr(target_entity, 'type')}</code> (Wartość: <code>{getattr(target_entity, 'type', 'N/A')}</code>)\n"
    debug_message += f" • Posiada .is_bot: <code>{hasattr(target_entity, 'is_bot')}</code> (Wartość: <code>{getattr(target_entity, 'is_bot', 'N/A')}</code>)\n\n"
    
    verification_result = is_entity_a_user(target_entity)
    debug_message += f"<b>Wynik funkcji `is_entity_a_user`:</b> <code>{verification_result}</code>\n"
    
    await message.reply_html(debug_message)


def load_handlers(application: Application):
    application.add_handler(CommandHandler("testresolve", test_resolve_command))
