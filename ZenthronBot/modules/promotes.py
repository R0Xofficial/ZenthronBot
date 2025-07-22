import logging
from telegram import Update, User
from telegram.constants import ChatType, ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from ..core.utils import _can_user_perform_action, resolve_user_with_telethon, create_user_html_link, safe_escape, is_entity_a_user
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- PROMOTION/DEMOTION COMMAND FUNCTIONS ---
@check_module_enabled("promotes")
@custom_handler("promote")
async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    if not message: return

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.reply_text("Huh? You can't promote in private chat....")
        return

    if not await _can_user_perform_action(update, context, 'can_promote_members', "Why should I listen to a person with no privileges for this? You need 'can_promote_members' permission.", allow_bot_privileged_override=True):
        return

    target_user: User | None = None
    args_for_title = list(context.args)

    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        args_for_title = list(context.args[1:])
        
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
        await message.reply_text("Usage: /promote <ID/@username/reply> [optional admin title]")
        return

    if not target_user:
        await message.reply_text(f"Skrrrt... I can't find the user..")
        return

    provided_custom_title = " ".join(args_for_title) if args_for_title else None
    
    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 Promotion can only be applied to users."); return
    if target_user.id == context.bot.id:
        await message.reply_text("Skrrrt... I'm a bot!!! I can't promote myself."); return
    if target_user.is_bot:
        await message.reply_text("Skrrrt... Bots should be promoted manually with specific rights. So... I can't help you 😱"); return

    try:
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        user_display = create_user_html_link(target_user)

        if target_chat_member.status == "creator":
            await message.reply_html(f"Huh? {user_display} is the chat Creator and cannot be managed.")
            return

        if target_chat_member.status == "administrator":
            if provided_custom_title:
                title_to_set = provided_custom_title[:16]
                await context.bot.set_chat_administrator_custom_title(chat.id, target_user.id, title_to_set)
                await message.reply_html(f"✅ User {user_display}'s title has been updated to '<i>{safe_escape(title_to_set)}</i>'.")
            else:
                await message.reply_html(f"ℹ️ User {user_display} is already an admin.")
            return

    except TelegramError as e:
        if "user not found" not in str(e).lower():
            logger.warning(f"Could not get target's chat member status for /promote: {e}")

    title_to_set = provided_custom_title[:16] if provided_custom_title else "Admin"

    try:
        await context.bot.promote_chat_member(
            chat_id=chat.id, user_id=target_user.id,
            can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
            can_restrict_members=True, can_change_info=True, can_invite_users=True,
            can_pin_messages=True, can_manage_topics=(chat.is_forum if hasattr(chat, 'is_forum') else None)
        )
        await context.bot.set_chat_administrator_custom_title(chat.id, target_user.id, title_to_set)
        
        user_display = create_user_html_link(target_user)
        await message.reply_html(f"✅ User {user_display} has been promoted with the title '<i>{safe_escape(title_to_set)}</i>'.")
    except TelegramError as e:
        await message.reply_text(f"Error: Failed to promote user: {safe_escape(str(e))}. Check if the user has not been promoted by another Admin or if I have permissions to perform this action.")

@check_module_enabled("promotes")
@custom_handler("demote")
async def demote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    if not message: return
    
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.reply_text("Huh? You can't demote in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_promote_members', "Why should I listen to a person with no privileges for this? You need 'can_promote_members' permission.", allow_bot_privileged_override=True):
        return
    
    target_user: User | None = None

    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        
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
        await message.reply_text("Usage: /demote <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text(f"Skrrrt... I can't find the user..")
        return
        
    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 Demotion can only be applied to users.")
        return
        
    if target_user.id == context.bot.id:
        await message.reply_text("Wait a minute! I can't demote myself. It's a paradox 😱.")
        return

    try:
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        user_display = create_user_html_link(target_user)

        if target_chat_member.status == "creator":
            await message.reply_html(f"The chat Creator cannot be demoted."); return
        
        if target_chat_member.status != "administrator":
            await message.reply_html(f"ℹ️ User {user_display} is not an administrator."); return

        await context.bot.promote_chat_member(
            chat_id=chat.id, user_id=target_user.id,
            is_anonymous=False, can_manage_chat=False, can_delete_messages=False,
            can_manage_video_chats=False, can_restrict_members=False, can_promote_members=False,
            can_change_info=False, can_invite_users=False, can_pin_messages=False, can_manage_topics=False
        )
        await message.reply_html(f"✅ User {user_display} has been demoted to a regular member.")

    except TelegramError as e:
        if "user not found" in str(e).lower():
            await message.reply_text("Error: User not found in this chat.")
        else:
            logger.error(f"Error during demotion: {e}")
            await message.reply_text(f"Error: Failed to demote user. Reason: {safe_escape(str(e))}. Check if the user has not been promoted by another Admin or if I have permissions to perform this action.")


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("promote", promote_command))
    application.add_handler(CommandHandler("demote", demote_command))
