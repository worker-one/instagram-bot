from email.mime import application
import json
import httpx
import logging
import os
from time import sleep

from hikerapi import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InstagramWrapper:
    def __init__(self, token: str):
        self.token = token
        self.client = Client(token=token)
        self.use_cache = True

    def get_balance(self):
        headers = {
            "x-access-key": self.token,
            "accept": "application/json",
        }
        response = httpx.get("https://api.hikerapi.com/sys/balance", headers=headers)
        if response.status_code == 200:
            return {"status": 200, "data": response.json()}
        return {"status": response.status_code, "message": response.text}

    def get_user_info(self, username: str):
        user = self.client.user_by_username_v1(username)
        if not user:
            return {"status": 404, "message": "User not found"}
        return {"status": 200, "data": user}

    def fetch_user_reels(
            self, user, n_media_items: int = 25
        ):
        
        print(user)

        username = user["username"]
        user_id = user["pk"]

        logger.info(f"Fetching reels for user {username} (ID: {user_id})")

        # Check cache
        if self.use_cache and os.path.exists(f"cache/user/{username}/reels.json"):
            with open(f"cache/user/{username}/reels.json", "r", encoding="utf-8") as f:
                media_list = json.loads(f.read())
                logger.info(f"Found reels for user {username} in cache")
        else:
            media_list = None

        # Fetch reels if not in cache
        if not media_list:
            if user["is_private"]:
                return {"status": 403, "message": "Account is private"}

            try:
                media_list = self.client.user_clips_v1(user_id, amount=n_media_items)
            except Exception as e:
                logger.error(f"Error fetching reels for user {username}: {e}. Retrying...")
                # try again
                sleep(1)
                try:
                    media_list = self.client.user_clips_v1(user_id, amount=n_media_items)
                except Exception as e:
                    logger.error(f"Error fetching reels for user {username}: {e}")
                    return {"status": 500, "message": "Internal server error"}

            if not media_list:
                return {"status": 402, "message": "No reels found"}

            # Save retrieved reels in cache folder
            os.makedirs(f"cache/user/{username}", exist_ok=True)
            with open(f"cache/user/{username}/reels.json", "w", encoding="utf-8") as f:
                json.dump(media_list, f, ensure_ascii=False)

        reels = []
        for media in media_list:
            if media["media_type"] in {2, 8} and media["play_count"] != 0:
                if media["play_count"] != 0:
                    er = (media["like_count"] + media["comment_count"]) / media["play_count"]
                else:
                    er = 0
                reel_item = {
                    "pk": media["pk"],
                    "title": media["title"],
                    "caption_text": media["caption_text"],
                    "likes": media["like_count"],
                    "comments": media["comment_count"],
                    "post_date": media["taken_at"],
                    "link": f"https://www.instagram.com/reel/{media['code']}/",
                    "video_url": media["video_url"],
                    "play_count": media["play_count"],
                    "id": media["id"],
                    "er": er,
                    "owner": username,
                }
                reels.append(reel_item)
        return {"status": 200, "data": reels}

    def fetch_hashtag_reels(self, hashtag: str, n_media_items: int = 50):
        # Check cache
        if self.use_cache and os.path.exists(f"cache/hashtag/{hashtag}/reels.json"):
            with open(f"cache/hashtag/{hashtag}/reels.json", "r", encoding="utf-8") as f:
                media_list = json.loads(f.read())
                logger.info(f"Found reels for hashtag {hashtag} in cache")
        else:
            media_list = None

        if not media_list:

            try:
                media_list = self.client.hashtag_medias_top_v1(hashtag, amount=n_media_items)
            except Exception as e:
                logger.error(f"Error fetching reels for hashtag {hashtag}: {e}. Retrying...")
                # try again
                sleep(1)
                try:
                    media_list = self.client.hashtag_medias_top_v1(hashtag, amount=n_media_items)
                except Exception as e:
                    logger.error(f"Error fetching reels for hashtag {hashtag}: {e}")
                    return {"status": 500, "message": "Internal server error"}

            if not media_list:
                return {"status": 404, "message": "Hashtag not found"}

            # Save retrieved reels in cache folder
            os.makedirs(f"cache/hashtag/{hashtag}", exist_ok=True)
            with open(f"cache/hashtag/{hashtag}/reels.json", "w", encoding="utf-8") as f:
                json.dump(media_list, f, ensure_ascii=False)

        reels = []
        for media in media_list:
            if media["media_type"] in {2, 8} and media["play_count"] != 0:
                if media["play_count"] != 0:
                    er = (media["like_count"] + media["comment_count"]) / media["play_count"]
                else:
                    er = 0
                reel_item = {
                    "pk": media["pk"],
                    "title": media["title"],
                    "caption_text": media["caption_text"],
                    "likes": media["like_count"],
                    "comments": media["comment_count"],
                    "post_date": media["taken_at"],
                    "link": f"https://www.instagram.com/reel/{media['code']}/",
                    "video_url": media["video_url"],
                    "play_count": media["play_count"],
                    "id": media["id"],
                    "er": er,
                    "owner": media["user"]["username"]
                }
                reels.append(reel_item)
        logger.info(f"Found {len(reels)} reels for hashtag {hashtag}")
        return {"status": 200, "data": reels}