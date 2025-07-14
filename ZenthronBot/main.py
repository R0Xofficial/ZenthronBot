import asyncio
import logging
import os
import importlib
import traceback
from telegram import Update, constants
from telegram.constants import ParseMode, UpdateType
from telegram.ext import Application, ApplicationBuilder, JobQueue, ContextTypes, MessageHandler, filters, ApplicationHandlerStop, ChatMemberHandler, CommandHandler
from telegram.request import HTTPXRequest
from telethon import TelegramClient

from .config import SESSION_NAME, API_ID, API_HASH, LOG_CHAT_ID, OWNER_ID, BOT_TOKEN
from .core.database import init_db, disable_module, enable_module, get_disabled_modules
from .core.utils import is_owner_or_dev, safe_escape
from .core.custom_handlers import CustomPrefixHandler
from .core.debugging_utils import DebugApplication

from .modules.core import error_handler
from .modules.mutes import handle_bot_permission_changes
from .modules.bans import handle_bot_banned
from .modules.blacklists import check_blacklist_handler
from .modules.userlogger import log_user_from_interaction
from .modules.globalbans import check_gban_on_message, check_gban_on_entry
from .modules.afk import check_afk_return, afk_reply_handler, afk_brb_handler
from .modules.notes import handle_note_trigger
from .modules.welcomes import handle_new_group_members, handle_left_group_member
from .modules.joinfilters import check_new_member
from .modules.filters import check_message_for_filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.vendor.ptb_urllib3.urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger('telethon').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def send_startup_log(context: ContextTypes.DEFAULT_TYPE) -> None:
    startup_message_text = "<i>Bot Started...</i>"
    target_id_for_log = LOG_CHAT_ID or OWNER_ID
    
    if target_id_for_log:
        try:
            await context.bot.send_message(
                chat_id=target_id_for_log,
                text=startup_message_text,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Sent startup notification to {target_id_for_log}.")
        except Exception as e:
            logger.error(f"Failed to send startup message to {target_id_for_log}: {e}")
    else:
        logger.warning("No target (LOG_CHAT_ID or OWNER_ID) to send startup message.")

async def ignore_edited_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Ignoring edited command: {update.edited_message.text}")
    raise ApplicationHandlerStop

def discover_and_register_handlers(application: Application):
    manageable_commands = set()
    base_path = os.path.dirname(os.path.abspath(__file__))
    modules_dir = os.path.join(base_path, "modules")

    for filename in sorted(os.listdir(modules_dir)):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"ZenthronBot.modules.{module_name}")
                
                if hasattr(module, "load_handlers"):
                    module.load_handlers(application)
                    logger.info(f"Successfully loaded module: {module_name}")
                
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and hasattr(attr, '_is_manageable'):
                        command_name = getattr(attr, '_command_name')
                        manageable_commands.add(command_name)
                        
            except Exception as e:
                logger.error(f"Error processing module {module_name}: {e}")
                traceback.print_exc()
    
    application.bot_data["manageable_commands"] = manageable_commands
    if manageable_commands:
        logger.info(f"Registered manageable commands: {sorted(list(manageable_commands))}")
    else:
        logger.info("No manageable commands found.")

def _get_available_modules():
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        modules_dir = os.path.join(base_path, "modules")
        
        all_files = os.listdir(modules_dir)
        
        modules = [
            f[:-3] for f in all_files 
            if f.endswith('.py') and not f.startswith('_')
        ]
        return sorted(modules)
    except Exception as e:
        logger.error(f"Could not scan for available modules: {e}")
        return []

