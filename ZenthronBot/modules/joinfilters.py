import logging
from datetime import datetime, timezone, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatType

from ..core.database import get_chat_join_settings, update_chat_join_settings
from ..core.utils import _can_user_perform_action, safe_escape, create_user_html_link, send_safe_reply
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)

@check_module_enabled("joinfilters")
async def check_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat or not update.message.new_chat_members:
        return

    join_filters, action_to_take = get_chat_join_settings(chat.id)
    if not join_filters:
        return

    for member in update.message.new_chat_members:
        full_name = f"{member.first_name} {member.last_name or ''}".lower()
        username = (member.username or "").lower()
        
        for filter_word in join_filters:
            if filter_word in full_name or filter_word in username:
                user_link = create_user_html_link(member)
                reason = f"Join filter triggered by name/username matching '<code>{safe_escape(filter_word)}</code>'."
                
                logger.info(f"Join filter in chat {chat.id} for user {member.id} ('{full_name}'). Action: {action_to_take}.")
                
                if action_to_take == "ban":
                    await context.bot.ban_chat_member(chat.id, member.id)
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=f"User {user_link} has been <b>banned</b>. {reason}",
                        parse_mode=ParseMode.HTML
                    )
                elif action_to_take == "kick":
                    try:
                        kick_duration = timedelta(minutes=1)
                        unban_date = datetime.now(timezone.utc) + kick_duration
                        await context.bot.ban_chat_member(
                            chat_id=chat.id, 
                            user_id=member.id, 
                            until_date=unban_date
                        )
                        await context.bot.send_message(
                            chat_id=chat.id,
                            text=f"User {user_link} has been <b>kicked</b> and cannot rejoin for 1 minute. {reason}",
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.error(f"Failed to perform timeout kick for user {member.id} in chat {chat.id}: {e}")
                        await context.bot.send_message(
                            chat_id=chat.id,
                            text=f"Failed to kick {user_link}. Please check my permissions.",
                            parse_mode=ParseMode.HTML
                        )
                elif action_to_take == "mute":
                    await context.bot.restrict_chat_member(chat.id, member.id, ChatPermissions(can_send_messages=False))
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=f"User {user_link} has been <b>muted</b>. {reason}",
                        parse_mode=ParseMode.HTML
                    )
                
                break

@check_module_enabled("joinfilters")
@custom_handler("addjoinfilter")
async def add_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't add joinfilter in private chat...")
        return
  
    if not await _can_user_perform_action(update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=False): return
    if not context.args: await update.message.reply_html("Usage: /addjoinfilter &lt;filter&gt;"); return
    
    chat_id = update.effective_chat.id
    filters, _ = get_chat_join_settings(chat_id)
    filter_text = " ".join(context.args).lower()
    
    if filter_text not in filters:
        filters.append(filter_text)
        if update_chat_join_settings(chat_id, filters=filters):
            await update.message.reply_text(f"✅ Filter '<code>{safe_escape(filter_text)}</code>' added.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("An error occurred while saving the filter.")
    else:
        await update.message.reply_text("This filter already exists.")

@check_module_enabled("joinfilters")
@custom_handler("deljoinfilter")
async def remove_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't remove joinfilter in private chat...")
        return
  
    if not await _can_user_perform_action(update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=False): return
    if not context.args: await update.message.reply_html("Usage: /deljoinfilter &lt;filter&gt;"); return

    chat_id = update.effective_chat.id
    filters, _ = get_chat_join_settings(chat_id)
    filter_text = " ".join(context.args).lower()

    if filter_text in filters:
        filters.remove(filter_text)
        if update_chat_join_settings(chat_id, filters=filters):
            await update.message.reply_text(f"✅ Filter '<code>{safe_escape(filter_text)}</code>' removed.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("An error occurred while saving the filter.")
    else:
        await update.message.reply_text("This filter doesn't exist.")

@check_module_enabled("joinfilters")
@custom_handler("joinfilters")
async def list_filters_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't list joinfilters in private chat...")
        return
  
    if not await _can_user_perform_action(update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=True): return
    
    filters, action = get_chat_join_settings(update.effective_chat.id)
    
    message = "<b>Join Filter Settings</b>\n\n"
    message += "This feature automatically takes action on users who join with a name or username containing specific keywords.\n\n"
    message += f"<b>Action on trigger:</b> <code>{action.upper()}</code>\n"
    message += "<i>Use /setjoinaction to change.</i>\n\n"
    
    if not filters:
        message += "There are no active join filters in this chat."
    else:
        message += "<b>Filtered keywords:</b>\n"
        message += " • ".join(f"<code>{safe_escape(f)}</code>" for f in filters)

    await update.message.reply_html(message)

@check_module_enabled("joinfilters")
@custom_handler("setjoinaction")
async def set_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't set joinfilter action in private chat...")
        return
  
    if not await _can_user_perform_action(update, context, 'can_manage_chat', "Why should I listen to a person with no privileges for this? You need 'can_manage_chat' permission.", allow_bot_privileged_override=False): return
    
    actions = ['ban', 'kick', 'mute']
    action_to_set = context.args[0].lower() if context.args else None
    
    if action_to_set not in actions:
        await update.message.reply_html("Usage: /setjoinaction &lt;ban/mute/kick&gt;"); return
        
    if update_chat_join_settings(update.effective_chat.id, action=action_to_set):
        await update.message.reply_text(f"✅ Join filter action has been set to <b>{action_to_set.upper()}</b>.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("An error occurred while setting the action.")


def load_handlers(application: Application):    
    application.add_handler(CommandHandler("addjoinfilter", add_filter_command))
    application.add_handler(CommandHandler("deljoinfilter", remove_filter_command))
    application.add_handler(CommandHandler("joinfilters", list_filters_command))
    application.add_handler(CommandHandler("setjoinaction", set_action_command))
