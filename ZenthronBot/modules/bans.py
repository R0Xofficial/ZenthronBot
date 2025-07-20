import logging
from datetime import datetime, timezone
from telegram import Update, User, Chat
from telegram.constants import ChatType, ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, ChatMemberHandler

from ..core.database import remove_chat_from_db
from ..core.utils import _can_user_perform_action, resolve_user_with_telethon, parse_duration_to_timedelta, create_user_html_link, send_safe_reply, safe_escape, is_entity_a_user
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- BAN COMMAND FUNCTIONS ---
@check_module_enabled("bans")
@custom_handler("ban")
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
        
        is_numeric_id = False
        try:
            int(target_input)
            is_numeric_id = True
        except ValueError:
            pass

        if not target_entity and is_numeric_id:
            target_entity = User(id=int(target_input), first_name="Unknown", is_bot=False)
    
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

    if is_entity_a_user(target_entity):
        try:
            member = await context.bot.get_chat_member(chat.id, target_entity.id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                await send_safe_reply(update, context, text="Admins and chat creators cannot be banned.")
                return
        except TelegramError:
            pass
    
    try:
        await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_entity.id, until_date=until_date_for_api)
        display_name = create_user_html_link(target_entity)
    except TelegramError:
        try:
            await context.bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=target_entity.id)
            display_name = safe_escape(target_entity.title or f"Entity {target_entity.id}")
        except Exception as e:
            await send_safe_reply(update, context, text=f"❌ Failed to ban this entity. Error: {safe_escape(str(e))}")
            return
            
    response_lines = ["✅ <b>User Banned</b>"]
    response_lines.append(f"<b>• User:</b> {display_name} [<code>{target_entity.id}</code>]")
    response_lines.append(f"<b>• Reason:</b> {safe_escape(reason)}")
    
    if is_entity_a_user(target_entity):
        duration_str = context.args[1] if len(context.args) > 1 and message.reply_to_message else (context.args[0] if context.args and not message.reply_to_message else None)
        if duration_td:
            response_lines.append(f"<b>• Duration:</b> <code>{duration_str}</code>")
        else:
            response_lines.append(f"<b>• Duration:</b> <code>Permanent</code>")
    
    await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)

@check_module_enabled("bans")
@custom_handler("unban")
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
        
        is_numeric_id = False
        try:
            int(target_arg)
            is_numeric_id = True
        except ValueError:
            pass

        if not target_entity and is_numeric_id:
            target_entity = User(id=int(target_arg), first_name="Unknown", is_bot=False)

    else:
        await send_safe_reply(update, context, text="Usage: /unban <ID/@username/reply>")
        return

    if not target_entity:
        await send_safe_reply(update, context, text=f"Skrrrt... I can't find the user.")
        return
        
    try:
        await context.bot.unban_chat_member(chat_id=chat.id, user_id=target_entity.id, only_if_banned=True)
        display_name = create_user_html_link(target_entity) if is_entity_a_user(target_entity) else safe_escape(getattr(target_entity, 'title', f"Entity {target_entity.id}"))
    
    except TelegramError as e:
        if "user not found" in str(e).lower() or "user_id_invalid" in str(e).lower():
            try:
                await context.bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=target_entity.id)
                display_name = safe_escape(target_entity.title or f"Entity {target_entity.id}")
            except Exception as final_e:
                await send_safe_reply(update, context, text=f"❌ Failed to unban this entity. Error: {safe_escape(str(final_e))}")
                return
        else:
            await send_safe_reply(update, context, text=f"❌ Failed to unban: {safe_escape(str(e))}")
            return

    response_lines = ["✅ <b>User Unbanned</b>"]
    response_lines.append(f"<b>• User:</b> {display_name} [<code>{target_entity.id}</code>]")
    
    await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)

@check_module_enabled("bans")
async def handle_bot_banned(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    update_data = update.my_chat_member
    if not update_data:
        return
        
    if (update_data.new_chat_member.user.id == context.bot.id and
            update_data.new_chat_member.status == ChatMemberStatus.BANNED):
        
        chat = update_data.chat
        logger.warning(f"Bot was banned from chat {chat.title} [{chat.id}]. Removing from DB.")
        remove_chat_from_db(chat.id)


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
