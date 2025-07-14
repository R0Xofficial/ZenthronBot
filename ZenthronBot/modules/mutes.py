import logging
from datetime import datetime, timezone
from telegram import Update, User, ChatPermissions
from telegram.constants import ChatType, ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, ChatMemberHandler

from ..core.utils import _can_user_perform_action, resolve_user_with_telethon, parse_duration_to_timedelta, create_user_html_link, send_safe_reply, safe_escape, send_critical_log
from ..core.decorators import check_module_enabled
from ..core.custom_handlers import CustomPrefixHandler

logger = logging.getLogger(__name__)


# --- MUTE COMMAND FUNCTIONS ---
@check_module_enabled("mutes")
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_mutes = update.effective_user
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't mute in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    args_after_target: list[str] = []

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if context.args:
            args_after_target = context.args
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            args_after_target = context.args[1:]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in MUTE. Proceeding with ID only.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await send_safe_reply(update, context, text="Usage: /mute <ID/@username/reply> [duration] [reason]")
        return

    if not target_user:
        await send_safe_reply(update, context, text=f"Skrrrt... I can't find the user.")
        return

    if not isinstance(target_user, User):
        await send_safe_reply(update, context, text="🧐 Mute can only be applied to users.")
        return
        
    duration_str: str | None = None
    reason: str = "No reason provided."
    if args_after_target:
        potential_duration_td = parse_duration_to_timedelta(args_after_target[0])
        if potential_duration_td:
            duration_str = args_after_target[0]
            if len(args_after_target) > 1:
                reason = " ".join(args_after_target[1:])
        else:
            reason = " ".join(args_after_target)
    if not reason.strip(): reason = "No reason provided."

    if target_user.id == context.bot.id or target_user.id == user_who_mutes.id:
        await send_safe_reply(update, context, text="Nuh uh... This user cannot be muted."); return

    try:
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"]:
            await send_safe_reply(update, context, text="WHAT? Chat Creator and Administrators cannot be muted.")
            return
    except TelegramError as e:
        if "user not found" in str(e).lower():
            user_display = create_user_html_link(target_user)
            await send_safe_reply(update, context, text=f"User {user_display} is not in this chat, cannot be muted.", parse_mode=ParseMode.HTML)
            return
        logger.warning(f"Could not get target's chat member status for /mute: {e}")

    duration_td = parse_duration_to_timedelta(duration_str)
    permissions_to_set_for_mute = ChatPermissions(can_send_messages=False, can_send_audios=False, can_send_documents=False, can_send_photos=False, can_send_videos=False, can_send_video_notes=False, can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False, can_add_web_page_previews=False)
    until_date_dt = datetime.now(timezone.utc) + duration_td if duration_td else None

    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target_user.id, permissions=permissions_to_set_for_mute, until_date=until_date_dt, use_independent_chat_permissions=True)
        user_display_name = create_user_html_link(target_user)

        response_lines = ["Success: User Muted"]
        response_lines.append(f"<b>• User:</b> {user_display_name} (<code>{target_user.id}</code>)")
        response_lines.append(f"<b>• Reason:</b> {safe_escape(reason)}")
        if duration_str and until_date_dt:
            response_lines.append(f"<b>• Duration:</b> <code>{duration_str}</code> (until <code>{until_date_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}</code>)")
        else:
            response_lines.append(f"<b>• Duration:</b> <code>Permanent</code>")
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await send_safe_reply(update, context, text=f"Failed to mute user: {safe_escape(str(e))}")

@check_module_enabled("mutes")
async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't unmute in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in UNMUTE. Proceeding with ID only.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await send_safe_reply(update, context, text="Usage: /unmute <ID/@username/reply>")
        return

    if not target_user:
        await send_safe_reply(update, context, text=f"Skrrrt... I can't find the user.")
        return

    if not isinstance(target_user, User):
        await send_safe_reply(update, context, text="🧐 Unmute can only be applied to users.")
        return

    permissions_to_restore = ChatPermissions(
        can_send_messages=True, can_send_audios=True, can_send_documents=True,
        can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
        can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
        can_add_web_page_previews=True
    )

    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target_user.id, permissions=permissions_to_restore, use_independent_chat_permissions=True)
        user_display_name = create_user_html_link(target_user)
        response_lines = ["Success: User Unmuted", f"<b>• User:</b> {user_display_name} (<code>{target_user.id}</code>)"]
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await send_safe_reply(update, context, text=f"Failed to unmute user: {safe_escape(str(e))}")

@check_module_enabled("mutes")
async def handle_bot_permission_changes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.my_chat_member:
        return

    new_status = update.my_chat_member.new_chat_member
    
    if new_status.user.id != context.bot.id:
        return

    if new_status.status == ChatMemberStatus.RESTRICTED and new_status.can_send_messages is False:
        chat = update.my_chat_member.chat
        logger.warning(f"Bot was muted in chat {chat.title} ({chat.id}). Leaving automatically.")
        try:
            log_text = (
                f"<b>#AUTOLEAVE</b>\n\n"
                f"Bot automatically left the chat <b>{safe_escape(chat.title)}</b> (<code>{chat.id}</code>) "
                f"because it lost the permission to send messages (Muted)."
            )
            await send_critical_log(context, log_text)
            
            await context.bot.leave_chat(chat.id)
        except Exception as e:
            logger.error(f"Error during automatic leave from chat {chat.id}: {e}")


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    prefixes = ['/', '!']
    application.add_handler(CustomPrefixHandler("mute", mute_command, custom_prefixes=prefixes))
    application.add_handler(CustomPrefixHandler("unmute", unmute_command, custom_prefixes=prefixes))
