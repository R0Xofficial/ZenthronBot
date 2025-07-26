import logging
from telegram import Update, User
from telegram.constants import ChatType, ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.utils import _can_user_perform_action, resolve_user_with_telethon, create_user_html_link, send_safe_reply, safe_escape, is_entity_a_user
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- KICK COMMAND FUNCTIONS ---
@check_module_enabled("kicks")
@custom_handler("kick")
async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_kicks = update.effective_user
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't kick in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    args_after_target: list[str] = []

    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        target_user = message.reply_to_message.from_user
        if context.args:
            args_after_target = context.args
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            args_after_target = context.args[1:]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user:
            try:
                target_id = int(target_input)
                if target_id > 0:
                    target_user = User(id=target_id, first_name="", is_bot=False)
                else:
                    target_user = Chat(id=target_id, type="channel")
            except ValueError:
                pass
    else:
        await send_safe_reply(update, context, text="Usage: /kick <ID/@username/reply> [reason]")
        return

    if not target_user:
        await send_safe_reply(update, context, text=f"Skrrrt... I can't find the user.")
        return

    reason: str = " ".join(args_after_target) or "No reason provided."

    if not is_entity_a_user(target_user):
        await send_safe_reply(update, context, text="🧐 Kick can only be applied to users.")
        return

    if target_user.id == context.bot.id:
        await send_safe_reply(update, context, text="Nuh uh... I can't kick myself."); return

    if target_user.id == user_who_kicks.id:
        await send_safe_reply(update, context, text="Nuh uh... You can't kick yourself."); return

    try:
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"]:
            await send_safe_reply(update, context, text="Chat Creator and Administrators cannot be kicked.")
            return
    except TelegramError as e:
        if "user not found" in str(e).lower():
            user_display = create_user_html_link(target_user)
            await send_safe_reply(update, context, text=f"User {user_display} is not in this chat, cannot be kicked.", parse_mode=ParseMode.HTML)
            return
        logger.warning(f"Could not get target's chat member status for /kick: {e}")

    try:
        await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_user.id)
        await context.bot.unban_chat_member(chat_id=chat.id, user_id=target_user.id, only_if_banned=True)

        user_display_name = create_user_html_link(target_user)
        response_lines = ["Success: User Kicked", f"<b>• User:</b> {user_display_name} [<code>{target_user.id}</code>]", f"<b>• Reason:</b> {safe_escape(reason)}"]
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await send_safe_reply(update, context, text=f"Failed to kick user: {safe_escape(str(e))}")

@check_module_enabled("kicks")
@custom_handler("dkick")
async def dkick_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_who_kicks = update.effective_user
    message = update.message
    if not message: return

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't dkick in private chat...")
        return

    can_kick = await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission.")
    can_del = await _can_user_perform_action(update, context, 'can_delete_messages', "Why should I listen to a person with no privileges for this? You need 'can_delete_messages' permission.")
    if not (can_kick and can_del):
        return

    if not message.reply_to_message or message.reply_to_message.forum_topic_created:
        await send_safe_reply(update, context, text="Usage: Reply to a user's message with /dkick [reason] to delete it and kick them.")
        return
        
    target_user = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "No reason provided."

    if not is_entity_a_user(target_user):
        await send_safe_reply(update, context, text="🧐 This command can only be used on users."); return
    
    if target_user.id == context.bot.id:
        await send_safe_reply(update, context, text="Nuh uh... I can't dkick myself."); return

    if target_user.id == user_who_kicks.id:
        await send_safe_reply(update, context, text="Nuh uh... You can't dkick yourself."); return

    try:
        member = await chat.get_member(target_user.id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await send_safe_reply(update, context, text="Chat Creator and Administrators cannot be kicked.")
            return
    except TelegramError: pass
    

    try:
        await message.reply_to_message.delete()
        
        await context.bot.ban_chat_member(chat_id=chat.id, user_id=target_user.id)
        await context.bot.unban_chat_member(chat_id=chat.id, user_id=target_user.id, only_if_banned=True)

        display_name = create_user_html_link(target_user)
        response_lines = ["Success: User Kicked"]
        response_lines.append(f"<b>• User:</b> {display_name} [<code>{target_user.id}</code>]")
        response_lines.append(f"<b>• Reason:</b> {safe_escape(reason)}")
        
        await send_safe_reply(update, context, text="\n".join(response_lines), parse_mode=ParseMode.HTML)

    except Exception as e:
        await send_safe_reply(update, context, text=f"❌ Failed to kick user (but their message was deleted). Error: {safe_escape(str(e))}")

@check_module_enabled("kicks")
@command_control("kickme")
@custom_handler("kickme")
async def kickme_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.effective_message
    user_to_kick = update.effective_user

    if not user_to_kick:
        return

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("Huh? You can't kick yourself in private chat...")
        return

    sender_chat = message.sender_chat
    if sender_chat and sender_chat.type == ChatType.CHANNEL:
        await message.reply_text("🧐 Anonymous admins (channels) cannot use the /kickme command.")
        return

    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if not (bot_member.status == "administrator" and getattr(bot_member, 'can_restrict_members', False)):
            await update.message.reply_text("Error: I can't kick users here because I'm not an admin with ban/kick permissions 🤓.")
            return
    except TelegramError as e:
        logger.error(f"Error checking bot's own permissions in /kickme for chat {chat.id}: {e}")
        await update.message.reply_text("Error: Couldn't verify my own permissions 🤕.")
        return

    try:
        user_chat_member = await context.bot.get_chat_member(chat.id, user_to_kick.id)
        
        if user_chat_member.status == "creator":
            await update.message.reply_text("Hold Up! As the chat Creator, you must use Telegram's native 'Leave group' option.")
            return
        if user_chat_member.status == "administrator":
            await update.message.reply_text("Hold Up! As a chat Administrator, you can't use /kickme. Please use Telegram's 'Leave group' option to prevent accidental self-removal.")
            return
            
    except TelegramError as e:
        if "user not found" in str(e).lower():
            logger.warning(f"User {user_to_kick.id} not found in chat {chat.id} for /kickme, though they sent the command.")
            await update.message.reply_text("🧐 It seems you're not in this chat anymore.")
            return
        else:
            logger.error(f"Error checking your status in this chat for /kickme: {e}")
            await update.message.reply_text("Skrrrt... Couldn't verify your status in this chat to perform /kickme.")
            return

    try:
        user_display_name = create_user_html_link(user_to_kick)
        
        await update.message.reply_text(f"Done! {user_display_name}, as you wish... You have been kicked from the chat.", parse_mode=ParseMode.HTML)
        
        await context.bot.ban_chat_member(chat_id=chat.id, user_id=user_to_kick.id)
        await context.bot.unban_chat_member(chat_id=chat.id, user_id=user_to_kick.id, only_if_banned=True)
        
        logger.info(f"User {user_to_kick.id} self-kicked from chat {chat.id} ('{chat.title}')")
        
    except TelegramError as e:
        logger.error(f"Failed to self-kick user {user_to_kick.id} from chat {chat.id}: {e}")
        await update.message.reply_text(f"Error: I tried to help you leave, but something went wrong: {safe_escape(str(e))}")
    except Exception as e:
        logger.error(f"Unexpected error in /kickme for user {user_to_kick.id}: {e}", exc_info=True)
        await update.message.reply_text("Error: An unexpected error occurred while trying to process your /kickme request.")


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("dkick", dkick_command))
    application.add_handler(CommandHandler("kickme", kickme_command))
