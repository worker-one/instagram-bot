import logging

from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from .models import InstagramAccount

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def create_instagram_accounts_menu_markup(lang: str) -> InlineKeyboardMarkup:
    """Create the Instagram accounts menu markup"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(strings[lang].add_account, callback_data="add_account")
    )
    markup.add(InlineKeyboardButton(strings[lang].list_my_accounts, callback_data="my_accounts"))
    markup.add(InlineKeyboardButton(strings[lang].back_to_menu, callback_data="menu"))
    return markup


def create_instagram_account_menu_markup(lang: str, account_id: int) -> InlineKeyboardMarkup:
    """Create the Instagram account menu markup"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            strings[lang].remove_account, callback_data=f"remove_account_{account_id}"
        )
    )
    markup.add(
        InlineKeyboardButton(strings[lang].back_to_accounts, callback_data="my_accounts")
    )
    markup.add(InlineKeyboardButton(strings[lang].back_to_menu, callback_data="menu"))
    return markup


def create_instagram_accounts_list_markup(lang: str, accounts: list[InstagramAccount]) -> InlineKeyboardMarkup:
    """Create the Instagram accounts list markup (no back/menu buttons here, handled in handler)."""
    markup = InlineKeyboardMarkup()
    for account in accounts:
        markup.add(
            InlineKeyboardButton(f"@{account.username}", callback_data=f"view_account_{account.id}")
        )
    return markup


def create_cancel_button(lang: str) -> InlineKeyboardMarkup:
    """Create a cancel button for the Instagram accounts menu"""
    cancel_button = InlineKeyboardMarkup(row_width=1)
    cancel_button.add(
        InlineKeyboardButton(strings[lang].cancel, callback_data="instagram_accounts"),
    )
    return cancel_button