async def disable_module_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /disablemodule attempt by user {user.id}.")
        return

    available_modules = _get_available_modules()
    if not context.args or context.args[0] not in available_modules:
        await update.message.reply_html(
            f"<b>Usage:</b> /disablemodule &lt;module name&gt;\n"
            f"<b>Available:</b> <code>{', '.join(available_modules)}</code>"
        )
        return

    module_name = context.args[0]
    if disable_module(module_name):
        await update.message.reply_text(f"✅ Module '<code>{safe_escape(module_name)}</code>' has been disabled.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"Module '<code>{safe_escape(module_name)}</code>' was already disabled or an error occurred.", parse_mode=ParseMode.HTML)

async def enable_module_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    if user.id != OWNER_ID:
        logger.warning(f"Unauthorized /enablemodule attempt by user {user.id}.")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /enablemodule <module name>")
        return
        
    module_name = context.args[0]
    if enable_module(module_name):
        await update.message.reply_text(f"✅ Module '<code>{safe_escape(module_name)}</code>' has been enabled.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"Module '<code>{safe_escape(module_name)}</code>' was already enabled or an error occurred.", parse_mode=ParseMode.HTML)

async def list_modules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    if not is_owner_or_dev(user.id):
        logger.warning(f"Unauthorized /listmodules attempt by user {user.id}.")
        return
        
    disabled_modules = get_disabled_modules()
    available_modules = _get_available_modules()
    
    message = "<b>Module Status:</b>\n\n"
    for module in available_modules:
        status = "🔴 Disabled" if module in disabled_modules else "🟢 Enabled"
        message += f"• <code>{module}</code>: {status}\n"
        
    await update.message.reply_html(message)

async def main() -> None:
    init_db()

    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as telethon_client:
        logger.info("Telethon client started.")

        custom_request_settings = HTTPXRequest(connect_timeout=20.0, read_timeout=80.0, write_timeout=80.0, pool_timeout=20.0)
        
        application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .request(custom_request_settings)
            .job_queue(JobQueue())
            .build()
        )

        # --- GLOBAL LAYER: TRACEBACKS - MODULE LOADER ---
        application.add_error_handler(error_handler)
        discover_and_register_handlers(application)

        # --- LAYER 1: TOP PRIORITY - SECURITY AND IGNORANCE ---
        application.add_handler(ChatMemberHandler(handle_bot_permission_changes, ChatMemberHandler.MY_CHAT_MEMBER), group=-100)
        application.add_handler(ChatMemberHandler(handle_bot_banned, ChatMemberHandler.MY_CHAT_MEMBER), group=-100)
        application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.COMMAND, ignore_edited_commands), group=-50)

        # --- LAYER 2: USER FILTERING - BLACKLISTS - GBANS - JOINFILTER ---
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, check_gban_on_entry), group=-20)
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, check_new_member), group=-15)
        application.add_handler(MessageHandler(filters.COMMAND, check_blacklist_handler), group=-10)
        application.add_handler(MessageHandler(filters.TEXT | filters.COMMAND | filters.Sticker.ALL | filters.PHOTO | filters.VIDEO | filters.VOICE | filters.ANIMATION & filters.ChatType.GROUPS, check_gban_on_message), group=-10)

        # --- LAYER 3: PASSIVE MECHANISMS - AFK ---
        application.add_handler(MessageHandler(filters.Regex(r'^(brb|BRB|Brb|bRB|brB|BRb|bRb)'), afk_brb_handler), group=-6)
        application.add_handler(MessageHandler(filters.TEXT | filters.COMMAND | filters.Sticker.ALL | filters.PHOTO | filters.VIDEO | filters.VOICE | filters.ANIMATION, check_afk_return), group=-5)
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & (filters.REPLY | filters.Entity(constants.MessageEntityType.MENTION) | filters.Entity(constants.MessageEntityType.TEXT_MENTION)), afk_reply_handler), group=-4)

        # --- LAYER 4: MAIN LOGIC - COMMANDS AND INTERACTIONS ---
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_note_trigger), group=0)
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & filters.ChatType.GROUPS, check_message_for_filters), group=3)

        # --- LAYER 5: GROUP MEMBERS SERVICING ---
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_group_members), group=5)
        application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_group_member), group=5)

        # --- LAYER 6: LOWEST PRIORITY - PASSIVE LOGIN ---
        application.add_handler(MessageHandler(filters.ALL & (~filters.UpdateType.EDITED_MESSAGE), log_user_from_interaction), group=10)

        # --- LAYER 7: COMMANDS - HANDLERS ---
        prefixes = ['/', '!']
        application.add_handler(CustomPrefixHandler("disablemodule", disable_module_command, custom_prefixes=prefixes))
        application.add_handler(CustomPrefixHandler("enablemodule", enable_module_command, custom_prefixes=prefixes))
        application.add_handler(CustomPrefixHandler("listmodules", list_modules_command, custom_prefixes=prefixes))

        application.bot_data["telethon_client"] = telethon_client
        logger.info("Telethon client has been injected into bot_data.")

        if application.job_queue:
            application.job_queue.run_once(send_startup_log, when=1)
            logger.info("Startup message job scheduled to run in 1 second.")
        else:
            logger.warning("JobQueue not available, cannot schedule startup message.")

        logger.info(f"Bot starting polling... Owner ID: {OWNER_ID}")
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await telethon_client.run_until_disconnected()

        await application.updater.stop()
        await application.stop()
        logger.info("Bot shutdown process completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.critical(f"Bot crashed unexpectedly at top level: {e}", exc_info=True)
        exit(1)
