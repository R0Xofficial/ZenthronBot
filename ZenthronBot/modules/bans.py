import logging
from datetime import datetime, timezone

from telegram import Update, User, Chat
from telegram.constants import ChatType, ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, ChatMemberHandler

from modules.database import remove_chat_from_db

from modules.utils import (
    _can_user_perform_action, resolve_user_with_telethon,
    parse_duration_to_timedelta, create_user_html_link,
    send_safe_reply, safe_escape
)

logger = logging.getLogger(__name__)


# --- BAN COMMAND FUNCTIONS ---
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_bans = update.effective_user
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't ban in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_entity: User | Chat | None = None
    args_after_target: list[str] = []

    if message.reply_to_message:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
        if context.args:
            args_after_target = context.args
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            args_after_target = context.args[1:]
        
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_entity and (target_input.isdigit() or (target_input.startswith('-') and target_input[1:].isdigit())):
            try:
                target_entity = await context.bot.get_chat(int(target_input))
            except:
                if target_input.isdigit():
                    target_entity = User(id=int(target_input), first_name="", is_bot=False)
    
    if not target_entity:
        await send_safe_reply(update, context, text="Usage: /ban <ID/@username/reply> [duration] [reason]")
        return
        
    duration_str: str | None = None
    reason: str = "No reason provided."
    if args_after_target:
        potential_duration_td = parse_duration_to_timedelta(args_after_target[0])
        if potential_duration_td:
            duration_str = args_after_target[0]
            if len(args_after_target) > 1: reason = " ".join(args_after_target[1:])
        else:
            reason = " ".join(args_after_target)
    if not reason.strip(): reason = "No reason provided."

    duration_td = parse_duration_to_timedelta(duration_str)
    until_date_for_api = datetime.now(timezone.utc) + duration_td if duration_td else None

    if target_entity.id == context.bot.id or target_entity.id == user_who_bans.id:
        await send_safe_reply(update, context, text="Nuh uh... This user cannot be banned."); return

    is_user = isinstance(target_entity, User) or (isinstance(target_entity, Chat) and target_entity.type == ChatType.PRIVATE)
    is_channel = isinstance(target_entity, Chat) and target_entity.type == ChatType.CHANNEL

    if not (is_user or is_channel):
        await send_safe_reply(update, context, text="🧐 This action can only be applied to users or by reply message for channel.")
        return

    if is_user:
        try:
            target_member = await context.bot.get_chat_member(chat.id, target_entity.id)
            if target_member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                await send_safe_reply(update, context, text="Chat Creator and Administrators cannot be banned.")
                return
        except TelegramError as e:
            if "user not found" not in str(e).lower():
                logger.warning(f"Could not get member status for /ban: {e}")
    
    try:
        if is_user:
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_entity.id, until_date=until_date_for_api)
        elif is_channel:
            await context.bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=target_entity.id)
        
        display_name = create_user_html_link(target_entity) if is_user else safe_escape(target_entity.title)
        
        response_lines = ["Success: User Banned"]
        response_lines.append(f"<b>• User:</b> {display_name} (<code>{target_entity.id}</code>)")
        response_lines.append(f"<b>• Reason:</b> {safe_escape(reason)}")
        
        if is_user:
            if duration_str and until_date_for_api:
                response_lines.append(f"<b>• Duration:</b> <code>{duration_str}</code> (until <code>{until_date_for_api.strftime('%Y-%m-%d %H:%M:%S %Z')}</code>)")
            else:
                response_lines.append(f"<b>• Duration:</b> <code>Permanent</code>")
        
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await send_safe_reply(update, context, text=f"Error: Failed to ban user: {safe_escape(str(e))}")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't unban in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_entity: User | Chat | None = None
    
    if message.reply_to_message:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    elif context.args:
        target_arg = context.args[0]
        target_entity = await resolve_user_with_telethon(context, target_arg, update)
        
        if not target_entity and (target_arg.isdigit() or (target_arg.startswith('-') and target_arg[1:].isdigit())):
            try:
                target_entity = await context.bot.get_chat(int(target_arg))
            except:
                if target_arg.isdigit():
                    target_entity = User(id=int(target_arg), first_name="", is_bot=False)

    else:
        await send_safe_reply(update, context, text="Usage: /unban <ID/@username/reply>")
        return

    if not target_entity:
        await send_safe_reply(update, context, text=f"Skrrrt... I can't find the user.")
        return
        
    is_user = isinstance(target_entity, User) or (isinstance(target_entity, Chat) and target_entity.type == ChatType.PRIVATE)
    is_channel = isinstance(target_entity, Chat) and target_entity.type == ChatType.CHANNEL

    if not (is_user or is_channel):
        await send_safe_reply(update, context, text="🧐 This action can only be applied to users or by reply message for channel.")
        return

    try:
        if is_user:
            await context.bot.unban_chat_member(chat_id=chat.id, user_id=target_entity.id, only_if_banned=True)
        elif is_channel:
            await context.bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=target_entity.id)
        
        if is_user:
            display_name = create_user_html_link(target_entity)
        else:
            display_name = safe_escape(target_entity.title or f"Channel {target_entity.id}")

        response_lines = ["Success: User Unbanned"]
        response_lines.append(f"<b>• User:</b> {display_name} (<code>{target_entity.id}</code>)")
        
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await send_safe_reply(update, context, text=f"Failed to unban user: {safe_escape(str(e))}")

async def handle_bot_banned(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    update_data = update.my_chat_member
    if not update_data:
        return
        
    if (update_data.new_chat_member.user.id == context.bot.id and
            update_data.new_chat_member.status == ChatMemberStatus.BANNED):
        
        chat = update_data.chat
        logger.warning(f"Bot was banned from chat {chat.title} ({chat.id}). Removing from DB.")
        remove_chat_from_db(chat.id)


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(ChatMemberHandler(handle_bot_banned, ChatMemberHandler.MY_CHAT_MEMBER))
