import asyncio
import html
import io
import logging
import platform
import random
import sqlite3
import subprocess
import time
from datetime import datetime, timezone, timedelta
from telegram import Update, User, Chat
from telegram import __version__ as ptb_version
from telethon import __version__ as telethon_version
from telegram.constants import ParseMode, ChatType, ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from ..config import BOT_START_TIME, DB_NAME, OWNER_ID, ADMIN_LOG_CHAT_ID
from ..core.database import (
    get_all_bot_chats_from_db, remove_chat_from_db_by_id,
    get_all_dev_users_from_db, add_dev_user, remove_dev_user,
    get_all_sudo_users_from_db, add_sudo_user, remove_sudo_user,
    get_all_support_users_from_db, add_support_user, remove_support_user,
    get_all_whitelist_users_from_db, add_to_whitelist, remove_from_whitelist,
    is_dev_user, is_sudo_user, is_support_user,
    is_whitelisted, get_gban_reason, get_blacklist_reason,
    get_user_from_db_by_username, delete_user_from_db
)
from ..core.utils import (
    is_owner_or_dev, get_readable_time_delta, safe_escape, resolve_user_with_telethon,
    create_user_html_link, send_operational_log, is_privileged_user, run_speed_test_async, is_entity_a_user
)
from ..core.constants import LEAVE_TEXTS
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- CORE HANDLER FUNCTIONS ---
@check_module_enabled("core")
@custom_handler("status")
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /status attempt by user {user.id}.")
        return

    uptime_delta = datetime.now() - BOT_START_TIME 
    readable_uptime = get_readable_time_delta(uptime_delta)
    
    python_version = platform.python_version()
    sqlite_version = sqlite3.sqlite_version

    neofetch_output = ""
    try:
        process = await asyncio.create_subprocess_shell(
            "neofetch --stdout --config none",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if stdout:
            lines = stdout.decode('utf-8').strip().split('\n')
            filtered_lines = []
            for line in lines:
                if '---' in line or '@' in line:
                    continue
                filtered_lines.append(line)
            
            neofetch_output = "\n".join(filtered_lines)
            
        elif stderr:
            logger.warning(f"Neofetch returned an error: {stderr.decode('utf-8')}")
            neofetch_output = "Neofetch not found or failed to run. Check if you have it installed | pkg install neofetch"

    except FileNotFoundError:
        logger.warning("Neofetch command not found. Skipping.")
        neofetch_output = "Neofetch not installed."
    except Exception as e:
        logger.error(f"Error running neofetch: {e}")
        neofetch_output = "An error occurred while fetching system info."

    status_lines = [
        "<b>Bot Status:</b>",
        "<b>• State:</b> <code>Online and operational</code>",
        f"<b>• Uptime:</b> <code>{readable_uptime}</code>",
        "",
        "<b>System Info:</b>",
        f"<code>{safe_escape(neofetch_output)}</code>",
        "",
        "<b>Software Info:</b>",
        f"<b>• Python:</b> <code>{python_version}</code>",
        f"<b>• python-telegram-bot:</b> <code>{ptb_version}</code>",
        f"<b>• Telethon:</b> <code>{telethon_version}</code>",
        f"<b>• SQLite:</b> <code>{sqlite_version}</code>",
    ]

    status_msg = "\n".join(status_lines)
    await update.message.reply_html(status_msg)

@check_module_enabled("core")
@custom_handler("stats")
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /stats attempt by user {user.id}.")
        return

    known_users_count = "N/A"
    blacklisted_count = "N/A"
    developer_users_count = "N/A"
    sudo_users_count = "N/A"
    support_users_count = "N/A"
    whitelist_users_count = "N/A"
    blacklisted_chats_count = "N/A"
    gban_count = "N/A"
    chat_count = "N/A"

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            known_users_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM blacklist")
            blacklisted_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM dev_users")
            developer_users_count = str(cursor.fetchone()[0])
                
            cursor.execute("SELECT COUNT(*) FROM sudo_users")
            sudo_users_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM support_users")
            support_users_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM whitelist_users")
            whitelist_users_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM chat_blacklist")
            blacklisted_chats_count = str(cursor.fetchone()[0])

            cursor.execute("SELECT COUNT(*) FROM global_bans")
            gban_count = str(cursor.fetchone()[0])
                
            cursor.execute("SELECT COUNT(*) FROM bot_chats")
            chat_count = str(cursor.fetchone()[0])
            
    except sqlite3.Error as e:
        logger.error(f"SQLite error fetching counts for /stats: {e}", exc_info=True)
        (known_users_count, blacklisted_count, developer_users_count, sudo_users_count, 
         support_users_count, whitelist_users_count, blacklisted_chats_count, gban_count, chat_count) = ("DB Error",) * 7

    stats_lines = [
        "<b>📊 Bot Database Stats:</b>\n",
        f"<b>• 💬 Chats:</b> <code>{chat_count}</code>",
        f"<b>• 🛑 Blacklisted Chats:</b> <code>{blacklisted_chats_count}</code>",
        f"<b>• 👀 Known Users:</b> <code>{known_users_count}</code>",
        f"<b>• 🛃 Developer Users:</b> <code>{developer_users_count}</code>",
        f"<b>• 🛡 Sudo Users:</b> <code>{sudo_users_count}</code>",
        f"<b>• 👷‍♂️ Support Users:</b> <code>{support_users_count}</code>",
        f"<b>• 🔰 Whitelist Users:</b> <code>{whitelist_users_count}</code>",
        f"<b>• 🚫 Blacklisted Users:</b> <code>{blacklisted_count}</code>",
        f"<b>• 🌍 Globally Banned Users:</b> <code>{gban_count}</code>"
    ]

    stats_msg = "\n".join(stats_lines)
    await update.message.reply_html(stats_msg)

@check_module_enabled("core")
@custom_handler("ping")
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_privileged_user(user.id):
        logger.warning(f"Unauthorized /ping attempt by user {user.id}.")
        return
    
    start_time = time.time()
    message = await update.message.reply_html("<b>Pinging...</b>")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await message.edit_text(
        f"🏓 <b>Pong!</b>\n"
        f"<b>Latency:</b> <code>{latency} ms</code>",
        parse_mode=ParseMode.HTML
    )

@check_module_enabled("core")
@custom_handler(["permissions", "perms"])
async def permissions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    if not message: return
    
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /permission attempt by user {user.id}.")
        return

    if chat.type == ChatType.PRIVATE:
        await message.reply_text("Huh? You can't check permissions in private chat...")
        return

    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
    except Exception as e:
        await message.reply_text(f"Could not fetch my own permissions. Error: {safe_escape(str(e))}")
        return
        
    if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
        await message.reply_html(
            "<b>🔧 My Permissions in this Chat:</b>\n\n"
            "I am not an administrator here, so I have only default member permissions."
        )
        return

    permissions_to_check = {
        "can_manage_chat": "Manage Chat",
        "can_delete_messages": "Delete Messages",
        "can_manage_video_chats": "Manage Video Chats",
        "can_restrict_members": "Restrict Members",
        "can_promote_members": "Promote Members",
        "can_change_info": "Change Chat Info",
        "can_invite_users": "Invite Users",
        "can_pin_messages": "Pin Messages",
        "can_manage_topics": "Manage Topics"
    }

    response_lines = ["<b>🔧 My Permissions in this Chat:</b>\n"]
    
    for perm_key, perm_name in permissions_to_check.items():
        has_permission = getattr(bot_member, perm_key, False)
        
        status_text = "Yes" if has_permission else "No"
        
        response_lines.append(f"• <b>{perm_name}:</b> <code>{status_text}</code>")

    await message.reply_html("\n".join(response_lines))

@check_module_enabled("core")
@custom_handler("echo")
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not (is_owner_or_dev(user.id) or is_sudo_user(user.id)):
        logger.warning(f"Unauthorized /echo attempt by user {user.id}.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /echo <optional_chat_id> [your message]")
        return

    target_chat_id_str = args[0]
    message_to_say_list = args
    target_chat_id = update.effective_chat.id
    is_remote_send = False

    try:
        potential_chat_id = int(target_chat_id_str)
        if len(target_chat_id_str) > 5 or potential_chat_id >= -1000:
            try:
                 await context.bot.get_chat(potential_chat_id)
                 if len(args) > 1:
                     target_chat_id = potential_chat_id
                     message_to_say_list = args[1:]
                     is_remote_send = True
                     logger.info(f"Privileged user {user.id} remote send detected. Target: {target_chat_id}")
                 else:
                     await update.message.reply_text("Target chat ID provided, but no message to send.")
                     return
            except TelegramError:
                 logger.info(f"Argument '{target_chat_id_str}' looks like ID but get_chat failed or not a valid target, sending to current chat.")
                 target_chat_id = update.effective_chat.id
                 message_to_say_list = args
                 is_remote_send = False
            except Exception as e:
                 logger.error(f"Unexpected error checking potential chat ID {potential_chat_id}: {e}")
                 target_chat_id = update.effective_chat.id
                 message_to_say_list = args
                 is_remote_send = False
        else:
             logger.info("First argument doesn't look like a chat ID, sending to current chat.")
             target_chat_id = update.effective_chat.id
             message_to_say_list = args
             is_remote_send = False
    except (ValueError, IndexError):
        logger.info("First argument is not numeric, sending to current chat.")
        target_chat_id = update.effective_chat.id
        message_to_say_list = args
        is_remote_send = False

    message_to_say = ' '.join(message_to_say_list)
    if not message_to_say:
        await update.message.reply_text("Cannot send an empty message.")
        return

    chat_title = f"Chat ID {target_chat_id}"
    safe_chat_title = chat_title
    try:
        target_chat_info = await context.bot.get_chat(target_chat_id)
        chat_title = target_chat_info.title or target_chat_info.first_name or f"Chat ID {target_chat_id}"
        safe_chat_title = safe_escape(chat_title)
        logger.info(f"Target chat title for /echo resolved to: '{chat_title}'")
    except TelegramError as e:
        logger.warning(f"Could not get chat info for {target_chat_id} for /echo confirmation: {e}")
    except Exception as e:
         logger.error(f"Unexpected error getting chat info for {target_chat_id} in /echo: {e}", exc_info=True)

    logger.info(f"Privileged user ({user.id}) using /echo. Target: {target_chat_id} ('{chat_title}'). Is remote: {is_remote_send}. Msg start: '{message_to_say[:50]}...'")

    try:
        await context.bot.send_message(chat_id=target_chat_id, text=message_to_say)
        if is_remote_send:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Message sent to <b>{safe_chat_title}</b> [<code>{target_chat_id}</code>].",
                parse_mode=ParseMode.HTML
            )
    except TelegramError as e:
        logger.error(f"Failed to send message via /echo to {target_chat_id} ('{chat_title}'): {e}")
        await update.message.reply_text(f"❌ Couldn't send message to <b>{safe_chat_title}</b> [<code>{target_chat_id}</code>]: {e}", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Unexpected error during /echo execution: {e}", exc_info=True)
        await update.message.reply_text(f"💥 Oops! An unexpected error occurred while trying to send the message to <b>{safe_chat_title}</b> [<code>{target_chat_id}</code>]. Check logs.", parse_mode=ParseMode.HTML)

@check_module_enabled("core")
@custom_handler("leave")
async def leave_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /leave attempt by user {user.id}.")
        return

    target_chat_id_to_leave: int | None = None
    chat_where_command_was_called_id = update.effective_chat.id
    is_leaving_current_chat = False

    if context.args:
        try:
            target_chat_id_to_leave = int(context.args[0])
            if target_chat_id_to_leave >= -100:
                await update.message.reply_text("Invalid Group/Channel ID format for leaving.")
                return
            logger.info(f"Privileged user {user.id} initiated remote leave for chat ID: {target_chat_id_to_leave}")
            if target_chat_id_to_leave == chat_where_command_was_called_id:
                is_leaving_current_chat = True
        except (ValueError, IndexError):
            await update.message.reply_text("Invalid chat ID format for leaving.")
            return
    else:
        if update.effective_chat.type == ChatType.PRIVATE:
            await update.message.reply_text("I can't leave a private chat.")
            return
        target_chat_id_to_leave = update.effective_chat.id
        is_leaving_current_chat = True
        logger.info(f"Privileged user {user.id} initiated leave for current chat: {target_chat_id_to_leave}")

    if target_chat_id_to_leave is None:
        await update.message.reply_text("Could not determine which chat to leave.")
        return

    admin_mention_for_farewell = create_user_html_link(user)

    chat_title_to_leave = f"Chat ID {target_chat_id_to_leave}"
    safe_chat_title_to_leave = chat_title_to_leave
    
    try:
        target_chat_info = await context.bot.get_chat(target_chat_id_to_leave)
        chat_title_to_leave = target_chat_info.title or target_chat_info.first_name or f"Chat ID {target_chat_id_to_leave}"
        safe_chat_title_to_leave = safe_escape(chat_title_to_leave)
    except TelegramError as e:
        logger.error(f"Could not get chat info for {target_chat_id_to_leave} before leaving: {e}")
        reply_to_chat_id_for_error = chat_where_command_was_called_id
        if is_leaving_current_chat: reply_to_chat_id_for_error = user.id
        
        error_message_text = f"❌ Cannot interact with chat <b>{safe_chat_title_to_leave}</b> [<code>{target_chat_id_to_leave}</code>]: {safe_escape(str(e))}. I might not be a member there."
        if "bot is not a member" in str(e).lower() or "chat not found" in str(e).lower():
            pass 
        else:
            error_message_text = f"⚠️ Couldn't get chat info for <code>{target_chat_id_to_leave}</code>: {safe_escape(str(e))}. Will attempt to leave anyway."
        
        if reply_to_chat_id_for_error:
            try: await context.bot.send_message(chat_id=reply_to_chat_id_for_error, text=error_message_text, parse_mode=ParseMode.HTML)
            except Exception as send_err: logger.error(f"Failed to send error about get_chat to {reply_to_chat_id_for_error}: {send_err}")
        if "bot is not a member" in str(e).lower() or "chat not found" in str(e).lower(): return
        
    except Exception as e:
         logger.error(f"Unexpected error getting chat info for {target_chat_id_to_leave}: {e}", exc_info=True)
         reply_to_chat_id_for_error = chat_where_command_was_called_id
         if is_leaving_current_chat: reply_to_chat_id_for_error = user.id
         if reply_to_chat_id_for_error:
             try: await context.bot.send_message(chat_id=reply_to_chat_id_for_error, text=f"⚠️ Unexpected error getting chat info for <code>{target_chat_id_to_leave}</code>. Will attempt to leave anyway.", parse_mode=ParseMode.HTML)
             except Exception as send_err: logger.error(f"Failed to send error about get_chat to {reply_to_chat_id_for_error}: {send_err}")

    if LEAVE_TEXTS:
        farewell_message = random.choice(LEAVE_TEXTS).format(admin_mention=admin_mention_for_farewell, chat_title=f"<b>{safe_chat_title_to_leave}</b>")
        try:
            await context.bot.send_message(chat_id=target_chat_id_to_leave, text=farewell_message, parse_mode=ParseMode.HTML)
            logger.info(f"Sent farewell message to {target_chat_id_to_leave}")
        except TelegramError as e:
            logger.error(f"Failed to send farewell message to {target_chat_id_to_leave}: {e}.")
            if "forbidden: bot is not a member" in str(e).lower() or "chat not found" in str(e).lower():
                logger.warning(f"Bot is not a member of {target_chat_id_to_leave} or chat not found. Cannot send farewell.")
                reply_to_chat_id_for_error = chat_where_command_was_called_id
                if is_leaving_current_chat: reply_to_chat_id_for_error = user.id
                if reply_to_chat_id_for_error:
                    try: await context.bot.send_message(chat_id=reply_to_chat_id_for_error, text=f"❌ Failed to send farewell to <b>{safe_chat_title_to_leave}</b> [<code>{target_chat_id_to_leave}</code>]: {safe_escape(str(e))}. Bot is not a member.", parse_mode=ParseMode.HTML)
                    except Exception as send_err: logger.error(f"Failed to send error about farewell to {reply_to_chat_id_for_error}: {send_err}")
                return 
        except Exception as e:
             logger.error(f"Unexpected error sending farewell message to {target_chat_id_to_leave}: {e}", exc_info=True)
    elif not LEAVE_TEXTS:
        logger.warning("LEAVE_TEXTS list is empty! Skipping farewell message.")

    try:
        success = await context.bot.leave_chat(chat_id=target_chat_id_to_leave)
        
        confirmation_target_chat_id = chat_where_command_was_called_id
        if is_leaving_current_chat:
            confirmation_target_chat_id = user.id

        if success:
            logger.info(f"Successfully left chat {target_chat_id_to_leave} ('{chat_title_to_leave}')")
            if confirmation_target_chat_id:
                await context.bot.send_message(chat_id=confirmation_target_chat_id, 
                                               text=f"✅ Successfully left chat: <b>{safe_chat_title_to_leave}</b> [<code>{target_chat_id_to_leave}</code>]", 
                                               parse_mode=ParseMode.HTML)
        else:
            logger.warning(f"leave_chat returned False for {target_chat_id_to_leave}. Bot might not have been a member.")
            if confirmation_target_chat_id:
                await context.bot.send_message(chat_id=confirmation_target_chat_id,
                                               text=f"🤔 Attempted to leave <b>{safe_chat_title_to_leave}</b> [<code>{target_chat_id_to_leave}</code>], but the operation indicated I might not have been there or lacked permission.", 
                                               parse_mode=ParseMode.HTML)
    except TelegramError as e:
        logger.error(f"Failed to leave chat {target_chat_id_to_leave}: {e}")
        confirmation_target_chat_id = chat_where_command_was_called_id
        if is_leaving_current_chat:
            confirmation_target_chat_id = user.id
        if confirmation_target_chat_id:
            await context.bot.send_message(chat_id=confirmation_target_chat_id,
                                           text=f"❌ Failed to leave chat <b>{safe_chat_title_to_leave}</b> [<code>{target_chat_id_to_leave}</code>]: {safe_escape(str(e))}", 
                                           parse_mode=ParseMode.HTML)
    except Exception as e:
         logger.error(f"Unexpected error during leave process for {target_chat_id_to_leave}: {e}", exc_info=True)
         confirmation_target_chat_id = chat_where_command_was_called_id
         if is_leaving_current_chat:
            confirmation_target_chat_id = user.id
         if confirmation_target_chat_id:
            await context.bot.send_message(chat_id=confirmation_target_chat_id,
                                           text=f"💥 Unexpected error leaving chat <b>{safe_chat_title_to_leave}</b> [<code>{target_chat_id_to_leave}</code>]. Check logs.", 
                                           parse_mode=ParseMode.HTML)

@check_module_enabled("core")
@custom_handler("speedtest")
async def speedtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /speedtest attempt by user {user.id}.")
        return

    message = await update.message.reply_text("Starting speed test... this might take a moment.")
    
    loop = asyncio.get_event_loop()
    try:
        results = await run_speed_test_async()
        await asyncio.sleep(4)

        if results and "error" not in results:
            ping_val = results.get("ping", 0.0)
            download_bps = results.get("download", 0)
            upload_bps = results.get("upload", 0)
            
            download_mbps_val = download_bps / 1000 / 1000
            upload_mbps_val = upload_bps / 1000 / 1000

            bytes_sent_val = results.get("bytes_sent", 0)
            bytes_received_val = results.get("bytes_received", 0)
            data_sent_mb_val = bytes_sent_val / 1024 / 1024
            data_received_mb_val = bytes_received_val / 1024 / 1024
            
            timestamp_str_val = results.get("timestamp", "N/A")
            formatted_time_val = "N/A"
            if timestamp_str_val != "N/A":
                try:
                    dt_obj = datetime.fromisoformat(timestamp_str_val.replace("Z", "+00:00"))
                    formatted_time_val = dt_obj.strftime('%Y-%m-%d %H:%M:%S %Z') 
                except ValueError:
                    formatted_time_val = safe_escape(timestamp_str_val)

            server_info_dict = results.get("server", {})
            server_name_val = server_info_dict.get("name", "N/A")
            server_country_val = server_info_dict.get("country", "N/A")
            server_cc_val = server_info_dict.get("cc", "N/A")
            server_sponsor_val = server_info_dict.get("sponsor", "N/A")
            server_lat_val = server_info_dict.get("lat", "N/A")
            server_lon_val = server_info_dict.get("lon", "N/A")

            info_lines = [
                "<b>🌐 Ookla SPEEDTEST:</b>\n",
                "<b>📊 RESULTS:</b>",
                f" <b>• 📤 Upload:</b> <code>{upload_mbps_val:.2f} Mbps</code>",
                f" <b>• 📥 Download:</b> <code>{download_mbps_val:.2f} Mbps</code>",
                f" <b>• ⏳️ Ping:</b> <code>{ping_val:.2f} ms</code>",
                f" <b>• 🕒 Time:</b> <code>{formatted_time_val}</code>",
                f" <b>• 📨 Data Sent:</b> <code>{data_sent_mb_val:.2f} MB</code>",
                f" <b>• 📩 Data Received:</b> <code>{data_received_mb_val:.2f} MB</code>\n",
                "<b>🖥 SERVER INFO:</b>",
                f" <b>• 🪪 Name:</b> <code>{safe_escape(server_name_val)}</code>",
                f" <b>• 🌍 Country:</b> <code>{safe_escape(server_country_val)} ({safe_escape(server_cc_val)})</code>",
                f" <b>• 🛠 Sponsor:</b> <code>{safe_escape(server_sponsor_val)}</code>",
                f" <b>• 🧭 Latitude:</b> <code>{server_lat_val}</code>",
                f" <b>• 🧭 Longitude:</b> <code>{server_lon_val}</code>"
            ]
            
            result_message = "\n".join(info_lines)
            await context.bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text=result_message, parse_mode=ParseMode.HTML)
        
        elif results and "error" in results:
            error_msg = results["error"]
            await context.bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text=f"Error: Speed test failed: {safe_escape(error_msg)}")
        else:
            await context.bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text="Error: Speed test failed to return results or returned an unexpected format.")

    except Exception as e:
        logger.error(f"Error in speedtest_command outer try-except: {e}", exc_info=True)
        try:
            await context.bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text=f"An unexpected error occurred during the speed test: {safe_escape(str(e))}")
        except Exception:
            pass

