import logging
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from ..core.database import add_warning, remove_warning_by_id, get_warnings, reset_warnings, set_warn_limit, get_warn_limit
from ..core.utils import _can_user_perform_action, resolve_user_with_telethon, create_user_html_link, send_safe_reply, safe_escape, is_entity_a_user
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- WARNINGS COMMAND AND HANDLER FUNCTIONS ---
@check_module_enabled("warns")
@custom_handler("warn")
async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    warner = update.effective_user
    message = update.message

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't warn in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    reason_parts: list[str] = []
    
    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        if not message.reply_to_message.sender_chat:
            target_user = message.reply_to_message.from_user
        reason_parts = context.args
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
        reason_parts = context.args[1:]
    
    if not target_user:
        await message.reply_text("Usage: /warn <ID/@username/reply> [reason]")
        return
    
    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 This command can only be used on users.")
        return

    if target_user.id == context.bot.id:
        await send_safe_reply(update, context, text="Nuh uh... I can't warn myself."); return

    if target_user.id == warner.id:
        await send_safe_reply(update, context, text="Nuh uh... You can't warn yourself."); return
        
    reason = " ".join(reason_parts) or "No reason provided."

    try:
        target_member = await context.bot.get_chat_member(chat.id, target_user.id)
        
        if target_member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            await message.reply_text("Chat Creator and Administrators cannot be warned.")
            return
    except TelegramError as e:
        if "user not found" not in str(e).lower():
            logger.warning(f"Could not get chat member status for warn target {target_user.id}: {e}")

    new_warn_id, warn_count = add_warning(chat.id, target_user.id, reason, warner.id)
    user_display = create_user_html_link(target_user)

    if new_warn_id == -1:
        await message.reply_text("A database error occurred while adding the warning.")
        return

    limit = get_warn_limit(chat.id)


    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Delete Warn [Admin Only]", callback_data=f"undo_warn_{new_warn_id}")]]
    )

    await message.reply_html(
        f"User {user_display} [<code>{target_user.id}</code>] has been warned. ({warn_count}/{limit})\n"
        f"<b>Reason:</b> {safe_escape(reason)}",
        reply_markup=keyboard
    )

    if warn_count >= limit:
        try:
            context.bot_data.setdefault('recently_removed_users', set()).add(target_user.id)
            
            await context.bot.ban_chat_member(chat.id, target_user.id)
            await message.reply_html(
                f"🚨 User {user_display} has reached {warn_count}/{limit} warnings and has been banned."
            )
            reset_warnings(chat.id, target_user.id)
        except Exception as e:
            await message.reply_text(f"Failed to ban user after reaching max warnings: {e}")

@check_module_enabled("warns")
@custom_handler("dwarn")
async def dwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    warner = update.effective_user
    message = update.message

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't dwarn in private chat...")
        return
    
    can_warn = await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission.")
    can_del = await _can_user_perform_action(update, context, 'can_delete_messages', "Why should I listen to a person with no privileges for this? You need 'can_delete_messages' permission.")
    if not (can_warn and can_del):
        return

    if not message.reply_to_message or message.reply_to_message.forum_topic_created:
        await message.reply_text("Usage: Reply to a user's message with /dwarn [reason] to delete it and warn them.")
        return
        
    target_user = message.reply_to_message.sender_chat or message.reply_to_message.from_user
    reason = " ".join(context.args) or "No reason provided."

    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 This command can only be used on users."); return

    if target_user.id == context.bot.id:
        await send_safe_reply(update, context, text="Nuh uh... I can't warn myself."); return

    if target_user.id == warner.id:
        await send_safe_reply(update, context, text="Nuh uh... You can't warn yourself."); return
        
    try:
        target_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            await message.reply_text("Chat Creator and Administrators cannot be warned.")
            return
    except TelegramError as e:
        if "user not found" not in str(e).lower():
            logger.warning(f"Could not get chat member status for dwarn target {target_user.id}: {e}")

    try:
        await message.reply_to_message.delete()
    except TelegramError as e:
        logger.warning(f"Could not delete message in dwarn: {e}")

    new_warn_id, warn_count = add_warning(chat.id, target_user.id, reason, warner.id)
    user_display = create_user_html_link(target_user)

    if new_warn_id == -1:
        await message.reply_text("A database error occurred while adding the warning.")
        return

    limit = get_warn_limit(chat.id)

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Delete Warn [Admin Only]", callback_data=f"undo_warn_{new_warn_id}")]]
    )

    await message.reply_html(
        f"User {user_display} [<code>{target_user.id}</code>] has been warned & their message deleted. ({warn_count}/{limit})\n"
        f"<b>Reason:</b> {safe_escape(reason)}",
        reply_markup=keyboard
    )

    if warn_count >= limit:
        try:
            context.bot_data.setdefault('recently_removed_users', set()).add(target_user.id)
            await context.bot.ban_chat_member(chat.id, target_user.id)
            await message.reply_html(
                f"🚨 User {user_display} has reached {warn_count}/{limit} warnings and has been banned."
            )
            reset_warnings(chat.id, target_user.id)
        except Exception as e:
            await message.reply_text(f"Failed to ban user after reaching max warnings: {e}")

