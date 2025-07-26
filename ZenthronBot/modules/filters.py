import logging
import re
import json
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatType

from ..core.database import add_or_update_filter, remove_filter, get_all_filters_for_chat
from ..core.utils import _can_user_perform_action, safe_escape
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler
from ..core.constants import FILTERS_HELP_TEXT

logger = logging.getLogger(__name__)


def fill_reply_template(text: str | None, user: User, chat: Chat) -> str:
    if not text:
        return ""
    
    return text.replace('{first}', safe_escape(user.first_name))\
               .replace('{last}', safe_escape(user.last_name or ""))\
               .replace('{fullname}', safe_escape(user.full_name))\
               .replace('{username}', f"@{user.username}" if user.username else "")\
               .replace('{mention}', user.mention_html())\
               .replace('{id}', str(user.id))\
               .replace('{chatname}', safe_escape(chat.title or "this chat"))

@check_module_enabled("filters")
@command_control("filters")
async def send_filter_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_data: dict):
    user = update.effective_user
    chat = update.effective_chat
    
    reply_text = fill_reply_template(filter_data.get('reply_text'), user, chat)
    reply_type = filter_data.get('reply_type', 'text')
    file_id = filter_data.get('file_id')
    buttons_json = filter_data.get('buttons')
    reply_markup = None

    if buttons_json:
        try:
            buttons_data = json.loads(buttons_json)
            keyboard = [
                [InlineKeyboardButton(text, url=url) for text, url in row]
                for row in buttons_data
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Could not parse buttons for filter '{filter_data.get('keyword')}': {e}")

    try:
        target_message = update.effective_message
        
        if reply_type == 'text':
            await target_message.reply_html(reply_text, reply_markup=reply_markup, disable_web_page_preview=True)
        elif reply_type == 'photo':
            await target_message.reply_photo(file_id, caption=reply_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        elif reply_type == 'audio':
            await target_message.reply_audio(file_id, caption=reply_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        elif reply_type == 'sticker':
            await target_message.reply_sticker(file_id, reply_markup=reply_markup)
        elif reply_type == 'animation':
            await target_message.reply_animation(file_id, caption=reply_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        elif reply_type == 'video':
            await target_message.reply_video(file_id, caption=reply_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        elif reply_type == 'voice':
            await target_message.reply_voice(file_id, caption=reply_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        elif reply_type == 'document':
            await target_message.reply_document(file_id, caption=reply_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    
    except Exception as e:
        logger.error(f"Failed to send filter reply for keyword '{filter_data.get('keyword')}': {e}")
        if reply_text:
            await update.effective_message.reply_html(f"<i>(Error sending media for this filter, showing text instead)</i>\n\n{reply_text}")

@check_module_enabled("filters")
@command_control("filters")
async def check_message_for_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.effective_message

    if not chat or not message or not message.text or chat.type == ChatType.PRIVATE:
        return
    current_time = time.time()
    if 'filters_cache' not in context.chat_data or context.chat_data.get('filters_last_update', 0) < (current_time - 60):
        context.chat_data['filters_cache'] = get_all_filters_for_chat(chat.id)
        context.chat_data['filters_last_update'] = current_time
    
    all_filters = context.chat_data.get('filters_cache', [])
    if not all_filters:
        return
    
    message_text = message.text
    for f in all_filters:
        keyword = f['keyword']
        filter_type = f['filter_type']
        
        match = False
        try:
            if filter_type == 'keyword':
                normalized_text = re.sub(r'[^\w\s]', '', message_text)
                words_in_message = normalized_text.lower().split()
                
                if keyword.lower() in words_in_message:
                    match = True
            
            elif filter_type == 'wildcard':
                pattern = re.escape(keyword).replace(r'\*', '.*')
                if re.search(pattern, message_text, re.IGNORECASE):
                    match = True
            
            elif filter_type == 'regex':
                if re.search(keyword, message_text, re.IGNORECASE):
                    match = True

        except re.error as e:
            logger.warning(f"Invalid regex pattern in filter for chat {chat.id}: {keyword} | Error: {e}")
            continue

        if match:
            await send_filter_reply(update, context, f)
            return

@check_module_enabled("filters")
@custom_handler(["addfilter", "filter"])
async def add_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't add filter in private chat...")
        return
    
    can_manage = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=False
    )
    if not can_manage:
        return

    msg = update.effective_message
    args = msg.text.split(None, 1)

    if len(args) < 2:
        await msg.reply_html(
            "Usage:\n"
            "• <code>/addfilter 'keyword' Your reply text</code>\n"
            "• <code>/addfilter type:wildcard 'key*' Reply</code>\n"
            "• Reply to a message/media with <code>/addfilter 'keyword'</code>"
        )
        return

    full_args_text = args[1]
    filter_type = 'keyword'

    if full_args_text.lower().startswith('type:'):
        try:
            type_part, keyword_part = full_args_text.split("'", 1)
            type_value = type_part.split(':')[1].strip().lower()
            if type_value in ['wildcard', 'regex']:
                filter_type = type_value
            full_args_text = "'" + keyword_part
        except (ValueError, IndexError):
            await msg.reply_html("Invalid type format. Use <code>type:wildcard</code> or <code>type:regex</code>.")
            return

    try:
        keyword = full_args_text.split("'", 2)[1]
    except IndexError:
        await msg.reply_html("You need to wrap your keyword in single quotes, e.g., 'hello'.")
        return
        
    filter_data = {'filter_type': filter_type}
    
    replied_msg = msg.reply_to_message
    if replied_msg:
        filter_data['reply_text'] = replied_msg.text or replied_msg.caption
        
        if replied_msg.sticker:
            filter_data['reply_type'], filter_data['file_id'] = 'sticker', replied_msg.sticker.file_id
        elif replied_msg.photo:
            filter_data['reply_type'], filter_data['file_id'] = 'photo', replied_msg.photo[-1].file_id
        elif replied_msg.animation:
            filter_data['reply_type'], filter_data['file_id'] = 'animation', replied_msg.animation.file_id
        elif replied_msg.video:
            filter_data['reply_type'], filter_data['file_id'] = 'video', replied_msg.video.file_id
        elif replied_msg.audio:
            filter_data['reply_type'], filter_data['file_id'] = 'audio', replied_msg.audio.file_id
        elif replied_msg.voice:
            filter_data['reply_type'], filter_data['file_id'] = 'voice', replied_msg.voice.file_id
        elif replied_msg.document:
            filter_data['reply_type'], filter_data['file_id'] = 'document', replied_msg.document.file_id
        else:
            filter_data['reply_type'] = 'text'
    else:
        try:
            reply_text = full_args_text.split(f"'{keyword}'", 1)[1].strip()
        except IndexError:
            reply_text = None

        if not reply_text:
            await msg.reply_html("You must provide a reply (like text or an emoji) after the keyword.")
            return
            
        filter_data['reply_type'] = 'text'
        filter_data['reply_text'] = reply_text

    if add_or_update_filter(msg.chat_id, keyword, filter_data):
        context.chat_data.pop('filters_cache', None)
        await msg.reply_text(f"✅ Filter for '<code>{safe_escape(keyword)}</code>' has been saved with type <code>{filter_type}</code>.", parse_mode=ParseMode.HTML)
    else:
        await msg.reply_text("An error occurred while saving the filter.")

@check_module_enabled("filters")
@custom_handler(["delfilter", "stop"])
async def remove_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't remove filter in private chat...")
        return
        
    can_manage = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=False
    )
    if not can_manage:
        return

    try:
        keyword_to_remove = update.message.text.split("'", 2)[1]
    except IndexError:
        await update.message.reply_html("Usage: /delfilter 'keyword'")
        return
        
    if remove_filter(update.effective_chat.id, keyword_to_remove):
        context.chat_data.pop('filters_cache', None)
        await update.message.reply_text(f"✅ Filter for '<code>{safe_escape(keyword_to_remove)}</code>' has been removed.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("This filter doesn't exist or an error occurred while removing it.")

@check_module_enabled("filters")
@custom_handler("filters")
async def list_filters_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't list filters in private chat...")
        return
    
    can_see = await _can_user_perform_action(
        update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=True
    )
    if not can_see:
        return
    
    all_filters = get_all_filters_for_chat(update.effective_chat.id)
    if not all_filters:
        await update.message.reply_text("There are no active filters in this chat.")
        return
        
    message = "<b>Active filters in this chat:</b>\n\n"
    filters_by_type = {'keyword': [], 'wildcard': [], 'regex': []}
    for f in all_filters:
        filters_by_type[f['filter_type']].append(f['keyword'])
        
    for f_type, keywords in filters_by_type.items():
        if keywords:
            message += f"<b>{f_type.capitalize()}:</b>\n"
            for keyword in sorted(keywords):
                message += f"• <code>{safe_escape(keyword)}</code>\n"
            message += "\n"

    await update.message.reply_html(message)

@check_module_enabled("filters")
@command_control("filters")
@custom_handler("filterhelp")
async def filter_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(FILTERS_HELP_TEXT)


def load_handlers(application: Application):  
    application.add_handler(CommandHandler(["addfilter", "filter"], add_filter_command))
    application.add_handler(CommandHandler(["delfilter", "stop"], remove_filter_command))
    application.add_handler(CommandHandler("filters", list_filters_command))
    application.add_handler(CommandHandler("filterhelp", filter_help_command))