@check_module_enabled("core")
@custom_handler("listsudo")
async def list_sudo_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listsudo attempt by user {user.id}.")
        return

    sudo_user_tuples = get_all_sudo_users_from_db()

    if not sudo_user_tuples:
        await update.message.reply_text("There are currently no users with sudo privileges.")
        return

    response_lines = ["<b>🛡️ Sudo Users List:</b>\n"]
    
    for user_id, timestamp_str in sudo_user_tuples:
        user_display_name = f"<code>{user_id}</code>"

        try:
            chat_info = await context.bot.get_chat(user_id)
            name_parts = []
            if chat_info.first_name: name_parts.append(safe_escape(chat_info.first_name))
            if chat_info.last_name: name_parts.append(safe_escape(chat_info.last_name))
            if chat_info.username: name_parts.append(f"(@{safe_escape(chat_info.username)})")
            
            if name_parts:
                user_display_name = " ".join(name_parts) + f" [<code>{user_id}</code>]"
        except Exception:
            user_obj_from_db = get_user_from_db_by_username(str(user_id))
            if user_obj_from_db:
                display_name_parts = []
                if user_obj_from_db.first_name: display_name_parts.append(safe_escape(user_obj_from_db.first_name))
                if user_obj_from_db.last_name: display_name_parts.append(safe_escape(user_obj_from_db.last_name))
                if user_obj_from_db.username: display_name_parts.append(f"(@{safe_escape(user_obj_from_db.username)})")
                if display_name_parts:
                    user_display_name = " ".join(display_name_parts) + f" [<code>{user_id}</code>]"

        formatted_added_time = timestamp_str
        try:
            dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp '{timestamp_str}' for sudo user {user_id}")

        response_lines.append(f"• {user_display_name}\n<b>Added:</b> <code>{formatted_added_time}</code>\n")

    message_text = "\n".join(response_lines)
    if len(message_text) > 4000:
        message_text = "\n".join(response_lines[:15])
        message_text += f"\n\n...and {len(sudo_user_tuples) - 15} more (list too long to display fully)."
        logger.info(f"Sudo list too long, truncated for display. Total: {len(sudo_user_tuples)}")

    await update.message.reply_html(message_text, disable_web_page_preview=True)

