import logging
import random
import cowsay
from pyfiglet import figlet_format
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..config import OWNER_ID
from ..core.utils import get_themed_gif, check_target_protection, check_username_protection, send_safe_reply, safe_escape
from ..core.constants import KILL_TEXTS, SLAP_TEXTS, PUNCH_TEXTS, PAT_TEXTS, BONK_TEXTS, CANT_TARGET_OWNER_TEXTS, CANT_TARGET_SELF_TEXTS
from ..core.decorators import check_module_enabled, command_control
from ..core.custom_handlers import CustomPrefixHandler

logger = logging.getLogger(__name__)


# --- FUN COMMANDS HELPER ---
@check_module_enabled("fun")
@command_control("fun")
async def _handle_action_command(update, context, texts, gifs, name, req_target=True, msg=""):
    target_mention = None
    if req_target:
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
            if await check_target_protection(target.id, context):
                await update.message.reply_html(random.choice(CANT_TARGET_OWNER_TEXTS if target.id == OWNER_ID else CANT_TARGET_SELF_TEXTS)); return
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

@check_module_enabled("fun")
@command_control("fun")
async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, KILL_TEXTS, ["gun", "gun shoting", "anime gun"], "kill", True, "Who to 'kill'?")

@check_module_enabled("fun")
@command_control("fun")
async def punch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, PUNCH_TEXTS, ["punch", "hit", "anime punch"], "punch", True, "Who to 'punch'?")

@check_module_enabled("fun")
@command_control("fun")
async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, SLAP_TEXTS, ["huge slap", "smack", "anime slap"], "slap", True, "Who to slap?")

@check_module_enabled("fun")
@command_control("fun")
async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, PAT_TEXTS, ["pat", "pat anime", "anime pat"], "pat", True, "Who to pat?")

@check_module_enabled("fun")
@command_control("fun")
async def bonk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, BONK_TEXTS, ["bonk", "anime bonk"], "bonk", True, "Who to bonk?")

@check_module_enabled("fun")
@command_control("fun")
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

@check_module_enabled("fun")
@command_control("fun")
async def cowsay_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        text_to_say = "Mooooo!"
    else:
        text_to_say = " ".join(context.args)
    
    if len(text_to_say) > 100:
        text_to_say = text_to_say[:100] + "..."

    cow_output = cowsay.get_output_string('cow', text_to_say)
    
    await send_safe_reply(
        update, 
        context, 
        text=f"<code>{safe_escape(cow_output)}</code>", 
        parse_mode=ParseMode.HTML
    )

@check_module_enabled("fun")
@command_control("fun")
async def ascii_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await send_safe_reply(update, context, text="Usage: /ascii <your text>")
        return

    text_to_convert = " ".join(context.args)
    
    if len(text_to_convert) > 20:
        await send_safe_reply(update, context, text="Text is too long! Please keep it under 20 characters.")
        return

    try:
        ascii_art = figlet_format(text_to_convert, font='standard')
        formatted_message = f"<code>{safe_escape(ascii_art)}</code>"
        await send_safe_reply(update, context, text=formatted_message, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Error generating ASCII art: {e}")
        await send_safe_reply(update, context, text="Sorry, an error occurred while generating the art.")

SKULL_ASCII = """
💀
<code>
⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀
⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀
⡀⡀⡀⡀⡀⡀⢀⣀⣤⣶⣶⣶⣶⣶⣶⣶⣶⣦⣄⡀⡀⡀⡀⡀⡀⡀
⡀⡀⡀⢀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⡀⡀⡀⡀⡀
⡀⡀⢀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⡀⡀⡀
⡀⡀⢸⣿⣿⣿⣿⣿⣿⣿⣿⡿⢛⣭⣭⣭⡙⣿⣿⢋⣭⣭⣅⡀⡀⡀
⡀⡀⠘⢿⣿⣿⣿⣿⣿⣿⡏⡀⣿⣿⣟⠉⣻⢸⣿⠸⣿⣅⣽⡀⡀⡀
⡀⡀⡀⡀⠻⡻⣿⣿⣿⣿⣧⣻⣌⣛⣛⣛⣵⡿⠋⢱⣬⣭⡆⡀⡀⡀
⡀⡀⡀⡀⡀⡈⠢⣉⣻⠿⣿⣿⠿⠟⢋⣾⣿⡇⣤⡀⡏⠉⡀⡀⡀⡀
⡀⡀⡀⡀⡀⡀⡀⡀⣿⡷⣴⠁⡀⡀⢿⣿⣿⣿⣿⣿⠇⡀⡀⡀⡀⡀
⡀⡀⡀⡀⡀⡀⡀⡀⠻⣿⣎⢳⣄⣀⣀⠜⡻⠛⠛⠛⠁⡀⡀⡀⡀⡀
⡀⡀⡀⡀⡀⡀⡀⡀⡀⠈⠻⣕⣉⣛⡻⠋⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀
⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀
⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀⡀
</code>
"""

@check_module_enabled("fun")
@command_control("fun")
async def skull_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_safe_reply(update, context, text=SKULL_ASCII, parse_mode=ParseMode.HTML)


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    prefixes = ['/', '!']
    application.add_handler(CustomPrefixHandler("kill", kill, custom_prefixes=prefixes))
    application.add_handler(CustomPrefixHandler("punch", punch, custom_prefixes=prefixes))
    application.add_handler(CustomPrefixHandler("slap", slap, custom_prefixes=prefixes))
    application.add_handler(CustomPrefixHandler("pat", pat, custom_prefixes=prefixes))
    application.add_handler(CustomPrefixHandler("bonk", bonk, custom_prefixes=prefixes))
    application.add_handler(CustomPrefixHandler("touch", damnbroski, custom_prefixes=prefixes))
    application.add_handler(CustomPrefixHandler("cowsay", cowsay_command, custom_prefixes=prefixes))
    application.add_handler(CustomPrefixHandler("ascii", ascii_command, custom_prefixes=prefixes))
    application.add_handler(CustomPrefixHandler("skull", skull_command, custom_prefixes=prefixes))
