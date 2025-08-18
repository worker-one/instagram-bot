import logging
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from omegaconf import OmegaConf
from telebot.states import State, StatesGroup
from telebot.types import CallbackQuery, InputMediaVideo, Message

from ..common.markup import create_cancel_button, create_keyboard_markup
from .service import InstagramWrapper
from .utils import create_resource, sanitize_instagram_input

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

load_dotenv(find_dotenv(usecwd=True))
HIKERAPI_TOKEN = os.getenv("HIKERAPI_TOKEN")

if not HIKERAPI_TOKEN:
    raise ValueError("HIKERAPI_TOKEN not found in environment variables")

instagram_client = InstagramWrapper(HIKERAPI_TOKEN)

# Define States
class AnalyzeAccountStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_number_of_videos = State()

def format_account_reel_response(
    idx: int,
    reel: dict[str, str],
    template: str,
    average_likes: float,
    average_comments: float
    ) -> str:

    likes_diff = int(reel["likes"] - average_likes)
    likes_comparative = (
        config.strings.comparative_less["ru"].format(value=f"{abs(likes_diff):,}".replace(",", " "))
        if likes_diff < 0 else
        config.strings.comparative_more["ru"].format(value=f"{likes_diff:,}".replace(",", " "))
    )

    comments_diff = int(reel["comments"] - average_comments)
    comments_comparative = (
        config.strings.comparative_less["ru"].format(value=f"{abs(comments_diff):,}".replace(",", " "))
        if comments_diff < 0 else
        config.strings.comparative_more["ru"].format(value=f"{comments_diff:,}".replace(",", " "))
    )

    reel_response = template.format(
        idx=idx,
        likes=f"{reel['likes']:,}".replace(",", " "),
        likes_comparative=likes_comparative,
        comments=f"{reel['comments']:,}".replace(",", " "),
        comments_comparative=comments_comparative,
        link=reel["link"],
        views=f"{reel['play_count']:,}".replace(",", " ")
    )
    return reel_response


def register_handlers(bot):
    @bot.callback_query_handler(func=lambda call: "analyze_account" in call.data)
    def analyze_account(call: CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(AnalyzeAccountStates.waiting_for_nickname)
        bot.send_message(
            call.from_user.id,
            config.strings.enter_nickname[user.lang],
            reply_markup=create_cancel_button(user.lang)
        )


    @bot.callback_query_handler(func=lambda call: call.data == "hikerapi_balance")
    def hikerapi_balance_handler(call: CallbackQuery, data: dict):
        balance_info = instagram_client.get_balance()
        bot.send_message(call.from_user.id, f'```json\n{balance_info["data"]}\n```', parse_mode="Markdown")


    @bot.message_handler(
        commands=["analyze_account", "account"]
    )
    def analyze_hashtag(message: Message, data: dict):
        user = data["user"]
        data["state"].set(AnalyzeAccountStates.waiting_for_nickname)
        bot.send_message(
            message.from_user.id,
            config.strings.enter_nickname[user.lang],
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.message_handler(state=AnalyzeAccountStates.waiting_for_nickname)
    def get_instagram_input(message: Message, data: dict):
        user = data["user"]
        user_input = sanitize_instagram_input(message.text)

        # Save user input in state data
        data["state"].add_data(user_input=user_input)

        bot.send_message(message.chat.id, config.strings.received[user.lang])

        logger.info(f"Fetching reels for account {user_input}")

        response = instagram_client.get_user_info(username=user_input)

        if response["status"] != 200:
            bot.send_message(message.chat.id, config.strings.no_found[user.lang])
            logger.info(f"Error fetching reels for account {user_input}")
            data["state"].delete()
            return
        else:
            account_user = response["data"]

        # Save account_user in state data
        data["state"].add_data(account_user=account_user)

        keyboard = create_keyboard_markup(["5", "10", "30"], ["5", "10", "30"], "horizontal")
        data["state"].set(AnalyzeAccountStates.waiting_for_number_of_videos)
        bot.send_message(
            message.chat.id,
            config.strings.ask_number_videos[user.lang],
            reply_markup=keyboard
        )

    @bot.callback_query_handler(
        func=lambda call: call.data in ["5", "10", "30"],
        state=AnalyzeAccountStates.waiting_for_number_of_videos
    )
    def get_number_of_videos(call: CallbackQuery, data: dict):
        user = data["user"]
        number_of_videos = int(call.data)

        # Retrieve user input from state data
        with data["state"].data() as data_items:
            input_text = data_items['user_input']
            account_user = data_items["account_user"]
        response = instagram_client.fetch_user_reels(account_user)

        if response["status"] == 200:
            reels_data = response["data"]
            reels_data.sort(key=lambda x: x["play_count"], reverse=True)

            logger.info(f"Found {len(reels_data)} reels for account {input_text}")

            result_ready_msg = config.strings.result_ready[user.lang].format(n=number_of_videos, nickname=input_text)
            bot.send_message(call.message.chat.id, result_ready_msg, parse_mode="HTML")

            response_template = config.strings.results[user.lang]

            # Compute average values for likes and comments
            average_likes = sum([reel["likes"] for reel in reels_data]) / len(reels_data)
            average_comments = sum([reel["comments"] for reel in reels_data]) / len(reels_data)

            reel_response_items = [
                format_account_reel_response(
                    idx + 1,
                    reel,
                    response_template,
                    average_likes,
                    average_comments
                )
                for idx, reel in enumerate(reels_data[:number_of_videos])
            ]

            data_list = [
                {
                    "Url": reel["link"],
                    "Likes": reel["likes"],
                    "Comments": reel["comments"],
                    "Views": reel["play_count"],
                    "Post Date": reel["post_date"],
                    "ER %": reel["er"] * 100,
                    "Owner": f'@{reel["owner"]}',
                    "Caption": reel["caption_text"]
                }
                for reel in reels_data
            ]

            # Generate unique filename and directory
            filename = create_resource(user.id, input_text, data_list)

            # Send response and download button
            footer = config.strings.final_message["ru"].format(bot_name=bot.get_me().username)
            response_message = '\n'.join(reel_response_items) + '\n' + footer

            download_button = create_keyboard_markup(
                [config.strings.download_report["ru"]],
                [f"GET {filename}"],
            )
            bot.send_message(
                call.message.chat.id,
                response_message,
                parse_mode="HTML",
                reply_markup=download_button
            )

            media_elements = []
            for reel in reels_data[:3]:
                media_elements.append(
                    InputMediaVideo(media=str(reel["video_url"]), caption=reel["title"])
                )
            if media_elements:
                bot.send_media_group(
                    call.message.chat.id,
                    media_elements
                )

            bot.send_message(
                call.message.chat.id,
                config.strings.advice_message["ru"],
                parse_mode="HTML"
            )

            data["state"].delete()

        else:
            if response["status"] == 403:
                bot.send_message(call.message.chat.id, config.strings.private_account[user.lang])
            else:
                bot.send_message(call.message.chat.id, config.strings.error[user.lang])
            data["state"].delete()
