import asyncio
import logging
import os
import importlib
import sys
import traceback
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, ApplicationBuilder, JobQueue, ContextTypes
from telethon import TelegramClient

import config
from modules.database import init_db

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

def load_modules(application: Application) -> None:
    modules_dir = "modules"
    for filename in os.listdir(modules_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"{modules_dir}.{module_name}")
                if hasattr(module, "load_handlers"):
                    module.load_handlers(application)
                    logger.info(f"Successfully loaded module: {module_name}")
                else:
                    logger.warning(f"Module {module_name} does not have a load_handlers function.")
            except Exception as e:
                logger.error(f"Failed to load module {module_name}: {e}")
                traceback.print_exc()

async def main() -> None:
    init_db()

    async with TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH) as telethon_client:
        logger.info("Telethon client started.")

        application = (
            ApplicationBuilder()
            .token(config.BOT_TOKEN)
            .job_queue(JobQueue())
            .build()
        )

        application.bot_data["telethon_client"] = telethon_client
        logger.info("Telethon client has been injected into bot_data.")

        load_modules(application)

        if application.job_queue:
            application.job_queue.run_once(send_startup_log, when=1)
            logger.info("Startup message job scheduled to run in 1 second.")
        else:
            logger.warning("JobQueue not available, cannot schedule startup message.")

        logger.info(f"Bot starting polling... Owner ID: {config.OWNER_ID}")
        
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
