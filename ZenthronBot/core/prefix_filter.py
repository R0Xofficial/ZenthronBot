from telegram.ext import filters

class PrefixFilter(filters.BaseFilter):
    def __init__(self, prefixes: list[str]):
        super().__init__()
        self.prefixes = tuple(prefixes)

    def filter(self, message) -> bool:
        if not hasattr(message, 'text') or not message.text:
            return False
        return message.text.startswith(self.prefixes)
