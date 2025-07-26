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

    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
        if context.args:
            args_after_target = context.args
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            args_after_target = context.args[1:]
        
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_entity:
            try:
                target_id = int(target_input)
                if target_id > 0:
                    target_entity = User(id=target_id, first_name="", is_bot=False)
                else:
                    target_entity = Chat(id=target_id, type="channel")
            except ValueError:
                pass
    
    if not target_entity:
        await send_safe_reply(update, context, text="Usage: /ban <ID/@username/reply> [reason]")
        return        

    duration_str: str | None = None
    reason: str = "No reason provided."
    if args_after_target:
        potential_duration_td = parse_duration_to_timedelta(args_after_target[0])
        if potential_duration_td:
            duration_str = args_after_target[0]
            reason = " ".join(args_after_target[1:]) if len(args_after_target) > 1 else reason
        else:
            reason = " ".join(args_after_target)
    if not reason.strip(): reason = "No reason provided."

    duration_td = parse_duration_to_timedelta(duration_str)
    until_date_for_api = datetime.now(timezone.utc) + duration_td if duration_td else None


    if target_entity.id == context.bot.id:
        await send_safe_reply(update, context, text="Nuh uh... I can't ban myself."); return

    if target_entity.id == user_who_bans.id:
        await send_safe_reply(update, context, text="Nuh uh... You can't ban yourself."); return

    if is_entity_a_user(target_entity):
        try:
            member = await context.bot.get_chat_member(chat.id, target_entity.id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                await send_safe_reply(update, context, text="Chat Creator and Administrators cannot be banned.")
                return
        except TelegramError: pass


    display_name = ""
    banned = False
    entity_type_str = "Entity"


    try:
        await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_entity.id, until_date=until_date_for_api)
        display_name = create_user_html_link(target_entity)
        entity_type_str = "User"
        banned = True
    except (TelegramError, ValueError):

        try:
            await context.bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=target_entity.id)
            display_name = safe_escape(getattr(target_entity, 'title', f"{target_entity.id}"))
            entity_type_str = "Channel"
            banned = True
        except Exception as e:
            await send_safe_reply(update, context, text=f"❌ Failed to ban this entity. Error: {safe_escape(str(e))}")
            return
            
    if banned:
        response_lines = [f"Success: {entity_type_str} Banned"]
        response_lines.append(f"<b>• {entity_type_str}:</b> {display_name} [<code>{target_entity.id}</code>]")
        response_lines.append(f"<b>• Reason:</b> {safe_escape(reason)}")
        if is_entity_a_user(target_entity) and duration_str:
            response_lines.append(f"<b>• Duration:</b> <code>{duration_str}</code>")
        
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)

@check_module_enabled("bans")
@custom_handler("dban")
async def dban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_bans = update.effective_user
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't dban in private chat...")
        return

    can_ban = await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission.")
    can_del = await _can_user_perform_action(update, context, 'can_delete_messages', "Why should I listen to a person with no privileges for this? You need 'can_delete_messages' permission.")
    if not (can_ban and can_del):
        return

    if not message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        await send_safe_reply(update, context, text="Usage: Reply to a message with /dban [reason] to delete it and ban the sender.")
        return
        
    target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "No reason provided."

    if target_entity.id == context.bot.id:
        await send_safe_reply(update, context, text="Nuh uh... I can't dban myself."); return

    if target_entity.id == user_who_bans.id:
        await send_safe_reply(update, context, text="Nuh uh... You can't dban yourself."); return

    if is_entity_a_user(target_entity):
        try:
            member = await chat.get_member(target_entity.id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                await send_safe_reply(update, context, text="Chat Creator and Administrators cannot be banned.")
                return
        except TelegramError: pass

    try:
        await message.reply_to_message.delete()
        
        display_name = ""
        entity_type_str = "Entity"

        try:
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_entity.id)
            display_name = create_user_html_link(target_entity)
            entity_type_str = "User"
        except (TelegramError, ValueError):
            await context.bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=target_entity.id)
            display_name = safe_escape(getattr(target_entity, 'title', f"{target_entity.id}"))
            entity_type_str = "Channel"

        response_lines = [f"Success: {entity_type_str} Banned"]
        response_lines.append(f"<b>• {entity_type_str}:</b> {display_name} [<code>{target_entity.id}</code>]")
        response_lines.append(f"<b>• Reason:</b> {safe_escape(reason)}")
        
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)

    except Exception as e:
        await send_safe_reply(update, context, text=f"❌ Failed to ban entity (but their message was deleted). Error: {safe_escape(str(e))}")

