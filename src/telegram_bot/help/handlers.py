import logging
from pathlib import Path
from typing import Any, Dict

from omegaconf import OmegaConf
from telebot import TeleBot, types

from ..menu.markup import create_menu_markup

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


def register_handlers(bot: TeleBot) -> None:
    """
    Register all Instagram account-related handlers for the bot.

    Args:
        bot: The Telegram bot instance to register handlers for
    """
    logger.info("Registering Instagram account handlers")

    @bot.callback_query_handler(func=lambda call: call.data == "help")
    def help_command(call: types.CallbackQuery, data: Dict[str, Any]) -> None:
        """
        Handle the help command callback.

        Args:
            call: The callback query
            data: The data dictionary containing user and state information
        """
        user = data["user"]
        bot.send_message(
            call.message.chat.id,
            strings[user.lang].help,
            reply_markup=create_menu_markup(user.lang),
        )