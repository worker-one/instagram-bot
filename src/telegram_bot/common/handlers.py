"""Handler to show information about the application configuration."""
import logging

from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import CallbackQuery

from src.telegram_bot.common.markup import create_cancel_button

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


# React to any text if not command
def register_handlers(bot):
    """Register common handlers"""

    @bot.callback_query_handler(func=lambda call: call.data == "cancel")
    def cancel_callback(call: CallbackQuery, data: dict):
        """Cancel current operation"""
        logger.info("Cancel callback triggered by user %s", call.from_user.id)
        user = data["user"]
        #bot.send_message(call.message.chat.id, strings[user.lang].cancelled)
        # Delete the message that triggered the callback
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
        logger.info("Cancelled operation for user %s", user.id)
