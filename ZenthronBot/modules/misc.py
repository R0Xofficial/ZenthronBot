import logging
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Chat, User
from telegram.constants import ChatType, ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

import config
from modules.database import (
    get_rules, is_privileged_user, is_dev_user, is_sudo_user, is_support_user,
    is_whitelisted, get_blacklist_reason, get_gban_reason, is_gban_enforced,
    update_user_in_db, get_user_from_db_by_username
)
from modules.utils import (
    safe_escape, resolve_user_with_telethon, create_user_html_link, send_safe_reply
)
from constants import (
    HELP_TEXT, ADMIN_NOTE_TEXT, SUPPORT_COMMANDS_TEXT, SUDO_COMMANDS_TEXT,
    DEVELOPER_COMMANDS_TEXT, OWNER_COMMANDS_TEXT
)

logger = logging.getLogger(__name__)


# --- MISCELLANEOUS COMMAND FUNCTIONS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    welcome_message = f"Welcome, {user.mention_html()}! I am a Zenthron. Your Telegram group assistant.\nUse /help to see available commands.\n\n<i>I'm Still a Work In Progress [WIP]. Various bugs and security holes may appear for which Bot creators are not responsible [You add me to group at your own risk]. For any questions or issues, please contact our support team at {APPEAL_CHAT_USERNAME}.</i>"
    
    if context.args:
        if context.args[0] == 'help':
            await update.message.reply_html(HELP_TEXT, disable_web_page_preview=True)
            return

        elif context.args[0].startswith('rules_'):
            try:
                chat_id = int(context.args[0].split('_')[1])
                rules_text = get_rules(chat_id)
                if rules_text:
                    await update.message.reply_html(rules_text, disable_web_page_preview=True)
                else:
                    await update.message.reply_text("The rules for that group are not set or I couldn't find them.")
            except (IndexError, ValueError):
                await update.message.reply_text("Invalid link for rules.")
            return
        
        if context.args[0] == 'sudocmds':
            if not is_privileged_user(user.id):
                return

            help_parts = []

            if is_sudo_user(user.id) or is_dev_user(user.id) or user.id == OWNER_ID:
                help_parts.append(ADMIN_NOTE_TEXT)
            
            if is_support_user(user.id) or is_sudo_user(user.id) or is_dev_user(user.id) or user.id == OWNER_ID:
                help_parts.append(SUPPORT_COMMANDS_TEXT)

            if is_sudo_user(user.id) or is_dev_user(user.id) or user.id == OWNER_ID:
                help_parts.append(SUDO_COMMANDS_TEXT)

            if is_dev_user(user.id) or user.id == OWNER_ID:
                help_parts.append(DEVELOPER_COMMANDS_TEXT)

            if user.id == OWNER_ID:
                help_parts.append(OWNER_COMMANDS_TEXT)
            
            final_sudo_help = "".join(help_parts)
            
            if final_sudo_help:
                await update.message.reply_html(final_sudo_help, disable_web_page_preview=True)
            return
            
    await update.message.reply_html(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_html(HELP_TEXT, disable_web_page_preview=True)
        return

    bot_username = context.bot.username
    deep_link_url = f"https://t.me/{bot_username}?start=help"
    
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="📬 Get Help (PM)", url=deep_link_url)]
        ]
    )
    
    message_text = "The help message has been sent to your private chat. Please click the button below to see it."
    
    await send_safe_reply(update, context, text=message_text, reply_markup=keyboard)

