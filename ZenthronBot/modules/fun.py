import logging
import random
import cowsay
import random
from pyfiglet import figlet_format
from telegram import Update, Dice
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..config import OWNER_ID
from ..core.utils import get_themed_gif, check_target_protection, check_username_protection, send_safe_reply, safe_escape
from ..core.constants import KILL_TEXTS, SLAP_TEXTS, PUNCH_TEXTS, PAT_TEXTS, BONK_TEXTS, CANT_TARGET_OWNER_TEXTS, CANT_TARGET_SELF_TEXTS
from ..core.decorators import check_module_enabled, command_control
from ..core.handlers import custom_handler

logger = logging.getLogger(__name__)


# --- FUN COMMANDS HELPER ---
@check_module_enabled("fun")
@command_control("fun")
async def _handle_action_command(update, context, texts, gifs, name, req_target=True, msg=""):
    message = update.effective_message
    target_mention = None
    if req_target:
        if update.message.reply_to_message and not update.message.reply_to_message.forum_topic_created:
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
@custom_handler("kill")
async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, KILL_TEXTS, ["gun", "gun shoting", "anime gun"], "kill", True, "Who to 'kill'?")

@check_module_enabled("fun")
@command_control("fun")
@custom_handler("punch")
async def punch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, PUNCH_TEXTS, ["punch", "hit", "anime punch"], "punch", True, "Who to 'punch'?")

@check_module_enabled("fun")
@command_control("fun")
@custom_handler("slap")
async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, SLAP_TEXTS, ["huge slap", "smack", "anime slap"], "slap", True, "Who to slap?")

@check_module_enabled("fun")
@command_control("fun")
@custom_handler("pat")
async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, PAT_TEXTS, ["pat", "pat anime", "anime pat"], "pat", True, "Who to pat?")

@check_module_enabled("fun")
@command_control("fun")
@custom_handler("bonk")
async def bonk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await _handle_action_command(update, context, BONK_TEXTS, ["bonk", "anime bonk"], "bonk", True, "Who to bonk?")

@check_module_enabled("fun")
@command_control("fun")
@custom_handler("touch")
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
@custom_handler("cowsay")
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
@custom_handler("ascii")
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
@custom_handler("skull")
async def skull_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_safe_reply(update, context, text=SKULL_ASCII, parse_mode=ParseMode.HTML)

@check_module_enabled("fun")
@command_control("fun")
@custom_handler("gamble")
async def gamble_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    
    dice_emojis = [
        Dice.DICE,
        Dice.DARTS,
        Dice.BASKETBALL,
        Dice.FOOTBALL,
        Dice.SLOT_MACHINE,
        Dice.BOWLING,
    ]

    try:
        random_emoji = random.choice(dice_emojis)
        await message.reply_dice(emoji=random_emoji)

    except Exception as e:
        logger.error(f"Failed to send dice emoji in gamble command: {e}")
        await message.reply_text("Oops, the dice seem to be broken!")

@check_module_enabled("fun")
@command_control("fun")
@custom_handler("decide")
async def decide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    answers = [
        "Yes, definitely.",
        "No, absolutely not.",
        "Maybe. The spirits are unsure.",
        "Without a doubt.",
        "My sources say no.",
        "You can rely on it.",
        "Don't count on it.",
        "Outlook good.",
        "I wouldn't bet on it.",
        "Signs point to yes.",
        "The answer is hazy, try again.",
        "Just do it!",
        "Why are you asking a bot?",
        "Probably.",
        "Seems unlikely.",
        "Yes.",
        "No."
    ]
    
    decision = random.choice(answers)
    
    if update.message.reply_to_message:
        await update.message.reply_to_message.reply_text(f"🤔... <b>{decision}</b>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"🤔... <b>{decision}</b>", parse_mode=ParseMode.HTML)


# --- HANDLER LOADER ---
def load_handlers(application: Application):
    application.add_handler(CommandHandler("kill", kill))
    application.add_handler(CommandHandler("punch", punch))
    application.add_handler(CommandHandler("slap", slap))
    application.add_handler(CommandHandler("pat", pat))
    application.add_handler(CommandHandler("bonk", bonk))
    application.add_handler(CommandHandler("touch", damnbroski))
    application.add_handler(CommandHandler("cowsay", cowsay_command))
    application.add_handler(CommandHandler("ascii", ascii_command))
    application.add_handler(CommandHandler("skull", skull_command))
    application.add_handler(CommandHandler("gamble", gamble_command))
    application.add_handler(CommandHandler("decide", decide_command))