@check_module_enabled("bans")
@custom_handler("tban")
async def tban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_bans = update.effective_user
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't use this command in a private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_entity: User | Chat | None = None
    args_after_target: list[str] = []

    if message.reply_to_message and not message.reply_to_message.forum_topic_created:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
        args_after_target = context.args
    elif context.args:
        target_input = context.args[0]
        args_after_target = context.args[1:]
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        if not target_entity:
            try:
                target_id = int(target_input)
                if target_id > 0:
                    target_entity = User(id=target_id, first_name="", is_bot=False)
                else:
                    target_entity = Chat(id=target_id, type="channel")
            except ValueError:
                pass
    
    if not target_entity:
        await send_safe_reply(update, context, text="Usage: /tban <ID/@username/reply> [duration] [reason]")
        return
        
    if not is_entity_a_user(target_entity):
        await send_safe_reply(update, context, text="🧐 Temporary bans can only be applied to users.")
        return

    if not args_after_target:
        await send_safe_reply(update, context, text="You must specify a duration for the temporary ban (e.g., 10m, 2h, 3d).")
        return
        
    duration_str = args_after_target[0]
    duration_td = parse_duration_to_timedelta(duration_str)

    if not duration_td:
        await send_safe_reply(update, context, text=f"'{safe_escape(duration_str)}' is not a valid duration. Use formats like 10m, 2h, 3d.")
        return

    reason = " ".join(args_after_target[1:]) if len(args_after_target) > 1 else "No reason provided."
    if not reason.strip(): reason = "No reason provided."

    until_date_for_api = datetime.now(timezone.utc) + duration_td

    if target_entity.id == context.bot.id:
        await send_safe_reply(update, context, text="Nuh uh... I can't tban myself."); return

    if target_entity.id == user_who_bans.id:
        await send_safe_reply(update, context, text="Nuh uh... You can't tban yourself."); return

    try:
        member = await context.bot.get_chat_member(chat.id, target_entity.id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await send_safe_reply(update, context, text="Chat admins and creators cannot be banned.")
            return
    except TelegramError: pass

    try:
        await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_entity.id, until_date=until_date_for_api)
        
        display_name = create_user_html_link(target_entity)
        response_lines = ["Success: User Banned"]
        response_lines.append(f"<b>• User:</b> {display_name} [<code>{target_entity.id}</code>]")
        response_lines.append(f"<b>• Reason:</b> {safe_escape(reason)}")
        response_lines.append(f"<b>• Duration:</b> <code>{duration_str}</code>")
        
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
    except Exception as e:
        await send_safe_reply(update, context, text=f"❌ Failed to temporarily ban user: {safe_escape(str(e))}")

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
    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_entity:
            try:
                target_id = int(target_input)
                if target_id > 0:
                    target_entity = User(id=target_id, first_name="", is_bot=False)
                else:
                    target_entity = Chat(id=target_id, type="channel")
            except ValueError:
                pass
    
    if not target_entity:
        await send_safe_reply(update, context, text="Usage: /unban <ID/@username/reply>")
        return

    unbanned = False
    display_name = ""
    entity_type_str = "Entity"

    try:
        await context.bot.unban_chat_member(chat_id=chat.id, user_id=target_entity.id, only_if_banned=True)
        display_name = create_user_html_link(target_entity)
        entity_type_str = "User"
        unbanned = True
    except (TelegramError, ValueError):
        try:
            await context.bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=target_entity.id)
            display_name = safe_escape(getattr(target_entity, 'title', f"{target_entity.id}"))
            entity_type_str = "Channel"
            unbanned = True
        except Exception as e:
            await send_safe_reply(update, context, text=f"❌ Failed to unban this entity. Error: {safe_escape(str(e))}")
            return
            
    if unbanned:
        response_lines = [f"Success: {entity_type_str} Unbanned"]
        response_lines.append(f"<b>• {entity_type_str}:</b> {display_name} [<code>{target_entity.id}</code>]")
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
    application.add_handler(CommandHandler("dban", dban_command))
    application.add_handler(CommandHandler("tban", tban_command))
    application.add_handler(CommandHandler("unban", unban_command))
