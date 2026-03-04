from sqlalchemy import (CheckConstraint, ForeignKey, String, Text,
                        UniqueConstraint)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from service_app.config import settings

# engine = create_async_engine(
# "postgresql+asyncpg://myuser:mypass@172.19.231.243:5432/microblogging")
engine = create_async_engine(settings.database_url, echo=False)
new_session = async_sessionmaker(engine, expire_on_commit=False)


class Microblogging(DeclarativeBase):
    pass


class FollowerORM(Microblogging):
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "followed_id", name="uq_follow_pair"),
        CheckConstraint(
            "follower_id != followed_id",
            name="ck_no_self_follow",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    followed_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    follower: Mapped["UserORM"] = relationship(
        "UserORM", foreign_keys=[follower_id], back_populates="following"
    )
    followed: Mapped["UserORM"] = relationship(
        "UserORM", foreign_keys=[followed_id], back_populates="followers"
    )


class TweetORM(Microblogging):
    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    attachments: Mapped[list["MediaORM"]] = relationship(
        "MediaORM",
        back_populates="tweet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    author: Mapped["UserORM"] = relationship("UserORM", back_populates="tweets")
    likes: Mapped[list["LikeORM"]] = relationship(
        "LikeORM",
        back_populates="tweet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MediaORM(Microblogging):
    __tablename__ = "medias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tweet_id: Mapped[int | None] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"), nullable=True
    )

    owner: Mapped["UserORM"] = relationship("UserORM")
    tweet: Mapped["TweetORM"] = relationship("TweetORM", back_populates="attachments")


class LikeORM(Microblogging):
    __tablename__ = "likes_tweets"
    __table_args__ = (
        UniqueConstraint("user_id", "tweet_id", name="uq_like_user_tweet"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tweet_id: Mapped[int] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["UserORM"] = relationship("UserORM", back_populates="likes")
    tweet: Mapped["TweetORM"] = relationship("TweetORM", back_populates="likes")


class UserORM(Microblogging):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    api_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    tweets: Mapped[list["TweetORM"]] = relationship(
        "TweetORM",
        back_populates="author",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    likes: Mapped[list["LikeORM"]] = relationship(
        "LikeORM",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    following: Mapped[list["FollowerORM"]] = relationship(
        "FollowerORM",
        foreign_keys=[FollowerORM.follower_id],
        back_populates="follower",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    followers: Mapped[list["FollowerORM"]] = relationship(
        "FollowerORM",
        foreign_keys=[FollowerORM.followed_id],
        back_populates="followed",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Microblogging.metadata.create_all)