@check_module_enabled("core")
@custom_handler("listsupport")
async def listsupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listsupport attempt by user {user.id}.")
        return

    support_user_tuples = get_all_support_users_from_db()

    if not support_user_tuples:
        await update.message.reply_text("There are currently no users in the Support team.")
        return

    response_lines = [f"<b>👷‍♂️ Support Users List:</b>\n"]
    
    for user_id, timestamp_str in support_user_tuples:
        user_display_name = f"<code>{user_id}</code>"

        try:
            chat_info = await context.bot.get_chat(user_id)
            name_parts = []
            if chat_info.first_name: name_parts.append(safe_escape(chat_info.first_name))
            if chat_info.last_name: name_parts.append(safe_escape(chat_info.last_name))
            if chat_info.username: name_parts.append(f"(@{safe_escape(chat_info.username)})")
            
            if name_parts:
                user_display_name = " ".join(name_parts) + f" [<code>{user_id}</code>]"
        except Exception:
            user_obj_from_db = get_user_from_db_by_username(str(user_id))
            if user_obj_from_db:
                display_name_parts = []
                if user_obj_from_db.first_name: display_name_parts.append(safe_escape(user_obj_from_db.first_name))
                if user_obj_from_db.last_name: display_name_parts.append(safe_escape(user_obj_from_db.last_name))
                if user_obj_from_db.username: display_name_parts.append(f"(@{safe_escape(user_obj_from_db.username)})")
                if display_name_parts:
                    user_display_name = " ".join(display_name_parts) + f" [<code>{user_id}</code>]"

        formatted_added_time = timestamp_str
        try:
            dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp '{timestamp_str}' for support user {user_id}")

        response_lines.append(f"• {user_display_name}\n<b>Added:</b> <code>{formatted_added_time}</code>\n")

    message_text = "\n".join(response_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

@check_module_enabled("core")
@custom_handler("listwhitelist")
async def listwhitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listwhitelist attempt by user {user.id}.")
        return

    whitelist_user_tuples = get_all_whitelist_users_from_db()

    if not whitelist_user_tuples:
        await update.message.reply_text("There are currently no users in the Whitelist.")
        return

    response_lines = [f"<b>🔰 Whitelist Users List:</b>\n"]
    
    for user_id, timestamp_str in whitelist_user_tuples:
        user_display_name = f"<code>{user_id}</code>"

        try:
            chat_info = await context.bot.get_chat(user_id)
            name_parts = []
            if chat_info.first_name: name_parts.append(safe_escape(chat_info.first_name))
            if chat_info.last_name: name_parts.append(safe_escape(chat_info.last_name))
            if chat_info.username: name_parts.append(f"(@{safe_escape(chat_info.username)})")
            
            if name_parts:
                user_display_name = " ".join(name_parts) + f" [<code>{user_id}</code>]"
        except Exception:
            user_obj_from_db = get_user_from_db_by_username(str(user_id))
            if user_obj_from_db:
                display_name_parts = []
                if user_obj_from_db.first_name: display_name_parts.append(safe_escape(user_obj_from_db.first_name))
                if user_obj_from_db.last_name: display_name_parts.append(safe_escape(user_obj_from_db.last_name))
                if user_obj_from_db.username: display_name_parts.append(f"(@{safe_escape(user_obj_from_db.username)})")
                if display_name_parts:
                    user_display_name = " ".join(display_name_parts) + f" [<code>{user_id}</code>]"

        formatted_added_time = timestamp_str
        try:
            dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp '{timestamp_str}' for support user {user_id}")

        response_lines.append(f"• {user_display_name}\n<b>Added:</b> <code>{formatted_added_time}</code>\n")

    message_text = "\n".join(response_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

@check_module_enabled("core")
@custom_handler("listdevs")
async def listdevs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        return

    dev_user_tuples = get_all_dev_users_from_db()

    if not dev_user_tuples:
        await update.message.reply_text("There are currently no users with Developer role.")
        return

    response_lines = [f"<b>🛃 Developer Users List:</b>\n"]
    
    for user_id, timestamp_str in dev_user_tuples:
        user_display_name = f"<code>{user_id}</code>"

        try:
            chat_info = await context.bot.get_chat(user_id)
            name_parts = []
            if chat_info.first_name: name_parts.append(safe_escape(chat_info.first_name))
            if chat_info.last_name: name_parts.append(safe_escape(chat_info.last_name))
            if chat_info.username: name_parts.append(f"(@{safe_escape(chat_info.username)})")
            
            if name_parts:
                user_display_name = " ".join(name_parts) + f" [<code>{user_id}</code>]"
        except Exception:
            user_obj_from_db = get_user_from_db_by_username(str(user_id))
            if user_obj_from_db:
                display_name_parts = []
                if user_obj_from_db.first_name: display_name_parts.append(safe_escape(user_obj_from_db.first_name))
                if user_obj_from_db.last_name: display_name_parts.append(safe_escape(user_obj_from_db.last_name))
                if user_obj_from_db.username: display_name_parts.append(f"(@{safe_escape(user_obj_from_db.username)})")
                if display_name_parts:
                    user_display_name = " ".join(display_name_parts) + f" [<code>{user_id}</code>]"

        formatted_added_time = timestamp_str
        try:
            dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp '{timestamp_str}' for dev user {user_id}")

        response_lines.append(f"• {user_display_name}\n<b>Added:</b> <code>{formatted_added_time}</code>\n")

    message_text = "\n".join(response_lines)
    await update.message.reply_html(message_text, disable_web_page_preview=True)

@check_module_enabled("core")
@custom_handler("listgroups")
async def list_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listgroups attempt by user {user.id}.")
        return

    bot_chats = get_all_bot_chats_from_db()

    if not bot_chats:
        await update.message.reply_text("The bot is not currently in any known groups.")
        return

    response_lines = [f"<b>📊 List of all known groups; <code>{len(bot_chats)}</code> total:</b>\n\n"]
    
    for chat_id, chat_title, added_at_str in bot_chats:
        display_title = safe_escape(chat_title or "Untitled Group")
        
        try:
            dt_obj = datetime.fromisoformat(added_at_str.replace("Z", "+00:00"))
            formatted_added_time = dt_obj.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            formatted_added_time = added_at_str[:16] if added_at_str else "N/A"

        response_lines.append(
            f"• <b>{display_title}</b> [<code>{chat_id}</code>]\n"
            f"<b>Added:</b> <code>{formatted_added_time}</code>\n\n"
        )

    final_message = ""
    for line in response_lines:
        if len(final_message) + len(line) > 4096:
            await update.message.reply_html(final_message, disable_web_page_preview=True)
            final_message = ""
        final_message += line

    if final_message:
        await update.message.reply_html(final_message, disable_web_page_preview=True)

@check_module_enabled("core")
@custom_handler("delgroup")
async def del_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /delgroup attempt by user {user.id}.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delchat <ID_1> [ID_2] ...")
        return

    deleted_chats = []
    failed_chats = []

    for chat_id_str in context.args:
        try:
            chat_id_to_delete = int(chat_id_str)
            if remove_chat_from_db_by_id(chat_id_to_delete):
                deleted_chats.append(f"<code>{chat_id_to_delete}</code>")
            else:
                failed_chats.append(f"<code>{chat_id_to_delete}</code> (not found)")
        except ValueError:
            failed_chats.append(f"<i>{safe_escape(chat_id_str)}</i> (invalid ID)")

    response_lines = []
    if deleted_chats:
        response_lines.append(f"✅ Successfully removed <code>{len(deleted_chats)}</code> entries from the chat cache:")
        response_lines.append(", ".join(deleted_chats))
    
    if failed_chats:
        if response_lines: response_lines.append("")
        response_lines.append(f"❌ Failed to remove <code>{len(failed_chats)}</code> entries:")
        response_lines.append(", ".join(failed_chats))
    
    if not response_lines:
        await update.message.reply_text("No valid IDs were provided.")
        return

    await update.message.reply_html("\n".join(response_lines))

@check_module_enabled("core")
@custom_handler("cleangroups")
async def clean_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /cleangroups attempt by user {user.id}.")
        return

    status_message = await update.message.reply_html("🧹 Starting group cache cleanup... This may take a while. Please wait.")

    all_chat_ids_from_db = [chat[0] for chat in get_all_bot_chats_from_db()]
    
    if not all_chat_ids_from_db:
        await status_message.edit_text("✅ Chat cache is already empty. Nothing to do.")
        return

    logger.info(f"Starting cleanup for {len(all_chat_ids_from_db)} chats...")
    
    removed_chats_count = 0
    checked_chats_count = 0
    
    chunk_size = 50 
    for i in range(0, len(all_chat_ids_from_db), chunk_size):
        chunk = all_chat_ids_from_db[i:i + chunk_size]
        
        status_text = (
            f"🧹 Checking chats <code>{checked_chats_count+1}-{checked_chats_count+len(chunk)} / {len(all_chat_ids_from_db)}</code>\n"
            f"🗑️ Removed so far: <code>{removed_chats_count}</code>"
        )
        try:
            await status_message.edit_text(status_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.warning(f"Could not edit status message: {e}")

        for chat_id in chunk:
            try:
                await context.bot.get_chat(chat_id)
            except TelegramError as e:
                if "not found" in str(e).lower() or "forbidden" in str(e).lower() or "chat not found" in str(e).lower():
                    logger.info(f"Chat {chat_id} not found or access is forbidden. Removing from cache.")
                    if remove_chat_from_db_by_id(chat_id):
                        removed_chats_count += 1
                else:
                    logger.warning(f"Unexpected API error while checking chat {chat_id}: {e}")
            
            checked_chats_count += 1
            await asyncio.sleep(0.2)

    final_report = (
        f"✅ <b>Cleanup complete!</b>\n\n"
        f"• Checked: <code>{checked_chats_count}</code> chats\n"
        f"• Removed: <code>{removed_chats_count}</code> inactive/invalid entries"
    )
    
    try:
        await status_message.edit_text(final_report, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Could not edit final report message: {e}")

@check_module_enabled("core")
@custom_handler("broadcast")
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not message: return

    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /broadcast attempt by user {user.id}.")
        return

    if not context.args:
        await message.reply_text("Usage: /broadcast <message to send>")
        return

    text_to_broadcast = " ".join(context.args)

    all_chats = get_all_bot_chats_from_db()
    if not all_chats:
        await message.reply_text("I'm not in any chats to broadcast to.")
        return

    status_message = await message.reply_html(
        f"📢 Starting broadcast to <code>{len(all_chats)}</code> chats..."
    )

    sent_count = 0
    failed_count = 0
    
    for chat_id, chat_title, _ in all_chats:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text_to_broadcast)
            sent_count += 1
            logger.info(f"Broadcast sent to: {chat_title} ({chat_id})")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {chat_title} ({chat_id}): {e}")
            if isinstance(e, (telegram.error.Forbidden, telegram.error.BadRequest)):
                if "forbidden" in str(e).lower() or "bot is not a member" in str(e).lower() or "chat not found" in str(e).lower():
                    remove_chat_from_db(chat_id)
        
        await asyncio.sleep(0.2)

    final_report = (
        f" complete!\n\n"
        f"✅ <b>Sent to:</b> <code>{sent_count}</code> chats.\n"
        f"❌ <b>Failed for:</b> <code>{failed_count}</code> chats."
    )
    
    try:
        await status_message.edit_text(
            text=f"📢 Broadcast to <code>{len(all_chats)}</code> chats" + final_report,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Failed to edit final broadcast report: {e}")

@check_module_enabled("core")
@custom_handler(["shell", "sh"])
async def shell_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /shell attempt by user {user.id}.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /shell <command>")
        return

    command = " ".join(context.args)
    status_message = await update.message.reply_html(f"🔩 Executing: <code>{html.escape(command)}</code>")

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)

        result_text = ""
        if stdout:
            result_text += f"<code>{html.escape(stdout.decode('utf-8', errors='ignore'))}</code>\n"
        if stderr:
            result_text += f"<code>{html.escape(stderr.decode('utf-8', errors='ignore'))}</code>\n"
        if not stdout and not stderr:
            result_text = "✅ Command executed with no output."
            
        if len(result_text) > 4096:
            await status_message.edit_text("Output is too long. Sending as a file.")
            with io.BytesIO(str.encode(result_text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", ""))) as f:
                f.name = "shell_output.txt"
                await update.message.reply_document(document=f)
        else:
            await status_message.edit_text(result_text, parse_mode=ParseMode.HTML)

    except asyncio.TimeoutError:
        await status_message.edit_text("<b>Error:</b> Command timed out after 60 seconds.")
    except Exception as e:
        logger.error(f"Error executing shell command '{command}': {e}", exc_info=True)
        await status_message.edit_text(f"<b>Error:</b> {html.escape(str(e))}")

@check_module_enabled("core")
@custom_handler(["execute", "exe"])
async def execute_script_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /execute attempt by user {user.id}.")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /execute <script_path> [args...]")
        return
    
    await shell_command(update, context)

@check_module_enabled("core")
@custom_handler("addsudo")
async def addsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /addsudo attempt by user {user.id}.")
        return

    target_user: User | None = None

    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        target_user = message.reply_to_message.from_user
    elif context.args:
        target_input = context.args[0]
        
        target_user = await resolve_user_with_telethon(context, target_input, update)
        
        if not target_user and target_input.isdigit():
            try:
                target_user = await context.bot.get_chat(int(target_input))
            except:
                logger.warning(f"Could not resolve full profile for ID {target_input} in ADDSUDO. Creating a minimal User object.")
                target_user = User(id=int(target_input), first_name="", is_bot=False)
    else:
        await message.reply_text("Usage: /addsudo <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    user_display = create_user_html_link(target_user)
    if is_privileged_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} [<code>{target_user.id}</code>] already has a privileged role. Use /setrank if want change it.")
        return
    
    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 Sudo can only be granted to users.")
        return

    if is_whitelisted(target_user.id):
        await message.reply_text("This user is on the whitelist and cannot be promoted to Sudo.")
        return

    if target_user.id == OWNER_ID or target_user.id == context.bot.id or target_user.is_bot:
        await message.reply_text("This user cannot be a sudo.")
        return
    
    gban_reason = get_gban_reason(target_user.id)
    blist_reason = get_blacklist_reason(target_user.id)

    if gban_reason:
        error_message = (
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} [<code>{target_user.id}</code>] cannot be promoted to <code>Sudo</code> because they are <b>Globally Bannned</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(gban_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove global ban first using /ungban if you wish to proceed.</i>"
        )
        await message.reply_html(error_message)
        return

    if blist_reason:
        error_message = (
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} [<code>{target_user.id}</code>] cannot be promoted to <code>Sudo</code> because they are on the <b>Blacklist</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(blist_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove the user from the blacklist first using /unblist if you wish to proceed.</i>"
        )
        await message.reply_html(error_message)
        return

    if add_sudo_user(target_user.id, user.id):
        await message.reply_html(f"✅ Done! {user_display} [<code>{target_user.id}</code>] has been granted <b>Sudo</b> powers.")
        
        try:
            await context.bot.send_message(target_user.id, "You have been granted Sudo privileges.")
        except Exception as e:
            logger.warning(f"Failed to send PM to new sudo user {target_user.id}: {e}")

        admin_link = create_user_html_link(user)
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#SUDO</b>\n\n"
                f"<b>User:</b> {user_display} [<code>{target_user.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user.id}</code>]"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #SUDO log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to sudo list. Check logs.")

@check_module_enabled("core")
@custom_handler("delsudo")
async def delsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /delsudo attempt by user {user.id}.")
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
        await message.reply_text("Usage: /delsudo <ID/@username/reply>")
        return
        
    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user..")
        return

    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 Sudo can only be revoked from users.")
        return

    if target_user.id == OWNER_ID:
        await message.reply_text("The Owner's powers cannot be revoked.")
        return
    
    user_display = create_user_html_link(target_user)

    if not is_sudo_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} [<code>{target_user.id}</code>] does not have <b>Sudo</b> powers.")
        return

    if remove_sudo_user(target_user.id):
        await message.reply_html(f"✅ Done! <b>Sudo</b> powers for user {user_display} [<code>{target_user.id}</code>] have been revoked.")
        
        try:
            await context.bot.send_message(target_user.id, "Your sudo privileges have been revoked.")
        except Exception as e:
            logger.warning(f"Failed to send PM to revoked sudo user {target_user.id}: {e}")

        admin_link = create_user_html_link(user)

        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#UNSUDO</b>\n\n"
                f"<b>User:</b> {user_display} [<code>{target_user.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user.id}</code>]"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #UNSUDO log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to remove user from sudo list. Check logs.")

@check_module_enabled("core")
@custom_handler("setrank")
async def setrank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /setrank attempt by user {user.id}.")
        return

    target_user: User | None = None
    args_for_role: list[str] = []

    if message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
        target_user = message.reply_to_message.from_user
        args_for_role = context.args
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
    
    if not target_user or not args_for_role:
        await message.reply_text("Usage: /setrank <ID/@username/reply> [support/sudo/dev]")
        return

    if not is_entity_a_user(target_user):
        await message.reply_text("After all, channels can't have privileged ranks, so why would you want to do that?")
        return

    new_role_shortcut = args_for_role[0].lower()

    role_map = {
        "support": "Support",
        "sudo": "Sudo",
        "dev": "Developer"
    }

    if new_role_shortcut not in role_map:
        await message.reply_text(f"Invalid role '{safe_escape(new_role_shortcut)}'. Please use one of: support, sudo, dev.")
        return

    new_role_full_name = role_map[new_role_shortcut]

    if target_user.id == OWNER_ID:
        await message.reply_text("Owner cannot have his rank changed because he has the ultimate authority.")
        return

    if not is_privileged_user(target_user.id):
        await message.reply_text("This command can only be used on users who already have a role (Support, Sudo, or Developer).")
        return

    if is_dev_user(user.id):
        if user.id == target_user.id:
            await message.reply_text("You cannot change your own rank.")
            return
        if is_dev_user(target_user.id):
            await message.reply_text("As a Developer, you cannot change the rank of other Developers.")
            return
        if new_role_shortcut == "dev":
            await message.reply_text("As a Developer, you cannot promote others to the Developer role.")
            return

    current_role_shortcut = ""
    if is_dev_user(target_user.id): current_role_shortcut = "dev"
    elif is_sudo_user(target_user.id): current_role_shortcut = "sudo"
    elif is_support_user(target_user.id): current_role_shortcut = "support"
    
    current_role_full_name = role_map.get(current_role_shortcut, "Unknown")

    if new_role_shortcut == current_role_shortcut:
        await message.reply_text(f"User is already a {new_role_full_name}. No changes made.")
        return

    remove_support_user(target_user.id)
    remove_sudo_user(target_user.id)
    remove_dev_user(target_user.id)

    success = False
    if new_role_shortcut == "support":
        success = add_support_user(target_user.id, user.id)
    elif new_role_shortcut == "sudo":
        success = add_sudo_user(target_user.id, user.id)
    elif new_role_shortcut == "dev":
        success = add_dev_user(target_user.id, user.id)

    if success:
        user_display = create_user_html_link(target_user)
        admin_link = create_user_html_link(user)
        
        feedback_message = f"✅ Done! {user_display} [<code>{target_user.id}</code>] rank has been changed from <b>{current_role_full_name}</b> to <b>{new_role_full_name}</b>."
        await message.reply_html(feedback_message)

        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        log_message = (f"<b>#ROLECHANGED</b>\n\n"
                       f"<b>User:</b> {user_display} [<code>{target_user.id}</code>]\n"
                       f"<b>Old Role:</b> <code>{current_role_full_name}</code>\n"
                       f"<b>New Role:</b> <code>{new_role_full_name}</code>\n"
                       f"<b>Date:</b> <code>{current_time}</code>\n"
                       f"<b>Admin:</b> {admin_link} [<code>{user.id}</code>]"
        )
        await send_operational_log(context, log_message)
    else:
        await message.reply_text("An error occurred while changing the rank. Check logs.")

@check_module_enabled("core")
@custom_handler("addsupport")
async def addsupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /addsupport attempt by user {user.id}.")
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
        await message.reply_text("Usage: /addsupport <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    user_display = create_user_html_link(target_user)
    if is_privileged_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} [<code>{target_user.id}</code>] already has a privileged role. Use /setrank if want change it.")
        return
    
    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 This role can only be granted to users.")
        return

    if is_whitelisted(target_user.id):
        await message.reply_text("This user is on the whitelist and cannot be promoted to Support.")
        return

    if target_user.id == OWNER_ID or target_user.id == context.bot.id or target_user.is_bot:
        await message.reply_text("This user cannot be a Support.")
        return
    
    gban_reason = get_gban_reason(target_user.id)
    if gban_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} [<code>{target_user.id}</code>] cannot be promoted to <code>Support</code> because they are <b>Globally Bannned</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(gban_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove global ban first using /ungban if you wish to proceed.</i>"
        )
        return
    blist_reason = get_blacklist_reason(target_user.id)
    if blist_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} [<code>{target_user.id}</code>] cannot be promoted to <code>Sudo</code> because they are on the <b>Blacklist</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(blist_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove the user from the blacklist first using /unblist if you wish to proceed.</i>"
        )
        return

    if add_support_user(target_user.id, user.id):
        await message.reply_html(f"✅ Done! {user_display} [<code>{target_user.id}</code>] has been granted <b>Support</b> powers.")
        
        try:
            await context.bot.send_message(target_user.id, "You have been added to the Support team.")
        except Exception as e:
            logger.warning(f"Failed to send PM to new Support user {target_user.id}: {e}")

        admin_link = create_user_html_link(user)
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#SUPPORT</b>\n\n"
                f"<b>User:</b> {user_display} [<code>{target_user.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user.id}</code>]"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #SUPPORT log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to Support list. Check logs.")

@check_module_enabled("core")
@custom_handler("delsupport")
async def delsupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /delsupport attempt by user {user.id}.")
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
        await message.reply_text("Usage: /delsupport <ID/@username/reply>")
        return
        
    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 This role can only be revoked from users.")
        return
    
    user_display = create_user_html_link(target_user)

    if not is_support_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} [<code>{target_user.id}</code>] is not in Support.")
        return

    if remove_support_user(target_user.id):
        await message.reply_html(f"✅ Done! <b>Support</b> role for user {user_display} [<code>{target_user.id}</code>] has been revoked.")
        
        try:
            await context.bot.send_message(target_user.id, "You have been removed from the Support team.")
        except Exception as e:
            logger.warning(f"Failed to send PM to revoked Support user {target_user.id}: {e}")

        admin_link = create_user_html_link(user)

        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#UNSUPPORT</b>\n\n"
                f"<b>User:</b> {user_display} [<code>{target_user.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user.id}</code>]"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #UNSUPPORT log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to remove user from Support list. Check logs.")

