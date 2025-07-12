from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from . import database
from .. import config

def check_module_enabled(module_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            
            if user and user.id == config.OWNER_ID:
                return await func(update, context, *args, **kwargs)

            if database.is_module_disabled(module_name):
                return

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator
