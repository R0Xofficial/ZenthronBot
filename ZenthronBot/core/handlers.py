from telegram import Update
from telegram.ext import MessageHandler, ContextTypes, filters

CUSTOM_COMMANDS = {}
PREFIXES = ['!', '?'] 

def custom_handler(name: str | list[str]):
    def decorator(func):
        if isinstance(name, list):
            for n in name:
                CUSTOM_COMMANDS[n.lower()] = func
        else:
            CUSTOM_COMMANDS[name.lower()] = func
        return func
    return decorator

async def command_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not message.text: return

    text = message.text
    
    used_prefix = None
    for p in PREFIXES:
        if text.startswith(p):
            used_prefix = p
            break
    
    if not used_prefix: return

    command_parts = text[len(used_prefix):].split()
    if not command_parts: return

    command = command_parts[0].lower()
    
    if command in CUSTOM_COMMANDS:
        context.args = command_parts[1:]
        await CUSTOM_COMMANDS[command](update, context)
        
def get_custom_command_handler():
    return MessageHandler(filters.TEXT & (~filters.COMMAND), command_router)
