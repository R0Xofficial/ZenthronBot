import asyncio
import logging
import os
import importlib
import sys
import traceback
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, JobQueue
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