@check_module_enabled("core")
@custom_handler("adddev")
async def adddev_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /adddev attempt by user {user.id}.")
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
        await message.reply_text("Usage: /adddev <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    user_display = create_user_html_link(target_user)
    if is_privileged_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} [<code>{target_user.id}</code>] already has a privileged role. Use /setrank if want change it.")
        return
    
    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 This role can only be granted to users.")
        return

    if is_whitelisted(target_user.id):
        await message.reply_text("This user is on the whitelist and cannot be promoted to Developer.")
        return

    if target_user.id == OWNER_ID or target_user.id == context.bot.id or target_user.is_bot:
        await message.reply_text("This user cannot be a Developer.")
        return
    
    gban_reason = get_gban_reason(target_user.id)
    if gban_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} [<code>{target_user.id}</code>] cannot be promoted to <code>Developer</code> because they are <b>Globally Bannned</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(gban_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove global ban first using /ungban if you wish to proceed.</i>"
        )
        return
    blist_reason = get_blacklist_reason(target_user.id)
    if blist_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} [<code>{target_user.id}</code>] cannot be promoted to <code>Developer</code> because they are on the <b>Blacklist</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(blist_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove the user from the blacklist first using /unblist if you wish to proceed.</i>"
        )
        return

    if add_dev_user(target_user.id, user.id):
        await message.reply_html(f"✅ Done! {user_display} [<code>{target_user.id}</code>] has been granted <b>Developer</b> powers.")
        
        try:
            await context.bot.send_message(target_user.id, "You have been promoted to Developer by the Bot Owner.")
        except Exception as e:
            logger.warning(f"Failed to send PM to new Dev user {target_user.id}: {e}")
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#DEVELOPER</b>\n\n"
                f"<b>User:</b> {user_display} [<code>{target_user.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #DEVELOPER log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to Developer list. Check logs.")

