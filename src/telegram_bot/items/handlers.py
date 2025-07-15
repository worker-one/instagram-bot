import logging
from pathlib import Path
from typing import Any, Dict

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..instagram.utils import sanitize_instagram_input
from ..menu.markup import create_menu_markup
from .markup import (
    create_cancel_button,
    create_instagram_account_menu_markup,
    create_instagram_accounts_list_markup,
    create_instagram_accounts_menu_markup,
)
from .service import (
    create_instagram_account,
    delete_instagram_account,
    read_instagram_account,
    read_instagram_accounts,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


class InstagramAccountState(StatesGroup):
    """States for Instagram account-related operations in the bot conversation flow."""

    menu = State()  # Main Instagram accounts menu state
    my_accounts = State()  # Viewing user's accounts
    add_account = State()  # Adding a new account
    username = State()  # Entering account username
    remove_account = State()  # Removing an account


def register_handlers(bot: TeleBot) -> None:
    """
    Register all Instagram account-related handlers for the bot.

    Args:
        bot: The Telegram bot instance to register handlers for
    """
    logger.info("Registering Instagram account handlers")

    @bot.callback_query_handler(func=lambda call: call.data == "instagram_accounts")
    def instagram_accounts_menu(call: types.CallbackQuery, data: Dict[str, Any]) -> None:
        """
        Handle the main Instagram accounts menu callback.

        Args:
            call: The callback query
            data: The data dictionary containing user and state information
        """
        user = data["user"]
        data["state"].set(InstagramAccountState.menu)

        markup = create_instagram_accounts_menu_markup(user.lang)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].instagram_accounts_menu,
            reply_markup=markup,
        )

    @bot.callback_query_handler(func=lambda call: call.data == "add_account")
    def start_add_account(call: types.CallbackQuery, data: Dict[str, Any]) -> None:
        """
        Start the account addition process by asking for username.

        Args:
            call: The callback query
            data: The data dictionary containing user, database session and state
        """
        user = data["user"]
        data["state"].set(InstagramAccountState.username)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_username,
            reply_markup=create_cancel_button(user.lang),
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("remove_account_"))
    def handle_remove_account(call: types.CallbackQuery, data: Dict[str, Any]) -> None:
        """
        Handle account removal.

        Args:
            call: The callback query with account ID embedded in data
            data: The data dictionary containing user and database session
        """
        user = data["user"]
        db_session = data["db_session"]
        data["state"].set(InstagramAccountState.remove_account)

        # Extract account ID from callback data
        account_id = int(call.data.split("_")[2])
        delete_instagram_account(db_session, account_id)

        bot.send_message(
            user.id,
            strings[user.lang].account_removed,
            reply_markup=create_menu_markup(user.lang),
        )

    @bot.callback_query_handler(func=lambda call: call.data == "my_accounts" or call.data.startswith("my_accounts_page_"))
    def show_my_accounts(call: types.CallbackQuery, data: Dict[str, Any]) -> None:
        """
        Display the user's Instagram accounts with pagination.
        """
        user = data["user"]
        db_session = data["db_session"]
        data["state"].set(InstagramAccountState.my_accounts)

        # Pagination
        accounts_per_page = 5
        if call.data.startswith("my_accounts_page_"):
            page = int(call.data.split("_")[-1])
        else:
            page = 1

        # Get all accounts and filter by current user, sort alphabetically
        accounts = read_instagram_accounts(db_session)
        user_accounts = sorted(
            [account for account in accounts if account.owner_id == user.id],
            key=lambda acc: acc.username.lower()
        )

        total_accounts = len(user_accounts)
        if not user_accounts:
            # Show empty state with back button
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    strings[user.lang].back_to_menu, callback_data="menu"
                )
            )
            bot.edit_message_text(
                chat_id=user.id,
                message_id=call.message.message_id,
                text=strings[user.lang].no_accounts,
                reply_markup=markup,
            )
            return

        # Pagination logic
        start = (page - 1) * accounts_per_page
        end = start + accounts_per_page
        page_accounts = user_accounts[start:end]

        markup = create_instagram_accounts_list_markup(user.lang, page_accounts)

        # Add pagination buttons
        nav_markup = types.InlineKeyboardMarkup()
        if page > 1:
            nav_markup.add(types.InlineKeyboardButton("⬅️", callback_data=f"my_accounts_page_{page-1}"))
        if end < total_accounts:
            nav_markup.add(types.InlineKeyboardButton("➡️", callback_data=f"my_accounts_page_{page+1}"))
        # Merge nav_markup into markup
        for row in nav_markup.keyboard:
            markup.keyboard.append(row)

        markup.add(types.InlineKeyboardButton(strings[user.lang].back_to_menu, callback_data="menu"))

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].your_accounts,
            reply_markup=markup,
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_account_"))
    def view_account(call: types.CallbackQuery, data: Dict[str, Any]) -> None:
        """
        Show details of a specific Instagram account.

        Args:
            call: The callback query with account ID embedded in data
            data: The data dictionary containing user and database session
        """
        user = data["user"]
        db_session = data["db_session"]

        # Extract account ID and fetch the account
        account_id = int(call.data.split("_")[2])
        account = read_instagram_account(db_session, account_id)

        if not account:
            bot.send_message(
                user.id,
                strings[user.lang].account_not_found,
                reply_markup=create_menu_markup(user.lang),
            )
            return

        # Format account details message
        message_text = strings[user.lang].account_details.format(
            username=account.username,
            created_at=account.created_at.strftime("%Y-%m-%d %H:%M"),
        )

        # Show account details with action buttons
        markup = create_instagram_account_menu_markup(user.lang, account.id)
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=message_text,
            reply_markup=markup,
            parse_mode="Markdown",
        )

    @bot.message_handler(state=InstagramAccountState.username)
    def process_username(message: types.Message, data: Dict[str, Any]) -> None:
        """
        Process the Instagram username input and complete account addition.
        Now supports multiple usernames separated by newlines and enforces account limit.
        """
        user = data["user"]
        db_session = data["db_session"]
        # Split input by newlines, strip, filter empty, sanitize each
        usernames = [
            sanitize_instagram_input(line.strip())
            for line in message.text.splitlines()
            if line.strip()
        ]

        # Get current accounts count for user
        accounts = read_instagram_accounts(db_session)
        user_accounts = [account for account in accounts if account.owner_id == user.id]
        accounts_limit = config.app.accounts_limit

        # Check if adding would exceed limit
        if len(user_accounts) + len(usernames) > accounts_limit:
            bot.send_message(
                user.id,
                strings[user.lang].limit_reached.format(limit=accounts_limit),
                reply_markup=create_menu_markup(user.lang),
            )
            data["state"].delete()
            return

        added_accounts = []
        for username in usernames:
            # Avoid duplicates in DB for this user
            if any(acc.username.lower() == username.lower() for acc in user_accounts + added_accounts):
                continue
            account = create_instagram_account(
                db_session,
                username=username,
                owner_id=message.from_user.id,
            )
            added_accounts.append(account)

        # Confirm account addition
        if added_accounts:
            usernames_str = ", ".join(f"@{acc.username}" for acc in added_accounts)
            bot.send_message(
                user.id,
                strings[user.lang].account_added.format(username=usernames_str),
                reply_markup=create_menu_markup(user.lang),
                parse_mode="Markdown",
            )
        else:
            bot.send_message(
                user.id,
                strings[user.lang].operation_cancelled,
                reply_markup=create_menu_markup(user.lang),
            )

        # Clear the state
        data["state"].delete()
