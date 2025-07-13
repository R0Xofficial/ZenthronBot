import logging
import re
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatType

from ..core.database import add_or_update_filter, remove_filter, get_all_filters_for_chat
from ..core.utils import _can_user_perform_action, safe_escape, create_user_html_link

logger = logging.getLogger(__name__)

def fill_reply_template(text: str | None, user: 'User', chat: 'Chat') -> str:
    if not text:
        return ""
    
    return text.replace('{first}', safe_escape(user.first_name))\
               .replace('{last}', safe_escape(user.last_name or ""))\
               .replace('{fullname}', safe_escape(user.full_name))\
               .replace('{username}', f"@{user.username}" if user.username else user.mention_html())\
               .replace('{id}', str(user.id))\
               .replace('{chatname}', safe_escape(chat.title or "this chat"))

async def send_filter_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_data: dict):
    user = update.effective_user
    chat = update.effective_chat
    
    reply_text = fill_reply_template(filter_data.get('reply_text'), user, chat)
    reply_type = filter_data.get('reply_type', 'text')
    file_id = filter_data.get('file_id')
    
    reply_markup = None

    try:
        target_message = update.effective_message
        
        if reply_type == 'text':
            await target_message.reply_html(reply_text, reply_markup=reply_markup)
        elif reply_type == 'photo':
            await target_message.reply_photo(file_id, caption=reply_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
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
        logger.error(f"Failed to send filter reply for keyword '{filter_data['keyword']}': {e}")
        if reply_text:
            await target_message.reply_html(f"<i>(Error sending media, showing text instead)</i>\n{reply_text}")

async def check_message_for_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_message or not update.effective_message.text:
        return

    if 'filters_cache' not in context.chat_data or context.chat_data.get('filters_last_update', 0) < (context.application.run_time.timestamp() - 60):
        context.chat_data['filters_cache'] = get_all_filters_for_chat(update.effective_chat.id)
        context.chat_data['filters_last_update'] = context.application.run_time.timestamp()

    all_filters = context.chat_data.get('filters_cache', [])
    if not all_filters:
        return
    
    message_text_lower = update.effective_message.text.lower()
    
    for f in all_filters:
        keyword = f['keyword']
        filter_type = f['filter_type']
        
        match = False
        if filter_type == 'keyword' and re.search(r'\b' + re.escape(keyword) + r'\b', message_text_lower, re.IGNORECASE):
            match = True
        
        if match:
            await send_filter_reply(update, context, f)
            return

async def add_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    can_manage = await _can_user_perform_action(update, context, 'can_manage_chat', "You need admin rights to manage filters.")
    if not can_manage: return

    msg = update.effective_message
    
    try:
        keyword = msg.text.split("'", 2)[1]
    except IndexError:
        await msg.reply_html("<b>Usage:</b> /addfilter 'keyword' <reply>\n<i>(You can also reply to a message/media with the keyword)</i>")
        return
        
    filter_data = {'filter_type': 'keyword'}
    
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
        elif replied_msg.voice:
            filter_data['reply_type'], filter_data['file_id'] = 'voice', replied_msg.voice.file_id
        elif replied_msg.document:
            filter_data['reply_type'], filter_data['file_id'] = 'document', replied_msg.document.file_id
        else:
            filter_data['reply_type'] = 'text'
    else:
        try:
            filter_data['reply_text'] = msg.text.split(f"'{keyword}'", 1)[1].strip()
            filter_data['reply_type'] = 'text'
            if not filter_data['reply_text']:
                 raise IndexError
        except IndexError:
            await msg.reply_html("You need to provide a reply text after the keyword, or reply to a message.")
            return

    if add_or_update_filter(msg.chat_id, keyword, filter_data):
        context.chat_data.pop('filters_cache', None)
        await msg.reply_text(f"✅ Filter for '<code>{safe_escape(keyword)}</code>' has been saved.", parse_mode=ParseMode.HTML)
    else:
        await msg.reply_text("An error occurred while saving the filter.")


async def remove_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    can_manage = await _can_user_perform_action(update, context, 'can_manage_chat', "You need admin rights to manage filters.")
    if not can_manage: return

    try:
        keyword_to_remove = update.message.text.split("'", 2)[1]
    except IndexError:
        await update.message.reply_html("<b>Usage:</b> /delfilter 'keyword'")
        return
        
    if remove_filter(update.effective_chat.id, keyword_to_remove):
        context.chat_data.pop('filters_cache', None)
        await update.message.reply_text(f"✅ Filter for '<code>{safe_escape(keyword_to_remove)}</code>' has been removed.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("This filter doesn't exist or an error occurred.")


async def list_filters_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    can_see = await _can_user_perform_action(update, context, 'can_manage_chat', "You need admin rights to see the filter list.")
    if not can_see: return
    
    all_filters = get_all_filters_for_chat(update.effective_chat.id)
    if not all_filters:
        await update.message.reply_text("There are no active filters in this chat.")
        return
        
    message = "<b>Active filters in this chat:</b>\n\n"
    for f in sorted(all_filters, key=lambda x: x['keyword']):
        message += f"• <code>{safe_escape(f['keyword'])}</code>\n"
    await update.message.reply_html(message)


def load_handlers(application: Application):
    application.add_handler(CommandHandler("addfilter", add_filter_command))
    application.add_handler(CommandHandler("delfilter", remove_filter_command))
    application.add_handler(CommandHandler("filters", list_filters_command))