@check_module_enabled("core")
@custom_handler("deldev")
async def deldev_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message: return
    
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /deldev attempt by user {user.id}.")
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
        await message.reply_text("Usage: /deldev <ID/@username/reply>")
        return
        
    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 This role can only be revoked from users.")
        return
    
    user_display = create_user_html_link(target_user)

    if not is_dev_user(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} [<code>{target_user.id}</code>] is not a Developer.")
        return

    if remove_dev_user(target_user.id):
        await message.reply_html(f"✅ Done! <b>Developer</b> role for user {user_display} [<code>{target_user.id}</code>] has been revoked.")
        
        try:
            await context.bot.send_message(target_user.id, "Your Developer role has been revoked by the Bot Owner.")
        except Exception as e:
            logger.warning(f"Failed to send PM to revoked Dev user {target_user.id}: {e}")

        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log_message = (
                f"<b>#UNDEVELOPER</b>\n\n"
                f"<b>User:</b> {user_display} [<code>{target_user.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #UNDEVELOPER log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to remove user from Developer list. Check logs.")

@check_module_enabled("core")
@custom_handler(["whitelist", "wlist"])
async def whitelist_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /whitelist attempt by user {user.id}.")
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
        await message.reply_text("Usage: /addsupport <ID/@username/reply>")
        return

    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return
        
    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 Added to Whitelist can only be users.")
        return

    user_display = create_user_html_link(target_user)

    if is_privileged_user(target_user.id):
        await message.reply_html(f"User {user_display} already has a privileged or protected role and cannot be whitelisted.")
        return

    gban_reason = get_gban_reason(target_user.id)
    if gban_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} [<code>{target_user.id}</code>] cannot be on <code>Whitelist</code> because they are <b>Globally Bannned</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(gban_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove global ban first using /ungban if you wish to proceed.</i>"
        )
        return
    blist_reason = get_blacklist_reason(target_user.id)
    if blist_reason:
        await message.reply_html(
            f"❌ <b>Promotion Failed!</b>\n\n"
            f"User {user_display} [<code>{target_user.id}</code>] cannot be on <code>Whitelist</code> because they are on the <b>Blacklist</b>.\n\n"
            f"<b>Reason:</b> {safe_escape(blist_reason)}\n\n"
            f"<i>For security reasons, this action has been blocked. "
            f"Please remove the user from the blacklist first using /unblist if you wish to proceed.</i>"
        )
        return

    if is_whitelisted(target_user.id):
        await message.reply_html(f"ℹ️ User {user_display} [<code>{target_user.id}</code>] is already <b>whitelisted</b>.")
        return

    prepare_message = f"Keep this user safe!"
    await message.reply_html(prepare_message)
    await asyncio.sleep(1.0)

    if add_to_whitelist(target_user.id, user.id):
        await message.reply_html(f"✅ Done! {user_display} [<code>{target_user.id}</code>] has been <b>whitelisted</b>.")
        
        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            admin_link = create_user_html_link(user)

            log_message = (
                f"<b>#WHITELISTED</b>\n\n"
                f"<b>User:</b> {user_display} [<code>{target_user.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user.id}</code>]"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #WHITELISTED log: {e}", exc_info=True)
    else:
        await message.reply_text("Failed to add user to whitelist (they might be already on it).")

@check_module_enabled("core")
@custom_handler(["whitelist", "wlist"])
async def unwhitelist_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /unwhitelist attempt by user {user.id}.")
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
        await message.reply_text("Usage: /unwhitelist <ID/@username/reply>")
        return
        
    if not target_user:
        await message.reply_text("Skrrrt... I can't find the user.")
        return

    if not is_entity_a_user(target_user):
        await message.reply_text("🧐 Deleted from Whitelist can only be users.")
        return

    if not is_whitelisted(target_user.id):
        await update.message.reply_html(f"User {target_user.mention_html()} is not <b>whitelisted</b>.")
        return

    prepare_message = f"Let him be like everyone else!"
    await message.reply_html(prepare_message)
    await asyncio.sleep(1.0)

    user_display = create_user_html_link(target_user)
    if remove_from_whitelist(target_user.id):
        await update.message.reply_html(f"✅ Done! {user_display} [<code>{target_user.id}</code>] has been <b>unwhitelisted</b>.")

        try:
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            admin_link = create_user_html_link(user)

            log_message = (
                f"<b>#UNWHITELISTED</b>\n\n"
                f"<b>User:</b> {user_display} [<code>{target_user.id}</code>]\n"
                f"<b>Date:</b> <code>{current_time}</code>\n"
                f"<b>Admin:</b> {admin_link} [<code>{user.id}</code>]"
            )
            await send_operational_log(context, log_message)
        except Exception as e:
            logger.error(f"Error sending #UNWHITELISTED log: {e}", exc_info=True)
    else:
        await update.message.reply_text("Failed to remove user from the whitelist.")

@check_module_enabled("core")
@custom_handler("rmcacheduser")
async def remove_cached_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /rmcacheduser attempt by user {user.id}.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /rmcacheduser <User ID>")
        return

    try:
        user_id_to_delete = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid user ID.")
        return

    if delete_user_from_db(user_id_to_delete):
        await update.message.reply_html(
            f"✅ User <b>{user_id_to_delete}</b> has been cleared from the local database cache.\n"
            "The next command used on this user will fetch fresh data from Telegram."
        )
    else:
        await update.message.reply_html(
            f"ℹ️ User <b>{user_id_to_delete}</b> was not found in the local database cache, so no action was taken."
        )


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler(["permissions", "perms"], permissions_command))
    application.add_handler(CommandHandler("echo", echo))
    application.add_handler(CommandHandler("leave", leave_chat))
    application.add_handler(CommandHandler("speedtest", speedtest_command))
    application.add_handler(CommandHandler("listsudo", list_sudo_users_command))
    application.add_handler(CommandHandler("listgroups", list_groups_command))
    application.add_handler(CommandHandler("delgroup", del_groups_command))
    application.add_handler(CommandHandler("cleangroups", clean_groups_command))
    application.add_handler(CommandHandler("addsudo", addsudo_command))
    application.add_handler(CommandHandler("delsudo", delsudo_command))
    application.add_handler(CommandHandler("adddev", adddev_command))
    application.add_handler(CommandHandler("deldev", deldev_command))
    application.add_handler(CommandHandler("listdevs", listdevs_command)) 
    application.add_handler(CommandHandler(["whitelist", "wlist"], whitelist_user_command))
    application.add_handler(CommandHandler(["unwhitelist", "unwlist"], unwhitelist_user_command))
    application.add_handler(CommandHandler("addsupport", addsupport_command))
    application.add_handler(CommandHandler("delsupport", delsupport_command))
    application.add_handler(CommandHandler("setrank", setrank_command))
    application.add_handler(CommandHandler("listsupport", listsupport_command))
    application.add_handler(CommandHandler("listwhitelist", listwhitelist_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler(["shell", "sh"], shell_command))
    application.add_handler(CommandHandler(["execute", "exe"], execute_script_command))
    application.add_handler(CommandHandler("rmcacheduser", remove_cached_user_command))
