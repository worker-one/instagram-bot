import logging

from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


def create_cancel_button(lang: str) -> InlineKeyboardMarkup:
    """Create a cancel button for the items menu"""
    cancel_button = InlineKeyboardMarkup(row_width=1)
    cancel_button.add(
        InlineKeyboardButton(strings[lang].cancel, callback_data="cancel"),
    )
    return cancel_button


def create_keyboard_markup(
    options: list[str],
    callback_data: list[str],
    orientation: str = "vertical",
    ) -> InlineKeyboardMarkup:
    if orientation == "horizontal":
        keyboard_markup = InlineKeyboardMarkup(row_width=len(options))
    elif orientation == "vertical":
        keyboard_markup = InlineKeyboardMarkup(row_width=1)
    else:
        raise ValueError("Invalid orientation value. Must be 'horizontal' or 'vertical'")
    buttons = [InlineKeyboardButton(option, callback_data=data) for option, data in zip(options, callback_data)]
    keyboard_markup.add(*buttons)
    return keyboard_markup
