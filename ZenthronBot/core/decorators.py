from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from .database import is_command_disabled_in_chat, is_module_disabled
from ..config import OWNER_ID
from .utils import _can_user_perform_action

def check_module_enabled(module_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            
            if user and user.id == OWNER_ID:
                return await func(update, context, *args, **kwargs)

            if is_module_disabled(module_name):
                return

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def command_control(command_name: str):
    def decorator(func):
        setattr(func, '_is_manageable', True)
        setattr(func, '_command_name', command_name)
        
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            chat = update.effective_chat

            if not chat or chat.type not in ["group", "supergroup"]:
                return await func(update, context, *args, **kwargs)

            if is_command_disabled_in_chat(chat.id, command_name):
                
                is_admin = await _can_user_perform_action(
                    update, 
                    context, 
                    'can_manage_chat', 
                    failure_message=None,
                    allow_bot_privileged_override=True
                )
                
                if is_admin:
                    pass
                else:
                    return

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator
