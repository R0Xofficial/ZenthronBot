from telegram import Update
from telegram.ext import CommandHandler, filters

class CustomPrefixHandler(CommandHandler):
    def __init__(self, command: str | list[str], callback, custom_prefixes: str | list[str] = '/', **kwargs):
        
        class CustomPrefixFilter(filters.BaseFilter):
            def filter(self, update: Update) -> bool:
                if not update.effective_message or not update.effective_message.text:
                    return False
                
                message_text = update.effective_message.text
                
                prefixes_to_check = custom_prefixes if isinstance(custom_prefixes, list) else [custom_prefixes]
                commands_to_check = command if isinstance(command, list) else [command]
                
                for p in prefixes_to_check:
                    for c in commands_to_check:
                        if message_text.lower().startswith(f"{p}{c}".lower()):
                            parts = message_text.split()
                            command_part = parts[0].split('@')[0]
                            if command_part.lower() == f"{p}{c}".lower():
                                return True
                return False

        final_filter = filters.UpdateType.MESSAGE & CustomPrefixFilter()
        
        super().__init__(command, callback, filters=final_filter, **kwargs)

class NotACommandFilter(filters.BaseFilter):
    def __init__(self, prefixes: list[str]):
        super().__init__()
        self.prefixes = tuple(prefixes)

    def filter(self, message) -> bool:
        if not hasattr(message, 'text') or not message.text:
            return True
            
        return not message.text.startswith(self.prefixes)
