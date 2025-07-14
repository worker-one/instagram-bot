from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from ..models import Base, TimeStampMixin


class InstagramAccount(Base, TimeStampMixin):
    """Instagram account model"""

    __tablename__ = "instagram_accounts"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="instagram_accounts")
    is_verified = Column(Boolean, default=False)
    reels = relationship("InstagramReels", back_populates="account")
    

class InstagramReels(Base, TimeStampMixin):
    """Instagram Reels model"""

    __tablename__ = "instagram_reels"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("instagram_accounts.id"))
    reel_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
    caption = Column(String, nullable=True)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)

    account = relationship("InstagramAccount", back_populates="reels")


class SentReel(Base, TimeStampMixin):
    """Track reels sent to users to avoid duplicates"""

    __tablename__ = "sent_reels"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reel_url = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sent_reels")

    # Ensure uniqueness of user_id + reel_url combination
    __table_args__ = (UniqueConstraint('user_id', 'reel_url', name='unique_user_reel'),)