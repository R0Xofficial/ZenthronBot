import asyncio
import logging
from datetime import datetime, timezone, timedelta
from telegram import Update, User, Chat
from telegram.constants import ParseMode, ChatType
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ApplicationHandlerStop

from ..config import OWNER_ID, APPEAL_CHAT_ID
from ..core.database import add_to_blacklist, remove_from_blacklist, get_blacklist_reason, is_user_blacklisted, is_whitelisted, is_sudo_user 
from ..core.utils import is_privileged_user, is_owner_or_dev, resolve_user_with_telethon, create_user_html_link, safe_escape, send_operational_log, is_entity_a_user
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- BLACKLIST COMMAND AND HANDLER FUNCTIONS ---
@check_module_enabled("blacklists")
@custom_handler(["blacklist", "blist"])
async def blacklist_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /blist attempt by user {user.id}.")
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
        await message.reply_html("Usage: /blist &lt;ID/@username/reply&gt; [reason]")
        return

    if not reason:
        await message.reply_text("You must provide a reason for this action.")
        return

    if not is_entity_a_user(target_entity):
        await message.reply_text("🧐 This action can only be applied to users.")
        return
    if is_privileged_user(target_entity.id) or target_entity.id == context.bot.id:
        await message.reply_text("LoL, looks like... Someone tried blacklist privileged user. Nice Try.")
        return
    if is_whitelisted(target_entity.id):
        await message.reply_text("This user is on the whitelist and cannot be blacklisted.")
        return

    user_display = create_user_html_link(target_entity)

    existing_blist_reason = get_blacklist_reason(target_entity.id)
    if existing_blist_reason:
        await message.reply_html(
            f"ℹ️ User {user_display} [<code>{target_entity.id}</code>] is already <b>blacklisted</b>.\n"
            f"<b>Reason:</b> {safe_escape(existing_blist_reason)}"
        )
        return

    prepare_message = f"Ok!"
    await message.reply_html(prepare_message)
    await asyncio.sleep(1.0)

    if add_to_blacklist(target_entity.id, user.id, reason):
        success_message = f"✅ Done! {user_display} [<code>{target_entity.id}</code>] has been <b>blacklisted</b>.\n<b>Reason:</b> {safe_escape(reason)}"
        await message.reply_html(success_message)
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_user_display = create_user_html_link(target_entity)
            admin_link = create_user_html_link(user)

            pm_message = (
                f"<b>#BLACKLISTED</b>\n\n"
                f"<b>User:</b> {log_user_display} [<code>{target_entity.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user.id}</code>]"
            )
            await send_operational_log(context, pm_message)
        except Exception as e:
            logger.error(f"Error preparing/sending #BLACKLISTED operational log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to the blacklist. Check logs.")

@check_module_enabled("blacklists")
@custom_handler(["unblacklist", "unblist"])
async def unblacklist_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /unblist attempt by user {user.id}.")
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
        await message.reply_html("Usage: /unblist &lt;ID/@username/reply&gt;")
        return
    
    if not is_entity_a_user(target_entity):
        await message.reply_text("🧐 This action can only be applied to users."); return
    if target_entity.id == OWNER_ID:
        await message.reply_text("WHAT? The Owner is never on the blacklist."); return

    user_display = create_user_html_link(target_entity)

    if not is_user_blacklisted(target_entity.id):
        await message.reply_html(f"ℹ️ User {user_display} [<code>{target_entity.id}</code>] is not <b>blacklisted</b>.")
        return

    prepare_message = f"Let’s give him next chance!"
    await message.reply_html(prepare_message)
    await asyncio.sleep(1.0)

    if remove_from_blacklist(target_entity.id):
        success_message = f"✅ Done! {user_display} [<code>{target_entity.id}</code>] has been <b>unblacklisted</b>."
        await message.reply_html(success_message)
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_user_display = create_user_html_link(target_entity)
            admin_link = create_user_html_link(user)

            log_message_to_send = (
                f"<b>#UNBLACKLISTED</b>\n\n"
                f"<b>User:</b> {log_user_display} [<code>{target_entity.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user.id}</code>]"
            )
            await send_operational_log(context, log_message_to_send)
        except Exception as e:
            logger.error(f"Error preparing/sending #UNBLACKLISTED operational log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to remove user from the blacklist. Check logs.")

@check_module_enabled("blacklists")
async def check_blacklist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text or not update.effective_user:
        return

    user = update.effective_user
    chat = update.effective_chat

    if user.id == OWNER_ID:
        return
        
    if not is_user_blacklisted(user.id):
        return

    always_allowed_commands = ['/start', '/help', '/info', '/rules', '/warns', '/warnings']
    appeal_chat_allowed_commands = ['/id']

    is_in_appeal_chat = (chat.id == APPEAL_CHAT_ID)

    command = message.text.split()[0].lower()

    if command in always_allowed_commands:
        return
    
    if is_in_appeal_chat and command in appeal_chat_allowed_commands:
        logger.info(f"Allowing command '{command}' for blacklisted user {user.id} in appeal chat.")
        return

    user_mention_log = f"@{user.username}" if user.username else str(user.id)
    message_text_preview = message.text[:50]
    
    logger.info(f"User {user.id} ({user_mention_log}) is blacklisted. Blocking command: '{message_text_preview}'")
    
    raise ApplicationHandlerStop


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler(["blacklist", "blist"],  blacklist_user_command))
    application.add_handler(CommandHandler(["unblacklist", "unblist"], unblacklist_user_command))
