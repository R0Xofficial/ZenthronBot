import logging
import random

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from modules.utils import (
    get_themed_gif, check_target_protection, check_username_protection
)
from .constants import (
    KILL_TEXTS, SLAP_TEXTS, PUNCH_TEXTS, PAT_TEXTS, BONK_TEXTS,
    CANT_TARGET_OWNER_TEXTS, CANT_TARGET_SELF_TEXTS
)

logger = logging.getLogger(__name__)


# --- FUN COMMANDS HELPER ---
async def _handle_action_command(update, context, texts, gifs, name, req_target=True, msg=""):
    target_mention = None
    if req_target:
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
            if await check_target_protection(target.id, context):
                await update.message.reply_html(random.choice(CANT_TARGET_OWNER_TEXTS if target.id == config.OWNER_ID else CANT_TARGET_SELF_TEXTS)); return
            target_mention = target.mention_html()
        elif context.args and context.args[0].startswith('@'):
            target_mention = context.args[0]
            is_prot, is_owner = await check_username_protection(target_mention, context)
            if is_prot: await update.message.reply_html(random.choice(CANT_TARGET_OWNER_TEXTS if is_owner else CANT_TARGET_SELF_TEXTS)); return
        else: await update.message.reply_text(msg); return
    
    text = random.choice(texts).format(target=target_mention or "someone")
    gif_url = await get_themed_gif(context, gifs)
    try:
        if gif_url: await update.message.reply_animation(gif_url, caption=text, parse_mode=ParseMode.HTML)
        else: await update.message.reply_html(text)
    except Exception as e: logger.error(f"Error sending {name} action: {e}"); await update.message.reply_html(text)

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, KILL_TEXTS, ["gun", "gun shoting", "anime gun"], "kill", True, "Who to 'kill'?")
async def punch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, PUNCH_TEXTS, ["punch", "hit", "anime punch"], "punch", True, "Who to 'punch'?")
async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, SLAP_TEXTS, ["huge slap", "smack", "anime slap"], "slap", True, "Who to slap?")
async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, PAT_TEXTS, ["pat", "pat anime", "anime pat"], "pat", True, "Who to pat?")
async def bonk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, BONK_TEXTS, ["bonk", "anime bonk"], "bonk", True, "Who to bonk?")

async def damnbroski(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    special_message = "💀Bro..."
    
    await _handle_action_command(
        update,
        context,
        [special_message],
        ["caught in 4k", "caught in 4k meme"],
        "damnbroski",
        False,
        ""
    )


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("kill", kill))
    application.add_handler(CommandHandler("punch", punch))
    application.add_handler(CommandHandler("slap", slap))
    application.add_handler(CommandHandler("pat", pat))
    application.add_handler(CommandHandler("bonk", bonk))
    application.add_handler(CommandHandler("touch", damnbroski))
