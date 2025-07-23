import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from omegaconf import OmegaConf
from telebot import TeleBot

from ..database.core import get_db
from ..instagram.service import InstagramWrapper
from ..items.service import (
    analyze_account_trends,
    cleanup_old_sent_reels,
    filter_unsent_reels,
    get_all_instagram_accounts_with_owners,
    record_sent_reel,
)

logger = logging.getLogger(__name__)

# Load configuration
CURRENT_DIR = Path(__file__).parent.parent / "items"
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Initialize Instagram wrapper
HIKERAPI_TOKEN = os.getenv("HIKERAPI_TOKEN")
if not HIKERAPI_TOKEN:
    logger.error("HIKERAPI_TOKEN not found in environment variables")
    instagram_wrapper = None
else:
    instagram_wrapper = InstagramWrapper(HIKERAPI_TOKEN)

# Initialize bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found in environment variables")
    bot = None
else:
    bot = TeleBot(BOT_TOKEN)

def send_trend_notifications():
    """Send trend notifications to all users based on their Instagram accounts"""
    if not instagram_wrapper or not bot:
        logger.error("Instagram wrapper or bot not initialized")
        return
        
    logger.info("Starting trend notifications task")
    
    try:
        # Get database session
        db_session = next(get_db())
        
        # Clean up old sent reels (older than 30 days)
        cleanup_old_sent_reels(db_session, days_old=30)
        
        # Get all Instagram accounts with their owners
        accounts_with_owners = get_all_instagram_accounts_with_owners(db_session)
        
        if not accounts_with_owners:
            logger.info("No Instagram accounts found")
            return
            
        # Group accounts by owner
        user_accounts = {}
        for account, user in accounts_with_owners:
            if user.id not in user_accounts:
                user_accounts[user.id] = {'user': user, 'accounts': []}
            user_accounts[user.id]['accounts'].append(account)
        
        # Process each user's accounts
        for user_id, data in user_accounts.items():
            user = data['user']
            accounts = data['accounts']
            
            logger.info(f"Processing notifications for user {user.id} with {len(accounts)} accounts")
            
            trending_content = []
            
            # Analyze each account
            for account in accounts:
                try:
                    # Get user info
                    user_info_result = instagram_wrapper.get_user_info(account.username)
                    if user_info_result['status'] != 200:
                        logger.warning(f"Could not fetch user info for {account.username}")
                        continue

                    user_info = user_info_result['data']

                    # Get reels
                    reels_result = instagram_wrapper.fetch_user_reels(user_info, n_media_items=10)
                    if reels_result['status'] != 200:
                        logger.warning(f"Could not fetch reels for {account.username}")
                        continue

                    reels = reels_result['data']

                    # Analyze for trending content
                    trends = analyze_account_trends(reels, user_info)
                    if trends:
                        trending_content.extend(trends)

                except Exception as e:
                    logger.error(f"Error processing account {account.username}: {e}")
                    continue

            # Filter out already sent reels
            unsent_trending_content = filter_unsent_reels(db_session, user.id, trending_content)
            # Send notifications if unsent trending content found
            send_user_notifications(user, unsent_trending_content, db_session)

        db_session.close()
        logger.info("Trend notifications task completed")

    except Exception as e:
        logger.error(f"Error in trend notifications task: {e}")


def send_user_notifications(user, trending_content: List[Dict[str, Any]], db_session):
    """Send notifications to a specific user"""
    try:
        # Get user's language
        lang = getattr(user, 'lang', 'en')

        # Send title message
        if len(trending_content) == 0:
            logger.info(f"No new trends for user {user.id}")
            bot.send_message(user.id, strings[lang].notification.no_new_trends)
            return
        title = strings[lang].notification.title
        bot.send_message(user.id, title)

        # Send each trending item and record it
        sent_count = 0
        for item in trending_content[:5]:  # Limit to 5 trending items
            message = strings[lang].notification.template.format(
                account_name=item['account_name'],
                video_url=item['video_url'],
                reason=item['reason'],
                views=item['views'],
                likes=item['likes'],
                comments=item['comments'],
                followers=item['followers'],
                trend_category=item['trend_category']
            )

            # Send message
            bot.send_message(user.id, message, parse_mode='Markdown')

            # Record that this reel was sent
            record_sent_reel(db_session, user.id, item['video_url'], item['account_name'])

            sent_count += 1

        logger.info(f"Sent {sent_count} new notifications to user {user.id}")

    except Exception as e:
        logger.error(f"Error sending notifications to user {user.id}: {e}")