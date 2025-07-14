from typing import cast
from telegram import Update
from telegram.ext import CommandHandler, filters

class CustomPrefixHandler(CommandHandler):
    """
    Niestandardowy CommandHandler, który pozwala na użycie
    niestandardowych prefiksów (np. '!', '.') zamiast '/'.
    """
    def __init__(self, command: str | list[str], callback, custom_prefixes: str | list[str] = '/', **kwargs):
        
        class CustomPrefixFilter(filters.BaseFilter):
            def filter(self, update: Update) -> bool:
                if not isinstance(update, Update) or not update.effective_message or not update.effective_message.text:
                    return False
                
                message_text = update.effective_message.text
                
                prefixes = custom_prefixes if isinstance(custom_prefixes, list) else [custom_prefixes]
                commands = command if isinstance(command, list) else [command]
                
                for p in prefixes:
                    for c in commands:
                        if message_text.startswith(f"{p}{c}"):
                            parts = message_text.split()
                            if parts[0] == f"{p}{c}" or parts[0].startswith(f"{p}{c}@"):
                                return True
                return False

        custom_filter = CustomPrefixFilter() & filters.COMMAND
        
        super().__init__(command, callback, filters=custom_filter, **kwargs)