@check_module_enabled("warns")
async def undo_warn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_who_clicked = query.from_user
    
    try:
        member = await context.bot.get_chat_member(query.message.chat_id, user_who_clicked.id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await query.answer("You must be an admin to undo this action.", show_alert=True)
            return
    except Exception:
        await query.answer("Could not verify your permissions.", show_alert=True)
        return

    try:
        warn_id_to_remove = int(query.data.split("_")[2])
    except (IndexError, ValueError):
        await query.edit_message_text("Error: Invalid callback data.")
        return

    if remove_warning_by_id(warn_id_to_remove):
        new_text = query.message.text_html + "\n\n<i>(Warn deleted by " + user_who_clicked.mention_html() + ")</i>"
        await query.edit_message_text(new_text, parse_mode=ParseMode.HTML, reply_markup=None)
    else:
        await query.edit_message_text(query.message.text_html + "\n\n<i>(This warn was already deleted or could not be found.)</i>", parse_mode=ParseMode.HTML, reply_markup=None)

@check_module_enabled("warns")
@command_control("warns")
@custom_handler(["warnings", "warns"])
async def warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't check warnings in private chat...")
        return
    
    target_user: User | None = None
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        resolved_entity = await resolve_user_with_telethon(context, target_input, update)
        
        if isinstance(resolved_entity, User):
            target_user = resolved_entity
        else:
            try:
                user_id = int(target_input)
                target_user = User(id=user_id, first_name=f"User {user_id}", is_bot=False)
            except ValueError:
                pass
    else:
        target_user = update.effective_user

    if not target_user:
        await update.message.reply_text("Could not find that user. Please provide a valid User ID, @username, or reply to a message.")
        return
        
    user_warnings = get_warnings(update.effective_chat.id, target_user.id)
    user_display = create_user_html_link(target_user)
    limit = get_warn_limit(update.effective_chat.id)

    if not user_warnings:
        await update.message.reply_html(f"User {user_display} has no warnings in this chat.")
        return

    message_lines = [f"<b>Warnings for {user_display}: [{len(user_warnings)}/{limit}]</b>"]
    for i, (reason, admin_id) in enumerate(user_warnings, 1):
        message_lines.append(f"\n{i}. <b>Reason:</b> {safe_escape(reason)}")
    
    await update.message.reply_html("\n".join(message_lines))

@check_module_enabled("warns")
@custom_handler("resetwarns")
async def reset_warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't reset warnings in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission."):
        return

    target_user: User | None = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        target_user = await resolve_user_with_telethon(context, target_input, update)
    
    if not target_user:
        await update.message.reply_text("Usage: /resetwarns <ID/@username/reply>")
        return
        
    if reset_warnings(update.effective_chat.id, target_user.id):
        user_display = create_user_html_link(target_user)
        await update.message.reply_html(f"✅ Warnings for {user_display} have been reset.")
    else:
        await update.message.reply_text("Failed to reset warnings (or user had no warnings).")

@check_module_enabled("warns")
@custom_handler("setwarnlimit")
async def set_warn_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't set warning limit in private chat...")
        return
    
    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission.", allow_bot_privileged_override=False):
        return

    if not context.args:
        limit = get_warn_limit(chat.id)
        await update.message.reply_html(f"The current warning limit in this chat is <b>{limit}</b>.")
        return

    try:
        limit = int(context.args[0])
        if limit < 1:
            await update.message.reply_text("The warning limit must be at least 1.")
            return
            
        if set_warn_limit(chat.id, limit):
            await update.message.reply_html(f"✅ The warning limit for this chat has been set to <b>{limit}</b>.")
        else:
            await update.message.reply_text("Failed to set the warning limit.")
            
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CallbackQueryHandler(undo_warn_callback, pattern=r"^undo_warn_"))
    application.add_handler(CommandHandler(["warnings", "warns"], warnings_command))
    application.add_handler(CommandHandler("resetwarns", reset_warnings_command))
    application.add_handler(CommandHandler("setwarnlimit", set_warn_limit_command))
