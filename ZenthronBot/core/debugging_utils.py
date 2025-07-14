import logging
from telegram.ext import Application

logger = logging.getLogger(__name__)

class DebugApplication(Application):
    async def process_update(self, update):
        logger.critical("=" * 50)
        logger.critical(f"--- START PROCESSING UPDATE ID {update.update_id} ---")
        logger.critical(f"Update content: {update.to_json()}")
        logger.critical("=" * 50)
        
        for group in sorted(self.handlers.keys()):
            logger.info(f"--- Checking handlers in GROUP {group} ---")
            for handler in self.handlers[group]:
                handler_name = "Unknown Handler"
                if hasattr(handler, 'callback'):
                    handler_name = handler.callback.__name__
                
                try:
                    check = await handler.check_update(update)
                    if check:
                        logger.critical(f"✅ [MATCH FOUND] Handler '{handler_name}' w grupie {group} złapał tę aktualizację.")
                    else:
                        logger.debug(f"  [NO MATCH] Handler '{handler_name}' w grupie {group} nie pasuje.")
                except Exception as e:
                    logger.error(f"  [ERROR] Checking handler '{handler_name}': {e}")
            
        logger.info("--- Handing over to original process_update to execute callback ---")
        await super().process_update(update)
        logger.critical(f"--- END PROCESSING UPDATE ID {update.update_id} ---")
        logger.critical("=" * 50)
