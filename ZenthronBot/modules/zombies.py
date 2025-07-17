import asyncio
import logging
from telegram import Update
from telegram.constants import ChatType, ChatMemberStatus, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from telethon import TelegramClient

from ..core.utils import _can_user_perform_action, send_safe_reply, safe_escape
from ..core.decorators import check_module_enabled
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- ZOMBIES COMMAND FUNCTIONS ---
@check_module_enabled("zombies")
async def _find_and_process_zombies(update: Update, context: ContextTypes.DEFAULT_TYPE, dry_run: bool) -> None:
    chat = update.effective_chat
    message = update.message
    telethon_client: TelegramClient = context.bot_data['telethon_client']

    action_text = "Scanning for" if dry_run else "Cleaning"
    status_message = await message.reply_html(f"🔥 <b>{action_text} deleted accounts...</b> This might take a while for large groups.")

    zombie_count = 0
    kicked_count = 0
    failed_count = 0
    
    try:
        async for member in telethon_client.iter_participants(chat.id):
            if member.deleted:
                zombie_count += 1
                
                if not dry_run:
                    try:
                        await context.bot.ban_chat_member(chat.id, member.id)
                        await context.bot.unban_chat_member(chat.id, member.id)
                        kicked_count += 1
                    except Exception as e:
                        failed_count += 1
                    
                    await asyncio.sleep(0.1)

    except Exception as e:
        await status_message.edit_text(f"An error occurred while scanning members: {safe_escape(str(e))}")
        return

    if not dry_run and kicked_count > 0:
        await asyncio.sleep(1)

    if dry_run:
        await status_message.edit_text(
            f"✅ <b>Scan complete!</b> Found <code>{zombie_count}</code> deleted accounts in this chat.\n",
            parse_mode=ParseMode.HTML
        )
    else:
        report = [f"✅ <b>Cleanup complete!</b>"]
        report.append(f"<b>• Found:</b> <code>{zombie_count}</code> deleted accounts.")
        report.append(f"<b>• Successfully kicked:</b> <code>{kicked_count}</code>.")
        if failed_count > 0:
            report.append(f"<b>• Failed to kick:</b> <code>{failed_count}</code> (likely because they are admins).")
        
        await status_message.edit_text("\n".join(report), parse_mode=ParseMode.HTML)

@check_module_enabled("zombies")
@custom_handler("zombies")
async def zombies_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        await send_safe_reply(update, context, text="Huh? You can't scan and delete zombies in private chat...")
        return

    if not await _can_user_perform_action(update, context, 'can_restrict_members', "Why should I listen to a person with no privileges for this? You need 'can_restrict_members' permission.", allow_bot_privileged_override=True):
        return

    if 'telethon_client' not in context.bot_data:
        await update.message.reply_text("Error: This feature requires the Telethon client, which is not available.")
        return

    chat = update.effective_chat
    try:
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            await update.message.reply_text("Error: I can't clean zombies here because I'm not an administrator.")
            return
        if not bot_member.can_restrict_members:
            await update.message.reply_text("Error: I can't clean zombies here because I don't have the 'can_restrict_members' permission.")
            return
    except Exception as e:
        await update.message.reply_text(f"Skrrrt... I couldn't verify my own permissions: {e}")
        return
        
    if context.args and context.args[0].lower() == 'clean':
        await _find_and_process_zombies(update, context, dry_run=False)
    else:
        await _find_and_process_zombies(update, context, dry_run=True)


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("zombies", zombies_command))