async def github(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    github_link = "https://github.com/R0Xofficial/ZenthronBot"
    await update.message.reply_text(f"This bot is open source. You can find the code here: {github_link}", disable_web_page_preview=True)

async def owner_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if OWNER_ID:
        owner_mention = f"<code>{OWNER_ID}</code>"; owner_name = "Bot Owner"
        try: owner_chat = await context.bot.get_chat(OWNER_ID); owner_mention = owner_chat.mention_html(); owner_name = owner_chat.full_name or owner_chat.username or owner_name
        except TelegramError as e: logger.warning(f"Could not fetch owner info ({OWNER_ID}): {e}")
        except Exception as e: logger.warning(f"Unexpected error fetching owner info: {e}")
        message = (f"My God is: 👤 <b>{safe_escape(owner_name)}</b> ({owner_mention})")
        await update.message.reply_html(message)
    else: await update.message.reply_text("Error: Owner information is not configured.")

def format_entity_info(entity: Chat | User,
                       chat_member_obj: telegram.ChatMember | None = None,
                       is_target_bot: bool = False,
                       is_target_owner: bool = False,
                       is_target_dev: bool = False,
                       is_target_sudo: bool = False,
                       is_target_support: bool = False,
                       is_target_whitelist: bool = False,
                       blacklist_reason_str: str | None = None,
                       gban_reason_str: str | None = None,
                       current_chat_id_for_status: int | None = None,
                       bot_context: ContextTypes.DEFAULT_TYPE | None = None
                       ) -> str:
    
    info_lines = []
    entity_id = entity.id
    is_user_type = isinstance(entity, User) 
    entity_chat_type = getattr(entity, 'type', None) if not is_user_type else ChatType.PRIVATE

    if is_user_type or entity_chat_type == ChatType.PRIVATE:
        user = entity
        info_lines.append(f"👤 <b>User Information:</b>\n")        
        first_name = safe_escape(getattr(user, 'first_name', "N/A") or "N/A")
        last_name = safe_escape(getattr(user, 'last_name', "") or "")
        username_display = f"@{safe_escape(user.username)}" if user.username else "N/A"
        permalink_user_url = f"tg://user?id={user.id}"
        permalink_text_display = "Link" 
        permalink_html_user = f"<a href=\"{permalink_user_url}\">{permalink_text_display}</a>"
        is_bot_val = getattr(user, 'is_bot', False)
        is_bot_str = "Yes" if is_bot_val else "No"
        language_code_val = getattr(user, 'language_code', "N/A")

        info_lines.extend([
            f"<b>• ID:</b> <code>{user.id}</code>",
            f"<b>• First Name:</b> {first_name}",
        ])
        if getattr(user, 'last_name', None):
            info_lines.append(f"<b>• Last Name:</b> {last_name}")
        
        info_lines.extend([
            f"<b>• Username:</b> {username_display}",
            f"<b>• Permalink:</b> {permalink_html_user}",
            f"<b>• Is Bot:</b> <code>{is_bot_str}</code>",
            f"<b>• Language Code:</b> <code>{language_code_val if language_code_val else 'N/A'}</code>"
        ])

        if chat_member_obj:
            status = chat_member_obj.status
            display_status = ""
    
            if status == "creator":
                display_status = "<code>Creator</code>"
            elif status == "administrator":
                display_status = "<code>Admin</code>"
            elif status == "kicked":
                display_status = "<code>Banned</code>"
            elif status == "left":
                display_status = "<code>Not in chat</code>"
            elif status == "restricted":
                if getattr(chat_member_obj, 'can_send_messages', True) is False:
                    display_status = "<code>Muted</code>"
                else:
                    display_status = "<code>Member (Excepted)</code>"
            elif status == "member":
                if getattr(chat_member_obj, 'can_send_messages', True) is False:
                     display_status = "<code>Muted</code>"
                else:
                     display_status = "<code>Member</code>"

            elif status == "not_a_member":
                display_status = "<code>Not in chat</code>"
            
            if display_status:
                info_lines.append(f"<b>• Status:</b> {display_status}")

        if is_target_bot:
            info_lines.append(f"\n<b>• That’s me!</b> <code>BOMBOCLAT!</code>")
        elif is_target_owner:
            info_lines.append(f"\n<b>• User Level:</b> <code>God</code>")
        elif is_target_dev:
            info_lines.append(f"\n<b>• User Level:</b> <code>Developer</code>")
        elif is_target_sudo:
            info_lines.append(f"\n<b>• User Level:</b> <code>Sudo</code>")
        elif is_target_support:
            info_lines.append(f"\n<b>• User Level:</b> <code>Support</code>")
        elif is_target_whitelist:
            info_lines.append(f"\n<b>• User Level:</b> <code>Whitelist</code>")
            
        if blacklist_reason_str is not None:
            info_lines.append(f"\n<b>• Blacklisted:</b> <code>Yes</code>")
            info_lines.append(f"<b>Reason:</b> {safe_escape(blacklist_reason_str)}")
        else:
            info_lines.append(f"\n<b>• Blacklisted:</b> <code>No</code>")

        if gban_reason_str is not None:
            info_lines.append(f"\n<b>• Globally Banned:</b> <code>Yes</code>")
            info_lines.append(f"<b>Reason:</b> {safe_escape(gban_reason_str)}")
        else:
            info_lines.append(f"\n<b>• Globally Banned:</b> <code>No</code>")

        if gban_reason_str is not None or blacklist_reason_str is not None:
            info_lines.append(f"\n<b>Appeal Chat:</b> {APPEAL_CHAT_USERNAME}")

    elif entity_chat_type == ChatType.CHANNEL:
        channel = entity
        info_lines.append(f"📢 <b>Channel info:</b>\n")
        info_lines.append(f"<b>• ID:</b> <code>{channel.id}</code>")
        channel_name_to_display = channel.title or getattr(channel, 'first_name', None) or f"Channel {channel.id}"
        info_lines.append(f"<b>• Title:</b> {safe_escape(channel_name_to_display)}")
        
        if channel.username:
            info_lines.append(f"<b>• Username:</b> @{safe_escape(channel.username)}")
            permalink_channel_url = f"https://t.me/{safe_escape(channel.username)}"
            permalink_text_display = "Link"
            permalink_channel_html = f"<a href=\"{permalink_channel_url}\">{permalink_text_display}</a>"
            info_lines.append(f"<b>• Permalink:</b> {permalink_channel_html}")
        else:
            info_lines.append(f"<b>• Permalink:</b> Private channel (no public link)")
        
    elif entity_chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        chat = entity
        title = safe_escape(chat.title or f"{entity_chat_type.capitalize()} {chat.id}")
        info_lines.append(f"ℹ️ Entity <code>{chat.id}</code> is a <b>{entity_chat_type.capitalize()}</b> ({title}).")
        info_lines.append(f"This command primarily provides detailed info for Users and Channels.")

    else:
        info_lines.append(f"❓ <b>Unknown or Unsupported Entity Type:</b> ID <code>{safe_escape(str(entity_id))}</code>")
        if entity_chat_type:
            info_lines.append(f"  • Type detected: {entity_chat_type.capitalize()}")

    return "\n".join(info_lines)

async def entity_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target_entity: Chat | User | None = None
    
    if update.message.reply_to_message:
        target_entity = update.message.reply_to_message.sender_chat or update.message.reply_to_message.from_user
    elif context.args:
        target_input = " ".join(context.args)
        
        target_entity = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_entity:
            try:
                target_entity = await context.bot.get_chat(target_input)
            except Exception:
                await update.message.reply_text(f"Error: I couldn't find the user. Most likely I've never seen him.")
                return
    else:
        target_entity = update.message.sender_chat or update.effective_user

    if not target_entity:
        await update.message.reply_text("Skrrrt... I don't know what I'm looking for...")
        return

    if isinstance(target_entity, User):
        update_user_in_db(target_entity)

    is_target_bot_flag = (target_entity.id == context.bot.id)
    is_target_owner_flag = (target_entity.id == OWNER_ID)
    is_target_dev_flag = is_dev_user(target_entity.id)
    is_target_sudo_flag = is_sudo_user(target_entity.id)
    is_target_support_flag = is_support_user(target_entity.id)
    is_target_whitelist_flag = is_whitelisted(target_entity.id)
    blacklist_reason_str = get_blacklist_reason(target_entity.id)
    gban_reason_str = get_gban_reason(target_entity.id)
    chat_member_obj: telegram.ChatMember | None = None
    
    if isinstance(target_entity, User) and update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        try:
            chat_member_obj = await context.bot.get_chat_member(update.effective_chat.id, target_entity.id)
        except TelegramError:
            pass 

    info_message = format_entity_info(
        entity=target_entity,
        chat_member_obj=chat_member_obj,
        is_target_bot=is_target_bot_flag,
        is_target_owner=is_target_owner_flag,
        is_target_dev=is_target_dev_flag,
        is_target_sudo=is_target_sudo_flag,
        is_target_support=is_target_support_flag,
        is_target_whitelist=is_target_whitelist_flag,
        blacklist_reason_str=blacklist_reason_str,
        gban_reason_str=gban_reason_str,
        current_chat_id_for_status=update.effective_chat.id
    )
    
    await update.message.reply_html(info_message, disable_web_page_preview=True)

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    
    target_user: User | None = None
    
    if message.reply_to_message:
        if message.reply_to_message.sender_chat:
            target_chat = message.reply_to_message.sender_chat
            await message.reply_html(f"<b>The ID of {safe_escape(target_chat.title)} is:</b> <code>{target_chat.id}</code>")
            return
        else:
            target_user = message.reply_to_message.from_user

    elif context.args:
        target_input = context.args[0]
        if target_input.startswith('@'):
            resolved_entity = await resolve_user_with_telethon(context, target_input, update)
            if isinstance(resolved_entity, User):
                target_user = resolved_entity
            else:
                await message.reply_text(f"Could not find a user with the username {safe_escape(target_input)}.")
                return
        else:
            await message.reply_text("Invalid argument. Please use @username or reply to a message to get a user's ID.")
            return

    if target_user:
        await message.reply_html(f"<b>{safe_escape(target_user.first_name)}'s ID is:</b> <code>{target_user.id}</code>")
        return

    if chat.type == ChatType.PRIVATE:
        await message.reply_html(f"<b>Your ID is:</b> <code>{user.id}</code>")
    else:
        await message.reply_html(f"<b>This chat's ID is:</b> <code>{chat.id}</code>")

async def chat_sinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays basic statistics about the current chat."""
    chat = update.effective_chat
    if not chat:
        await update.message.reply_text("Could not get chat information for some reason.")
        return

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        await update.message.reply_text("This command shows stats for groups, supergroups, or channels.")
        return

    try:
        full_chat_object = await context.bot.get_chat(chat_id=chat.id)
    except TelegramError as e:
        logger.error(f"Failed to get full chat info for /chatstats in chat {chat.id}: {e}")
        await update.message.reply_html(f"Error: Couldn't fetch detailed stats for this chat. Reason: {safe_escape(str(e))}")
        return
    except Exception as e:
        logger.error(f"Unexpected error fetching full chat info for /chatstats in chat {chat.id}: {e}", exc_info=True)
        await update.message.reply_html(f"An unexpected error occurred while fetching chat stats.")
        return

    chat_title_display = full_chat_object.title or full_chat_object.first_name or f"Chat ID {full_chat_object.id}"
    info_lines = [f"🔎 <b>Chat stats for: {safe_escape(chat_title_display)}</b>\n"]

    info_lines.append(f"<b>• ID:</b> <code>{full_chat_object.id}</code>")

    chat_description = getattr(full_chat_object, 'description', None)
    if chat_description:
        desc_preview = chat_description[:70]
        info_lines.append(f"<b>• Description:</b> {safe_escape(desc_preview)}{'...' if len(chat_description) > 70 else ''}")
    else:
        info_lines.append(f"<b>• Description:</b> Not set")
    
    if getattr(full_chat_object, 'photo', None):
        info_lines.append(f"<b>• Chat Photo:</b> <code>Yes</code>")
    else:
        info_lines.append(f"<b>• Chat Photo:</b> <code>No</code>")

    slow_mode_delay_val = getattr(full_chat_object, 'slow_mode_delay', None)
    if slow_mode_delay_val and slow_mode_delay_val > 0:
        info_lines.append(f"<b>• Slow Mode:</b> <code>Enabled</code> ({slow_mode_delay_val}s)")
    else:
        info_lines.append(f"<b>• Slow Mode:</b> <code>Disabled</code>")
    
    try:
        member_count = await context.bot.get_chat_member_count(chat_id=full_chat_object.id)
        info_lines.append(f"<b>• Total Members:</b> <code>{member_count}</code>")
    except TelegramError as e:
        logger.warning(f"Could not get member count for /chatstats in chat {full_chat_object.id}: {e}")
        info_lines.append(f"<b>• Total Members:</b> N/A (Error fetching)")
    except Exception as e:
        logger.error(f"Unexpected error in get_chat_member_count for /chatstats in {full_chat_object.id}: {e}", exc_info=True)
        info_lines.append(f"<b>• Total Members:</b> N/A (Unexpected error)")

    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        status_line = "<b>• Gban Enforcement:</b> "
        
        if not is_gban_enforced(chat.id):
            status_line += "<code>Disabled</code>"
        else:
            try:
                bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
                if bot_member.status == "administrator" and bot_member.can_restrict_members:
                    status_line += "<code>Enabled</code>"
                else:
                    status_line += "<code>Disabled</code>\n<i>Reason: Bot needs 'Ban Users' permission</i>"
            except Exception:
                status_line += "<code>Disabled</code>\n<i>Reason: Could not verify bot permissions</i>"
        
        info_lines.append(status_line)

    message_text = "\n".join(info_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

async def chat_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /cinfo attempt by user {user.id}.")
        return

    target_chat_id: int | None = None
    chat_object_for_details: Chat | None = None

    if context.args:
        try:
            target_chat_id = int(context.args[0])
            logger.info(f"Privileged user {user.id} calling /cinfo with target chat ID: {target_chat_id}")
            try:
                chat_object_for_details = await context.bot.get_chat(chat_id=target_chat_id)
            except TelegramError as e:
                logger.error(f"Failed to get chat info for ID {target_chat_id}: {e}")
                await update.message.reply_html(f"Error: Couldn't fetch info for chat ID <code>{target_chat_id}</code>. Reason: {safe_escape(str(e))}.")
                return
            except Exception as e:
                logger.error(f"Unexpected error fetching chat info for ID {target_chat_id}: {e}", exc_info=True)
                await update.message.reply_html(f"An unexpected error occurred trying to get info for chat ID <code>{target_chat_id}</code>.")
                return
        except ValueError:
            await update.message.reply_text("Invalid chat ID format. Please provide a numeric ID.")
            return
    else:
        effective_chat_obj = update.effective_chat
        if effective_chat_obj:
             target_chat_id = effective_chat_obj.id
             try:
                 chat_object_for_details = await context.bot.get_chat(chat_id=target_chat_id)
                 logger.info(f"Privileged user {user.id} calling /cinfo for current chat: {target_chat_id}")
             except TelegramError as e:
                logger.error(f"Failed to get full chat info for current chat ID {target_chat_id}: {e}")
                await update.message.reply_html(f"Error: Couldn't fetch full info for current chat. Reason: {safe_escape(str(e))}.")
                return
             except Exception as e:
                logger.error(f"Unexpected error fetching full info for current chat ID {target_chat_id}: {e}", exc_info=True)
                await update.message.reply_html(f"An unexpected error occurred trying to get full info for current chat.")
                return
        else:
             await update.message.reply_text("Could not determine current chat.")
             return

    if not chat_object_for_details or target_chat_id is None:
        await update.message.reply_text("Couldn't determine the chat to inspect.")
        return

    if chat_object_for_details.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        await update.message.reply_text("This command provides info about groups, supergroups, or channels.")
        return

    bot_id = context.bot.id
    chat_title_display = chat_object_for_details.title or chat_object_for_details.first_name or f"Chat ID {target_chat_id}"
    info_lines = [f"🔎 <b>Chat Information for: {safe_escape(chat_title_display)}</b>\n"]

    info_lines.append(f"<b>• ID:</b> <code>{target_chat_id}</code>")
    info_lines.append(f"<b>• Type:</b> {chat_object_for_details.type.capitalize()}")

    chat_description = getattr(chat_object_for_details, 'description', None)
    if chat_description:
        desc_preview = chat_description[:200]
        info_lines.append(f"<b>• Description:</b> {safe_escape(desc_preview)}{'...' if len(chat_description) > 200 else ''}")
    
    if getattr(chat_object_for_details, 'photo', None):
        info_lines.append(f"<b>• Chat Photo:</b> Yes")
    else:
        info_lines.append(f"<b>• Chat Photo:</b> No")

    chat_link_line = ""
    if chat_object_for_details.username:
        chat_link = f"https://t.me/{chat_object_for_details.username}"
        chat_link_line = f"<b>• Link:</b> <a href=\"{chat_link}\">@{chat_object_for_details.username}</a>"
    elif chat_object_for_details.type != ChatType.CHANNEL:
        try:
            bot_member = await context.bot.get_chat_member(chat_id=target_chat_id, user_id=bot_id)
            if bot_member.status == "administrator" and bot_member.can_invite_users:
                link_name = f"cinfo_{str(target_chat_id)[-5:]}_{random.randint(100,999)}"
                invite_link_obj = await context.bot.create_chat_invite_link(chat_id=target_chat_id, name=link_name)
                chat_link_line = f"<b>• Generated Invite Link:</b> {invite_link_obj.invite_link} (temporary)"
            else:
                chat_link_line = "<b>• Link:</b> Private group (no public link, bot cannot generate one)"
        except TelegramError as e:
            logger.warning(f"Could not create/check invite link for private chat {target_chat_id}: {e}")
            chat_link_line = f"<b>• Link:</b> Private group (no public link, error: {safe_escape(str(e))})"
        except Exception as e:
            logger.error(f"Unexpected error with invite link for {target_chat_id}: {e}", exc_info=True)
            chat_link_line = "<b>• Link:</b> Private group (no public link, unexpected error)"
    else:
        chat_link_line = "<b>• Link:</b> Private channel (no public/invite link via bot)"
    info_lines.append(chat_link_line)

    pinned_message_obj = getattr(chat_object_for_details, 'pinned_message', None)
    if pinned_message_obj:
        pin_text_preview = pinned_message_obj.text or pinned_message_obj.caption or "[Media/No Text]"
        pin_link = "#" 
        if chat_object_for_details.username:
             pin_link = f"https://t.me/{chat_object_for_details.username}/{pinned_message_obj.message_id}"
        elif str(target_chat_id).startswith("-100"):
             chat_id_for_link = str(target_chat_id).replace("-100","")
             pin_link = f"https://t.me/c/{chat_id_for_link}/{pinned_message_obj.message_id}"
        info_lines.append(f"<b>• Pinned Message:</b> <a href=\"{pin_link}\">'{safe_escape(pin_text_preview[:50])}{'...' if len(pin_text_preview) > 50 else ''}'</a>")
    
    linked_chat_id_val = getattr(chat_object_for_details, 'linked_chat_id', None)
    if linked_chat_id_val:
        info_lines.append(f"<b>• Linked Chat ID:</b> <code>{linked_chat_id_val}</code>")
    
    slow_mode_delay_val = getattr(chat_object_for_details, 'slow_mode_delay', None)
    if slow_mode_delay_val and slow_mode_delay_val > 0:
        info_lines.append(f"<b>• Slow Mode:</b> Enabled ({slow_mode_delay_val}s)")

    member_count_val: int | str = "N/A"; admin_count_val: int | str = 0
    try:
        member_count_val = await context.bot.get_chat_member_count(chat_id=target_chat_id)
        info_lines.append(f"<b>• Total Members:</b> {member_count_val}")
    except Exception as e:
        logger.error(f"Error get_chat_member_count for {target_chat_id}: {e}")
        info_lines.append(f"<b>• Total Members:</b> Error fetching")

    admin_list_str_parts = ["<b>• Administrators:</b>"]
    admin_details_list = []
    try:
        administrators = await context.bot.get_chat_administrators(chat_id=target_chat_id)
        admin_count_val = len(administrators)
        admin_list_str_parts.append(f"  <b>• Total:</b> {admin_count_val}")
        for admin_member in administrators:
            admin_user = admin_member.user
            admin_name_display = f"ID: {admin_user.id if admin_user else 'N/A'}"
            if admin_user:
                admin_name_display = admin_user.mention_html() if admin_user.username else safe_escape(admin_user.full_name or admin_user.first_name or f"ID: {admin_user.id}")
            detail_line = f"    • {admin_name_display}"
            current_admin_status_str = getattr(admin_member, 'status', None)
            if current_admin_status_str == "creator":
                detail_line += " (Creator 👑)"
            admin_details_list.append(detail_line)
        if admin_details_list:
            admin_list_str_parts.append("  <b>• List:</b>")
            admin_list_str_parts.extend(admin_details_list)
    except Exception as e:
        admin_list_str_parts.append("  <b>• Error fetching admin list.</b>")
        admin_count_val = "Error"
        logger.error(f"Error get_chat_administrators for {target_chat_id}: {e}", exc_info=True)
    info_lines.append("\n".join(admin_list_str_parts))

    if isinstance(member_count_val, int) and isinstance(admin_count_val, int) and admin_count_val >=0:
         other_members_count = member_count_val - admin_count_val
         info_lines.append(f"<b>• Other Members:</b> {other_members_count if other_members_count >= 0 else 'N/A'}")

    bot_status_lines = ["\n<b>• Bot Status in this Chat:</b>"]
    try:
        bot_member_on_chat = await context.bot.get_chat_member(chat_id=target_chat_id, user_id=bot_id)
        bot_current_status_str = bot_member_on_chat.status
        bot_status_lines.append(f"  <b>• Status:</b> {bot_current_status_str.capitalize()}")
        if bot_current_status_str == "administrator":
            bot_status_lines.append(f"  <b>• Can invite users:</b> {'Yes' if bot_member_on_chat.can_invite_users else 'No'}")
            bot_status_lines.append(f"  <b>• Can restrict members:</b> {'Yes' if bot_member_on_chat.can_restrict_members else 'No'}")
            bot_status_lines.append(f"  <b>• Can pin messages:</b> {'Yes' if getattr(bot_member_on_chat, 'can_pin_messages', None) else 'No'}")
            bot_status_lines.append(f"  <b>• Can manage chat:</b> {'Yes' if getattr(bot_member_on_chat, 'can_manage_chat', None) else 'No'}")
        else:
            bot_status_lines.append("  <b>• Note:</b> Bot is not an admin here.")
    except TelegramError as e:
        if "user not found" in str(e).lower() or "member not found" in str(e).lower():
             bot_status_lines.append("  <b>• Status:</b> Not a member")
        else:
            bot_status_lines.append(f"  <b>• Error fetching bot status:</b> {safe_escape(str(e))}")
    except Exception as e:
        bot_status_lines.append("  <b>• Unexpected error fetching bot status.")
        logger.error(f"Unexpected error getting bot status in {target_chat_id}: {e}", exc_info=True)
    info_lines.append("\n".join(bot_status_lines))
    
    chat_permissions = getattr(chat_object_for_details, 'permissions', None)
    if chat_permissions:
        perms = chat_permissions
        perm_lines = ["\n<b>• Default Member Permissions:</b>"]
        perm_lines.append(f"  <b>• Send Messages:</b> {'Yes' if getattr(perms, 'can_send_messages', False) else 'No'}")
        
        can_send_any_media = (
            getattr(perms, 'can_send_audios', False) or
            getattr(perms, 'can_send_documents', False) or
            getattr(perms, 'can_send_photos', False) or 
            getattr(perms, 'can_send_videos', False) or
            getattr(perms, 'can_send_video_notes', False) or
            getattr(perms, 'can_send_voice_notes', False) or
            getattr(perms, 'can_send_media_messages', False)
        )
        perm_lines.append(f"  <b>• Send Media:</b> {'Yes' if can_send_any_media else 'No'}")
        perm_lines.append(f"  <b>• Send Polls:</b> {'Yes' if getattr(perms, 'can_send_polls', False) else 'No'}")
        perm_lines.append(f"  <b>• Send Other Messages:</b> {'Yes' if getattr(perms, 'can_send_other_messages', False) else 'No'}")
        perm_lines.append(f"  <b>• Add Web Page Previews:</b> {'Yes' if getattr(perms, 'can_add_web_page_previews', False) else 'No'}")
        perm_lines.append(f"  <b>• Change Info:</b> {'Yes' if getattr(perms, 'can_change_info', False) else 'No'}")
        perm_lines.append(f"  <b>• Invite Users:</b> {'Yes' if getattr(perms, 'can_invite_users', False) else 'No'}")
        perm_lines.append(f"  <b>• Pin Messages:</b> {'Yes' if getattr(perms, 'can_pin_messages', False) else 'No'}")
        if hasattr(perms, 'can_manage_topics'):
            perm_lines.append(f"  <b>• Manage Topics:</b> {'Yes' if perms.can_manage_topics else 'No'}")
        info_lines.extend(perm_lines)

    message_text = "\n".join(info_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("github", github))
    application.add_handler(CommandHandler("owner", owner_info))
    application.add_handler(CommandHandler("info", entity_info_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("chatinfo", chat_sinfo_command))
    application.add_handler(CommandHandler("cinfo", chat_info_command))
