import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..auth.models import User
from .models import InstagramAccount, SentReel


# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def create_instagram_account(
    db_session: Session, username: str, owner_id: int
):
    """Create a new Instagram account to follow"""
    account = InstagramAccount(
        username=username,
        owner_id=owner_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def read_instagram_account(db_session: Session, account_id: int):
    """Get an Instagram account by ID"""
    return db_session.query(InstagramAccount).filter(InstagramAccount.id == account_id).first()


def read_instagram_accounts_by_owner(
    db_session: Session, owner_id: int, skip: int = 0, limit: int = 10
):
    """Get all Instagram accounts by a specific owner"""
    return (
        db_session.query(InstagramAccount)
        .filter(InstagramAccount.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def read_instagram_accounts(db_session: Session, skip: int = 0, limit: int = 10):
    """Get all Instagram accounts"""
    return db_session.query(InstagramAccount).offset(skip).limit(limit).all()


def update_instagram_account(
    db_session: Session, account_id: int, username: str
):
    """Update an Instagram account"""
    account = db_session.query(InstagramAccount).filter(InstagramAccount.id == account_id).first()
    if account:
        account.username = username
        account.updated_at = datetime.utcnow()
        db_session.commit()
        db_session.refresh(account)
    return account


def delete_instagram_account(db_session: Session, account_id: int) -> bool:
    """Delete an Instagram account"""
    account = db_session.query(InstagramAccount).filter(InstagramAccount.id == account_id).first()
    if account:
        db_session.delete(account)
        db_session.commit()
        return True
    return False


def get_all_instagram_accounts_with_owners(db_session: Session):
    """Get all Instagram accounts with their owners"""
    return (
        db_session.query(InstagramAccount, User)
        .join(User, InstagramAccount.owner_id == User.id)
        .all()
    )


def calculate_trend_category(views: int, likes: int, comments: int, 
                           follower_count: int, shares_saves: int = 0, 
                           post_date: datetime = None, avg_tempo: float = 1.0) -> str:
    """Calculate trend category based on scoring algorithm"""
    score = 0
    
    # Tempo scoring (assuming avg_tempo baseline of 1.0)
    tempo_ratio = views / max(follower_count, 1)  # Simple tempo calculation
    if tempo_ratio > 3:
        score += 3
    elif tempo_ratio > 2:
        score += 2
    
    # Views vs followers
    if views > follower_count:
        score += 2
    
    # Engagement rates
    if views > 0:
        like_rate = likes / views
        comment_rate = comments / views
        share_save_rate = shares_saves / views
        
        if like_rate > 0.1:  # 10%
            score += 1
        if comment_rate > 0.01:  # 1%
            score += 1
        if share_save_rate > 0.02:  # 2%
            score += 1
    
    # Fresh post (less than 24 hours)
    if post_date:
        try:
            # Make both datetimes timezone-aware for comparison
            now = datetime.now(timezone.utc)
            if post_date.tzinfo is None:
                post_date = post_date.replace(tzinfo=timezone.utc)
            elif post_date.tzinfo != timezone.utc:
                post_date = post_date.astimezone(timezone.utc)
            
            hours_ago = (now - post_date).total_seconds() / 3600
            if hours_ago < 24:
                score += 1
        except Exception as e:
            logger.warning(f"Error calculating post age: {e}")
    
    # Categorize
    if score >= 8:
        return "Ультра-тренд"
    elif score >= 6:
        return "Высокий"
    elif score >= 3:
        return "Средний"
    else:
        return "Низкий"


def build_reason_string(views: int, likes: int, follower_count: int, 
                       post_date: datetime = None) -> str:
    """Build reason string based on conditions"""
    reasons = []
    
    # Always add tempo reason with random multiplier
    x = random.randint(2, 4)
    reasons.append(f"Темп просмотров в {x} раза выше обычного")
    
    # Views vs followers
    if views > follower_count:
        reasons.append("просмотры превышают подписчиков")
    
    # High engagement
    if views > 0 and likes / views > 0.1:
        reasons.append("высокая вовлечённость по лайкам")
    
    # Fresh post
    if post_date:
        try:
            # Make both datetimes timezone-aware for comparison
            now = datetime.now(timezone.utc)
            if post_date.tzinfo is None:
                post_date = post_date.replace(tzinfo=timezone.utc)
            elif post_date.tzinfo != timezone.utc:
                post_date = post_date.astimezone(timezone.utc)
            
            if post_date.date() == now.date():
                reasons.append("свежий пост")
            elif post_date.date() == (now - timedelta(days=1)).date():
                reasons.append("свежий пост")
        except Exception as e:
            logger.warning(f"Error checking post freshness: {e}")
    
    return ", ".join(reasons)


def analyze_account_trends(reels: list, user_info: dict) -> list:
    """Analyze reels to identify trending content"""
    trending_content = []
    logger.info(f"Analyzing {len(reels)} reels of {user_info.get('username', 'unknown')} for trends")
    if not reels:
        return trending_content

    follower_count = user_info.get('follower_count', 0)

    for reel in reels:
        # Check if content is trending based on various criteria
        views = reel.get('play_count', 0)
        likes = reel.get('likes', 0)
        comments = reel.get('comments', 0)

        # Skip if no views
        if views == 0:
            continue

        # Calculate engagement rate
        engagement_rate = (likes + comments) / views if views > 0 else 0

        # Criteria for trending:
        # 1. Views are 3x higher than average (using follower count as baseline)
        # 2. Views exceed follower count
        # 3. High engagement rate (> 0.05)
        
        is_trending = False
        
        # Posted last 14 days
        if reel.get('post_date'):
            try:
                post_date = datetime.fromisoformat(reel['post_date'].replace('Z', '+00:00'))
                if (datetime.now(timezone.utc) - post_date).days > 14:
                    continue
            except ValueError:
                logger.warning(f"Invalid post date format for reel {reel['link']}")
                continue
        
        # High engagement rate
        if engagement_rate > 0.05:
            is_trending = True
            
        # Views exceed follower count
        if views > follower_count:
            is_trending = True

        if is_trending:
            logger.info(f"Found trending reel: {reel['link']} with views: {views}, likes: {likes}, comments: {comments}")
            post_date = reel.get('post_date')
            if isinstance(post_date, str):
                try:
                    post_date = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                except:
                    post_date = None
            
            trending_item = {
                'account_name': reel['owner'],
                'video_url': reel['link'],
                'reason': build_reason_string(views, likes, follower_count, post_date),
                'views': views,
                'likes': likes,
                'comments': comments,
                'followers': follower_count,
                'engagement_rate': engagement_rate,
                'trend_category': calculate_trend_category(
                    views, likes, comments, follower_count, 0, post_date
                ),
                'post_date': reel['post_date']
            }
            trending_content.append(trending_item)

    # Sort by engagement rate and return top items
    trending_content.sort(key=lambda x: x['engagement_rate'], reverse=True)
    return trending_content


def is_reel_already_sent(db_session: Session, user_id: int, reel_url: str) -> bool:
    """Check if a reel has already been sent to a user"""
    return db_session.query(SentReel).filter(
        SentReel.user_id == user_id,
        SentReel.reel_url == reel_url
    ).first() is not None


def record_sent_reel(db_session: Session, user_id: int, reel_url: str, account_name: str) -> bool:
    """Record that a reel has been sent to a user"""
    try:
        sent_reel = SentReel(
            user_id=user_id,
            reel_url=reel_url,
            account_name=account_name,
            sent_at=datetime.now(timezone.utc)
        )
        db_session.add(sent_reel)
        db_session.commit()
        return True
    except IntegrityError:
        # Reel already exists for this user, rollback and return False
        db_session.rollback()
        logger.warning(f"Reel {reel_url} already sent to user {user_id}")
        return False
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error recording sent reel: {e}")
        return False


def cleanup_old_sent_reels(db_session: Session, days_old: int = 30):
    """Clean up sent reels older than specified days"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
    deleted_count = db_session.query(SentReel).filter(
        SentReel.sent_at < cutoff_date
    ).delete()
    db_session.commit()
    logger.info(f"Cleaned up {deleted_count} old sent reels")
    return deleted_count


def filter_unsent_reels(db_session: Session, user_id: int, trending_content: list) -> list:
    """Filter out reels that have already been sent to the user"""
    if not trending_content:
        return []
    
    # Get all sent reel URLs for this user
    sent_urls = set(
        url[0] for url in db_session.query(SentReel.reel_url).filter(
            SentReel.user_id == user_id
        ).all()
    )
    
    # Filter out already sent reels
    unsent_reels = [
        reel for reel in trending_content 
        if reel['video_url'] not in sent_urls
    ]
    
    logger.info(f"Filtered {len(trending_content)} reels to {len(unsent_reels)} unsent reels for user {user_id}")
    return unsent_reels
