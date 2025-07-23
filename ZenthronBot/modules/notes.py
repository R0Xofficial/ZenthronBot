import logging
from telegram import Update
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..core.database import add_note, get_all_notes, remove_note, get_note
from ..core.utils import _can_user_perform_action, send_safe_reply, safe_escape
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- NOTES COMMAND AND HANDLER FUNCTIONS ---
@check_module_enabled("notes")
@custom_handler(["addnote", "savenote", "save"])
async def save_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    message = update.message

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't save note in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return
        
    note_name = ""
    content = ""

    if message.reply_to_message and not message.reply_to_message.forum_topic_created:
        replied_message = message.reply_to_message
        
        if not context.args:
            await message.reply_text("You need to provide a name for the note.\nUsage: /addnote <notename> (replying to a message)")
            return
        
        note_name = context.args[0]
        content = replied_message.text_html if replied_message.text_html else replied_message.text

        if replied_message.caption:
            content = replied_message.caption_html if replied_message.caption_html else replied_message.caption

        if not content:
            await message.reply_text("The replied message doesn't seem to have any text content to save.")
            return

    else:
        if len(context.args) < 2:
            await message.reply_text("Usage:\n1. /addnote <notename> <content>\n2. Reply to a message with /addnote <notename>")
            return
            
        note_name = context.args[0]
        command = message.text.split()[0]
        note_name_raw = context.args[0]
        
        content_offset = len(command) + len(note_name_raw) + 2
        
        content = message.text_html[content_offset:]
        
        if not content:
            await message.reply_text("You need to provide some content for the note.")
            return

    if add_note(chat.id, note_name, content, user.id):
        await message.reply_html(f"✅ Note <code>{note_name.lower()}</code> has been saved.")
    else:
        await message.reply_text("Failed to save the note due to a database error.")

@check_module_enabled("notes")
@command_control("notes")
@custom_handler(["notes", "saved"])
async def list_notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't list notes in private chat...")
        return

    notes = get_all_notes(update.effective_chat.id)
    
    if not notes:
        await update.message.reply_text("There are no notes in this chat.")
        return

    note_list = [f"- <code>{safe_escape(note)}</code>" for note in notes]
    message = "<b>Notes in this chat:</b>\n<i>Use</i> <code>/get notename</code> <i>or</i> <code>#notename</code> <i>to get note.</i>\n\n" + "\n".join(note_list)
    await update.message.reply_html(message)

@check_module_enabled("notes")
@custom_handler(["delnote", "rmnote", "clear"])
async def remove_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't remove notes in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_change_info', "Why should I listen to a person with no privileges for this? You need 'can_change_info' permission.", allow_bot_privileged_override=False):
        return

    if not context.args:
        await update.message.reply_text("Usage: /delnote <notename>")
        return

    note_name = context.args[0]
    if remove_note(chat.id, note_name):
        await update.message.reply_html(f"✅ Note <code>{note_name.lower()}</code> has been removed.")
    else:
        await update.message.reply_html(f"Note <code>{note_name.lower()}</code> not found.")

@check_module_enabled("notes")
@command_control("notes")
@custom_handler("get")
async def get_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't get notes in private chat...")
        return
    
    if not context.args:
        await send_safe_reply(update, context, text="Usage: /get <notename>")
        return
        
    note_name = context.args[0].lower()
    chat_id = update.effective_chat.id

    content = get_note(chat_id, note_name)
    if content:
        await update.message.reply_html(content, disable_web_page_preview=True)
    else:
        await send_safe_reply(update, context, text=f"Note '<code>{safe_escape(note_name)}</code>' not found.", parse_mode=ParseMode.HTML)

@check_module_enabled("notes")
@command_control("notes")
async def handle_note_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    if not text.startswith('#') or text.startswith('#/'):
        return

    note_name = text.split()[0][1:].lower()
    chat_id = update.effective_chat.id

    content = get_note(chat_id, note_name)
    if content:
        await update.message.reply_html(content, disable_web_page_preview=True)


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler(["addnote", "savenote", "save"], save_note_command))
    application.add_handler(CommandHandler(["notes", "saved"], list_notes_command))
    application.add_handler(CommandHandler(["delnote", "rmnote", "clear"], remove_note_command))
    application.add_handler(CommandHandler("get", get_note_command))
