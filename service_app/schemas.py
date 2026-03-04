from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ServiceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OkResponse(ServiceBase):
    """Отдаем сообщение о статусе операции
    п.п. 3-7 ТЗ"""

    result: bool = True


class ErrorResponse(ServiceBase):
    """Отдаем сообщение об ошибке"""

    result: bool = False
    error_type: str
    error_message: str


class UserShort(ServiceBase):
    """Автор твита"""

    id: int = Field(description="Идентификато пользователя")
    name: str = Field(description="Имя пользователя")


class UserProfile(ServiceBase):
    """Отдаем профиль пользователя"""

    id: int = Field(description="Идентификато пользователя")
    name: str = Field(description="Имя пользователя")
    followers: list[UserShort] = Field(default_factory=list, description="Подписчики")
    following: list[UserShort] = Field(
        default_factory=list, description="Подписки пользователя"
    )


class LikeUser(ServiceBase):
    """Пользователь ставит Like твиту"""

    id: int = Field(description="Идентификато пользователя")
    name: str = Field(description="Имя пользователя")


class TweetOut(ServiceBase):
    """Отдаем все твиты пользователя"""

    id: int = Field(description="Идентификатор твита")
    content: str = Field(description="Содержание твита")
    attachments: list[str] = Field(default_factory=list, description="Вложения твита")
    author: UserShort = Field(description="Автор твита")
    likes: list[LikeUser] = Field(default_factory=list, description="Лайки твита")


class TweetCreateIn(ServiceBase):
    """п.1 ТЗ. Отдаем при входе POST /api/tweets"""

    tweet_data: str = Field(min_length=1, description="Текст твита")
    tweet_media_ids: Optional[list[int]] = Field(default=None, description="Id медиа")


class TweetCreateOut(OkResponse):
    """п.1 ТЗ. Отдаем на выходе POST /api/tweets"""

    tweet_id: int = Field(description="Идентификатор твита")


class MediaUploadOut(OkResponse):
    """п.2 ТЗ. Отдаем на выходе POST /api/medias"""

    media_id: int = Field(description="Идентификатор медиа")


class TweetsFeedOut(OkResponse):
    """п.8 ТЗ. Отдаем на выходе GET /api/tweets"""

    tweets: list[TweetOut] = Field(default_factory=list)


class UserProfileResponse(OkResponse):
    """п.п. 9-10 ТЗ. GET /api/users/me, /api/users/<id>"""

    user: UserProfile
