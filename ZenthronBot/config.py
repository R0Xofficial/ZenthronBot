import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
logger = logging.getLogger(__name__)

try:
    OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID"))
    logger.info(f"Owner ID loaded: {OWNER_ID}")
except (ValueError, TypeError):
    logger.critical("CRITICAL: Invalid or missing TELEGRAM_OWNER_ID.")
    exit(1)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("CRITICAL: TELEGRAM_BOT_TOKEN not set!")
    exit(1)

try:
    API_ID = int(os.getenv("TELEGRAM_API_ID"))
    logger.info("API ID loaded.")
except (ValueError, TypeError):
    logger.critical("CRITICAL: Invalid or missing TELEGRAM_API_ID.")
    exit(1)

API_HASH = os.getenv("TELEGRAM_API_HASH")
if not API_HASH:
    logger.critical("CRITICAL: TELEGRAM_API_HASH not set!")
    exit(1)

APPEAL_CHAT_USERNAME = os.getenv("APPEAL_CHAT_USERNAME")
if not APPEAL_CHAT_USERNAME:
    logger.critical("CRITICAL: APPEAL_CHAT_USERNAME not set!")
    exit(1)
else:
    logger.info(f"Appeal chat loaded: {APPEAL_CHAT_USERNAME}")
    
try:
    APPEAL_CHAT_ID = int(os.getenv("APPEAL_CHAT_ID"))
    logger.info(f"Appeal Chat ID loaded: {APPEAL_CHAT_ID}")
except (ValueError, TypeError):
    logger.critical("CRITICAL: Invalid or missing APPEAL_CHAT_ID. It must be a numeric chat ID.")
    exit(1)

TENOR_API_KEY = os.getenv("TENOR_API_KEY")
if TENOR_API_KEY:
    logger.info("Tenor API Key loaded.")
else:
    logger.warning("WARNING: TENOR_API_KEY not set. Themed GIFs will be disabled.")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    logger.info("Gemini API Key loaded.")
else:
    logger.warning("WARNING: GEMINI_API_KEY not set. AI features will be disabled.")

LOG_CHAT_ID = None
log_chat_id_str = os.getenv("LOG_CHAT_ID")
if log_chat_id_str:
    try:
        LOG_CHAT_ID = int(log_chat_id_str)
        logger.info(f"Log Chat ID loaded: {LOG_CHAT_ID}")
    except ValueError:
        logger.error(f"Invalid LOG_CHAT_ID: '{log_chat_id_str}'. Falling back.")
else:
    logger.info("LOG_CHAT_ID not set. Some logs will be sent to OWNER_ID if available.")

ADMIN_LOG_CHAT_ID = None
admin_log_chat_id_str = os.getenv("ADMIN_LOG_CHAT_ID")
if admin_log_chat_id_str:
    try:
        ADMIN_LOG_CHAT_ID = int(admin_log_chat_id_str)
        logger.info(f"Admin Log Chat ID loaded: {ADMIN_LOG_CHAT_ID}")
    except ValueError:
        logger.error(f"Invalid ADMIN_LOG_CHAT_ID: '{admin_log_chat_id_str}'. Falling back.")
else:
    logger.info("ADMIN_LOG_CHAT_ID not set. Critical logs will be sent to OWNER_ID.")
    
LOG_CHAT_USERNAME = os.getenv("LOG_CHAT_USERNAME")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "zenthron_data.db")
SESSION_NAME = "zenthron_user_session"

BOT_START_TIME = datetime.now()
MAX_WARNS = 3
PUBLIC_AI_ENABLED = False
