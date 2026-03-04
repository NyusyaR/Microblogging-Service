import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from service_app.database import (FollowerORM, LikeORM, MediaORM, TweetORM,
                                  UserORM)
from service_app.schemas import (ErrorResponse, LikeUser, MediaUploadOut,
                                 OkResponse, TweetCreateIn, TweetCreateOut,
                                 TweetOut, TweetsFeedOut, UserProfile,
                                 UserProfileResponse, UserShort)

UPLOAD_DIR = Path("/service_app/static")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif"}
MAX_SIZE = 2 * 1024 * 1024  # 2Mb


class TweetsRepository:  # noqa: PIE798
    @classmethod
    async def create_tweet(
        cls, user_id: int, data: TweetCreateIn, session: AsyncSession
    ) -> TweetCreateOut | ErrorResponse:
        """Создание нового твита"""
        try:
            tweet = TweetORM(
                author_id=user_id,
                content=data.tweet_data,
            )
            session.add(tweet)
            await session.flush()  # получаем tweet.id без commit

            if data.tweet_media_ids:  # если медиа есть, сохраняем
                # убираем дубли
                ids = list(dict.fromkeys(data.tweet_media_ids))
                stmt = (
                    update(MediaORM)
                    .where(MediaORM.id.in_(ids))
                    .where(MediaORM.tweet_id.is_(None))
                    .where(MediaORM.owner_id == user_id)
                    .values(twee_id=tweet.id)
                )
                result = await session.execute(stmt)
                updated_rows = result.rowcount or 0  # type: ignore[attr-defined]

                # проверка привязки медиа к твиту
                if updated_rows != len(ids):
                    await session.rollback()
                    return ErrorResponse(
                        error_type="NotFound",
                        error_message="Некоторые media_id не существуют, "
                        "не принадлежат пользователю "
                        "или уже привязаны",
                    )

            await session.commit()
            return TweetCreateOut(tweet_id=tweet.id)

        except SQLAlchemyError:
            await session.rollback()
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )

    @classmethod
    async def create_media(
        cls, user_id: int, file: UploadFile, session: AsyncSession
    ) -> MediaUploadOut | ErrorResponse:
        """Загрузка файлов из твита"""

        if not file or not file.filename:
            return ErrorResponse(
                error_type="BadRequest", error_message="Файл не передан"
            )

        data = await file.read()
        await file.close()

        if not data:
            return ErrorResponse(error_type="BadRequest", error_message="Файл пустой")

        if len(data) > MAX_SIZE:
            return ErrorResponse(
                error_type="BadRequest",
                error_message="Размер файла не должен превышать 2 Мбайт",
            )

        ext = ALLOWED_TYPES.get(file.content_type or "")
        if not ext:
            return ErrorResponse(
                error_type="BadRequest", error_message="Недопустимый тип файла"
            )

        file_name = f"{uuid.uuid4().hex}.{ext}"
        full_path = UPLOAD_DIR / file_name

        try:
            full_path.write_bytes(data)

            media = MediaORM(file_path=file_name, owner_id=user_id)
            session.add(media)

            await session.commit()
            await session.refresh(media)

            return MediaUploadOut(media_id=media.id)

        except SQLAlchemyError:
            await session.rollback()
            full_path.unlink(missing_ok=True)
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )

        except OSError:
            # если не удалось записать файл
            full_path.unlink(missing_ok=True)
            return ErrorResponse(
                error_type="IOError", error_message="Ошибка сохранения файла"
            )

    @classmethod
    async def delete_tweets(
        cls, user_id: int, tweet_id: int, session: AsyncSession
    ) -> OkResponse | ErrorResponse:
        """Удаление собственного твита пользователем"""
        try:
            tweet = await session.get(TweetORM, tweet_id)
            if tweet is None:
                return ErrorResponse(
                    error_type="NotFound", error_message="Твит отсутствует"
                )

            if tweet.author_id != user_id:
                return ErrorResponse(
                    error_type="Forbidden", error_message="Нельзя удалить чужой твит"
                )

            await session.delete(tweet)
            await session.commit()

            return OkResponse()

        except SQLAlchemyError:
            await session.rollback()
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )

    @classmethod
    async def like_tweet(
        cls, user_id: int, tweet_id: int, session: AsyncSession
    ) -> OkResponse | ErrorResponse:
        """Пользователь проставляет отметку 'Нравится' на твит"""
        try:
            tweet = await session.get(TweetORM, tweet_id)
            if tweet is None:
                return ErrorResponse(
                    error_type="NotFound", error_message="Твит отсутствует"
                )

            if tweet.author_id == user_id:
                return ErrorResponse(
                    error_type="Forbidden",
                    error_message="Нельзя поставить like на собственный твит",
                )

            like = LikeORM(user_id=user_id, tweet_id=tweet_id)
            session.add(like)

            await session.flush()
            await session.commit()

            return OkResponse()

        except IntegrityError:
            await session.rollback()
            return ErrorResponse(
                error_type="AlreadyLiked", error_message="Лайк уже поставлен"
            )

        except SQLAlchemyError:
            await session.rollback()
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )

    @classmethod
    async def delete_like_tweet(
        cls, user_id: int, tweet_id: int, session: AsyncSession
    ) -> OkResponse | ErrorResponse:
        """Пользователь убирает отметку 'Нравится' на твит"""
        try:
            stmt = select(LikeORM).where(
                and_(
                    LikeORM.user_id == user_id,
                    LikeORM.tweet_id == tweet_id,
                )
            )
            result = await session.execute(stmt)
            like = result.scalar_one_or_none()

            if like is None:
                return ErrorResponse(
                    error_type="NotFound", error_message="Лайк не найден"
                )

            await session.delete(like)
            await session.commit()
            return OkResponse()

        except SQLAlchemyError:
            await session.rollback()
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )

    @classmethod
    async def get_tweets(
        cls, user_id: int, session: AsyncSession
    ) -> TweetsFeedOut | ErrorResponse:
        """Пользователь получает ленту с твитами"""
        try:
            subq = select(FollowerORM.followed_id).where(
                FollowerORM.follower_id == user_id
            )

            stmt = (
                select(TweetORM)
                .where(or_(TweetORM.author_id == user_id, TweetORM.author_id.in_(subq)))
                .options(
                    selectinload(TweetORM.author),
                    selectinload(TweetORM.attachments),
                    selectinload(TweetORM.likes).selectinload(LikeORM.user),
                )
                .order_by(TweetORM.id.desc())
            )

            result = await session.execute(stmt)
            tweets = result.scalars().all()

            tweets_out = [
                TweetOut(
                    id=t.id,
                    content=t.content,
                    attachments=[f"/static/{m.file_path}" for m in t.attachments],
                    author=UserShort(id=t.author.id, name=t.author.name),
                    likes=[
                        LikeUser(id=like.user.id, name=like.user.name)
                        for like in t.likes
                    ],
                )
                for t in tweets
            ]

            return TweetsFeedOut(tweets=tweets_out)

        except SQLAlchemyError:
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )


class UsersRepository:  # noqa: PIE798
    @classmethod
    async def follow_user(
        cls, follower_id: int, followed_id: int, session: AsyncSession
    ) -> OkResponse | ErrorResponse:
        """Пользователь фоловит другого пользователя(подписывается на него)"""
        try:
            if follower_id == followed_id:
                return ErrorResponse(
                    error_type="BadRequest", error_message="Нельзя подписаться от себя"
                )

            followed_user = await session.get(UserORM, followed_id)
            if followed_user is None:
                return ErrorResponse(
                    error_type="NotFound", error_message="Пользователь не найден"
                )

            session.add(FollowerORM(follower_id=follower_id, followed_id=followed_id))
            await session.flush()
            await session.commit()
            return OkResponse()

        except IntegrityError:
            await session.rollback()
            return ErrorResponse(
                error_type="AlreadyFollowing", error_message="Подписка уже существует"
            )

        except SQLAlchemyError:
            await session.rollback()
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )

    @classmethod
    async def unfollow_user(
        cls, follower_id: int, followed_id: int, session: AsyncSession
    ) -> OkResponse | ErrorResponse:
        """Пользователь отписывается от другого подльзователя"""
        try:
            if followed_id == follower_id:
                return ErrorResponse(
                    error_type="BadRequest", error_message="Нельзя отписаться на себя"
                )

            stmt = select(FollowerORM).where(
                and_(
                    FollowerORM.follower_id == follower_id,
                    FollowerORM.followed_id == followed_id,
                )
            )
            result = await session.execute(stmt)
            follow = result.scalar_one_or_none()
            if follow is None:
                return ErrorResponse(
                    error_type="NotFound", error_message="Подписка не найдена"
                )

            await session.delete(follow)
            await session.commit()
            return OkResponse()

        except SQLAlchemyError:
            await session.rollback()
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )

    @classmethod
    async def user_profile(
        cls, user_id: int, session: AsyncSession
    ) -> UserProfileResponse | ErrorResponse:
        """Пользователь получает информацию о своём профиле"""
        try:
            stmt = (
                select(UserORM)
                .where(UserORM.id == user_id)
                .options(
                    selectinload(UserORM.followers).selectinload(FollowerORM.follower),
                    selectinload(UserORM.following).selectinload(FollowerORM.followed),
                )
            )

            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                return ErrorResponse(
                    error_type="NotFound", error_message="Пользователь не найден"
                )

            profile = UserProfile(
                id=user.id,
                name=user.name,
                followers=[
                    UserShort(id=i.follower.id, name=i.follower.name)
                    for i in user.followers
                ],
                following=[
                    UserShort(id=j.followed.id, name=j.followed.name)
                    for j in user.following
                ],
            )

            return UserProfileResponse(user=profile)

        except SQLAlchemyError:
            await session.rollback()
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )

    @classmethod
    async def selected_profile(
        cls, user_id: int, session: AsyncSession
    ) -> UserProfileResponse | ErrorResponse:
        """Пользователь получает информацию о профиле по его id"""
        try:
            stmt = (
                select(UserORM)
                .where(UserORM.id == user_id)
                .options(
                    selectinload(UserORM.followers).selectinload(FollowerORM.follower),
                    selectinload(UserORM.following).selectinload(FollowerORM.followed),
                )
            )

            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                return ErrorResponse(
                    error_type="NotFound", error_message="Пользователь не найден"
                )

            profile = UserProfile(
                id=user.id,
                name=user.name,
                followers=[
                    UserShort(id=i.follower.id, name=i.follower.name)
                    for i in user.followers
                ],
                following=[
                    UserShort(id=j.followed.id, name=j.followed.name)
                    for j in user.following
                ],
            )

            return UserProfileResponse(user=profile)

        except SQLAlchemyError:
            await session.rollback()
            return ErrorResponse(
                error_type="DBError", error_message="Ошибка базы данных"
            )
