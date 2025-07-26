import logging
import asyncio
import sqlite3
from datetime import datetime, timezone, timedelta
from telegram import Update, User, Chat
from telegram.constants import ParseMode, ChatType, ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ApplicationHandlerStop

from ..config import APPEAL_CHAT_USERNAME, DB_NAME
from ..core.database import is_gban_enforced, get_gban_reason, add_to_gban, remove_from_gban, is_whitelisted, add_chat_to_db
from ..core.utils import is_privileged_user, resolve_user_with_telethon, create_user_html_link, safe_escape, send_operational_log, propagate_unban, is_entity_a_user
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- GLOBAL BAN COMMAND AND HANDLER FUNCTIONS ---
@check_module_enabled("globalbans")
async def check_gban_on_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    new_members = update.message.new_chat_members if update.message else []
    chat = update.effective_chat

    if not new_members or not chat or not is_gban_enforced(chat.id):
        return
    
    for member in new_members:
        gban_reason = get_gban_reason(member.id)
        if gban_reason and not is_privileged_user(member.id):
            logger.info(f"Gbanned user {member.id} detected in {chat.id}. Enforcing ban.")
            try:
                await context.bot.ban_chat_member(chat_id=chat.id, user_id=member.id)
                
                message_text = (
                    f"⚠️ <b>Alert!</b> This user is globally banned.\n"
                    f"<i>Enforcing ban in this chat.</i>\n\n"
                    f"<b>User ID:</b> <code>{member.id}</code>\n"
                    f"<b>Reason:</b> {safe_escape(gban_reason)}\n"
                    f"<b>Appeal Chat:</b> {APPEAL_CHAT_USERNAME}"
                )
                await context.bot.send_message(chat.id, text=message_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Failed to enforce gban on new member {member.id} in {chat.id}: {e}")

@check_module_enabled("globalbans")
async def check_gban_on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or update.effective_chat.type == ChatType.PRIVATE:
        return
    
    chat = update.effective_chat
    
    if not is_gban_enforced(chat.id):
        return

    user = update.effective_user
    if not user or is_privileged_user(user.id):
        return
        
    gban_reason = get_gban_reason(user.id)
    if gban_reason:
        message = update.effective_message
        
        try:
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            user_member = await context.bot.get_chat_member(chat.id, user.id)

            if user_member.status in ["creator", "administrator"]:
                return

            if bot_member.status == "administrator" and bot_member.can_restrict_members:
                
                await context.bot.ban_chat_member(chat.id, user.id)
                
                if bot_member.can_delete_messages:
                    try:
                        await message.delete()
                    except Exception: pass
                
                message_text = (
                    f"⚠️ <b>Alert!</b> This user is globally banned.\n"
                    f"<i>Enforcing ban in this chat.</i>\n\n"
                    f"<b>User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Reason:</b> {safe_escape(gban_reason)}\n"
                    f"<b>Appeal Chat:</b> {APPEAL_CHAT_USERNAME}"
                )
                await context.bot.send_message(chat.id, text=message_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Failed to take gban action on message for user {user.id} in chat {chat.id}: {e}")

@check_module_enabled("globalbans")
@custom_handler("gban")
async def gban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_who_gbans = update.effective_user
    chat = update.effective_chat
    message = update.message
    if not message: return

    if not is_privileged_user(user_who_gbans.id):
        logger.warning(f"Unauthorized /gban attempt by user {user_who_gbans.id}.")
        return

    target_entity: User | Chat | None = None
    reason: str | None = None

    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        target_entity = message.reply_to_message.sender_chat or message.reply_to_message.from_user
        if context.args:
            reason = " ".join(context.args)
    elif context.args:
        target_input = context.args[0]
        if len(context.args) > 1:
            reason = " ".join(context.args[1:])
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
        await message.reply_html("Usage: /gban &lt;ID/@username/reply&gt; [reason]")
        return

    if not reason:
        await message.reply_text("You must provide a reason for this action.")
        return

    if not is_entity_a_user(target_entity):
        await message.reply_text("🧐 This action can only be applied to users.")
        return
    if is_privileged_user(target_entity.id) or target_entity.id == context.bot.id:
        await message.reply_text("LoL, looks like... Someone tried global ban privileged user. Nice Try.")
        return
    if is_whitelisted(target_entity.id):
        await message.reply_text("This user is on the whitelist and cannot be globally banned.")
        return

    user_display = create_user_html_link(target_entity)
    existing_gban_reason = get_gban_reason(target_entity.id)
    if existing_gban_reason:
        await message.reply_html(
            f"ℹ️ User {user_display} [<code>{target_entity.id}</code>] is already <b>globally banned</b>.\n"
            f"<b>Reason:</b> {safe_escape(existing_gban_reason)}"
        )
        return

    prepare_message = f"Ok!"
    await message.reply_html(prepare_message)
    await asyncio.sleep(1.0)

    if add_to_gban(target_entity.id, user_who_gbans.id, reason):
        if chat.type != ChatType.PRIVATE and is_gban_enforced(chat.id):
            try:
                await context.bot.ban_chat_member(chat.id, target_entity.id)
            except Exception as e:
                logger.warning(f"Could not enforce local ban for gban: {e}")

        success_message = f"✅ Done! {user_display} [<code>{target_entity.id}</code>] has been <b>globally banned</b>.\n<b>Reason:</b> {safe_escape(reason)}"
        await message.reply_html(success_message)
    
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            log_user_display = create_user_html_link(target_entity)
            
            chat_name_display = safe_escape(chat.title or f"PM with {user_who_gbans.first_name}")
            if chat.type != ChatType.PRIVATE and chat.username:
                message_link = f"https://t.me/{chat.username}/{message.message_id}"
                chat_name_display = f"<a href='{message_link}'>{safe_escape(chat.title)}</a>"
            reason_display = safe_escape(reason)
            admin_link = create_user_html_link(user_who_gbans)
            log_message = (
                f"<b>#GBANNED</b>\n"
                f"<b>Initiated From:</b> {chat_name_display} [<code>{chat.id}</code>]\n\n"
                f"<b>User:</b> {log_user_display} [<code>{target_entity.id}</code>]\n"
                f"<b>Reason:</b> <code>{reason_display}</code>\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user_who_gbans.id}</code>]"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error preparing/sending #GBANNED operational log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to global ban list.")

@check_module_enabled("globalbans")
@custom_handler("ungban")
async def ungban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_who_ungbans = update.effective_user
    chat = update.effective_chat
    message = update.message
    if not message: return

    if not is_privileged_user(user_who_ungbans.id):
        logger.warning(f"Unauthorized /ungban attempt by user {user_who_ungbans.id}.")
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
        await message.reply_html("Usage: /ungban &lt;ID/@username/reply&gt;")
        return
        
    if not target_entity:
        await message.reply_text("Skrrrt... I can't find the user."); return

    if not is_entity_a_user(target_entity):
        await message.reply_text("🧐 This action can only be applied to users."); return

    user_display = create_user_html_link(target_entity)

    if not get_gban_reason(target_entity.id):
        await message.reply_html(f"ℹ️ User {user_display} [<code>{target_entity.id}</code>] is not <b>globally banned</b>.")
        return

    if remove_from_gban(target_entity.id):
        prepare_message = f"Let’s give him next chance!"
        await message.reply_html(prepare_message)
    
        if context.job_queue:
            context.job_queue.run_once(propagate_unban, 1, data={'target_user_id': target_entity.id, 'command_chat_id': chat.id, 'user_display': user_display, 'command_message_id': message.message_id})

        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            log_user_display = create_user_html_link(target_entity)
            
            chat_name_display = safe_escape(chat.title or f"PM with {user_who_ungbans.first_name}")
            if chat.type != ChatType.PRIVATE and chat.username:
                message_link = f"https://t.me/{chat.username}/{message.message_id}"
                chat_name_display = f"<a href='{message_link}'>{safe_escape(chat.title)}</a>"
                
            admin_link = create_user_html_link(user_who_ungbans)
    
            log_message = (
                f"<b>#UNGBANNED</b>\n"
                f"<b>Initiated From:</b> {chat_name_display} [<code>{chat.id}</code>]\n\n"
                f"<b>User:</b> {log_user_display} [<code>{target_entity.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user_who_ungbans.id}</code>]"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error preparing/sending #UNGBANNED operational log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to remove from global ban list.")

@check_module_enabled("globalbans")
@custom_handler(["enforcegban", "gbanstat"])
async def enforce_gban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("Huh? You can't set enforcement gban in private chat.")
        return

    try:
        member = await chat.get_member(user.id)
        if member.status != "creator":
            await update.message.reply_text("Only the chat Creator can use this command.")
            return
    except Exception as e:
        logger.error(f"Could not verify creator status for /enforcegban: {e}")
        return

    if not context.args or len(context.args) != 1 or context.args[0].lower() not in ['yes', 'on', 'off', 'no']:
        await update.message.reply_text("Usage: /enforcegban <yes/on/off/no>")
        return
    
    choice = context.args[0].lower()
    current_status_bool = is_gban_enforced(chat.id)

    if choice == 'yes' or choice == 'on':
        permission_notice = ""
        try:
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if not (bot_member.status == "administrator" and bot_member.can_restrict_members):
                permission_notice = (
                    "\n\n<b>⚠️ Notice:</b> I do not have the 'can_restrict_members' permission in this chat. "
                    "The feature is enabled in settings, but I cannot enforce it until I'm granted this right."
                )
        except Exception:
            permission_notice = "\n\n<b>⚠️ Notice:</b> Could not verify my own permissions in this chat."

        if current_status_bool:
            await update.message.reply_html(
                f"ℹ️ Global Ban enforcement is already <b>ENABLED</b> for this chat."
                f"{permission_notice}"
            )
            return
        
        setting = 1
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE bot_chats SET enforce_gban = ? WHERE chat_id = ?", (setting, chat.id))
                if cursor.rowcount == 0:
                    add_chat_to_db(chat.id, chat.title or f"Chat {chat.id}")
                    cursor.execute("UPDATE bot_chats SET enforce_gban = ? WHERE chat_id = ?", (setting, chat.id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update gban enforcement for chat {chat.id}: {e}")
            await update.message.reply_text("An error occurred while updating the setting.")
            return

        await update.message.reply_html(
            f"✅ <b>Global Ban enforcement is now ENABLED for this chat.</b>\n\n"
            f"I will now automatically remove any globally banned user who tries to join or speak here."
            f"{permission_notice}"
        )
        return

    if choice == 'no' or choice == 'off':
        if not current_status_bool:
            await update.message.reply_html("ℹ️ Global Ban enforcement is already <b>DISABLED</b> for this chat.")
            return
        
        setting = 0
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE bot_chats SET enforce_gban = ? WHERE chat_id = ?", (setting, chat.id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update gban enforcement for chat {chat.id}: {e}")
            await update.message.reply_text("An error occurred while updating the setting.")
            return
        
        await update.message.reply_html(
            "❌ <b>Global Ban enforcement is now DISABLED for this chat.</b>\n\n"
            "<b>Notice:</b> This means globally banned users will be able to join and participate here. "
            "This may expose your community to users banned for severe offenses like spam, harassment, or illegal activities."
        )


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("gban", gban_command))
    application.add_handler(CommandHandler("ungban", ungban_command))
    application.add_handler(CommandHandler(["enforcegban", "gbanstat"], enforce_gban_command))
