from fastapi import APIRouter, Body, Depends, File, Path, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from service_app.dependencies import get_current_user_id, get_session
from service_app.repository import TweetsRepository, UsersRepository
from service_app.schemas import (
    ErrorResponse,
    MediaUploadOut,
    OkResponse,
    TweetCreateIn,
    TweetCreateOut,
    TweetsFeedOut,
    UserProfileResponse,
)

tweets_router = APIRouter()
medias_router = APIRouter()
users_router = APIRouter()


@tweets_router.post(
    "/tweets",
    response_model=TweetCreateOut,
    status_code=201,
    summary="Создать твит",
    description=(
        "Создаёт новый твит текущего пользователя.\n\n"
        "Опционально привязывает ранее загруженные медиа (tweet_media_ids), "
        "если они принадлежат пользователю и ещё не привязаны к твиту."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        400: {
            "model": ErrorResponse,
            "description": "Некорректные данные / media_id невалидны",
        },
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def post_tweets(
    user_id: int = Depends(get_current_user_id),
    data: TweetCreateIn = Body(...),
    session: AsyncSession = Depends(get_session),
):
    return await TweetsRepository.create_tweet(
        user_id=user_id, data=data, session=session
    )


@medias_router.post(
    "/medias",
    response_model=MediaUploadOut,
    status_code=201,
    summary="Загрузить медиа",
    description=(
        "Загрузка файла (multipart/form-data). "
        "Возвращает id загруженного файла (media_id)."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Некорректный файл (пустой/слишком большой/тип "
            "не поддерживается)",
        },
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def post_medias(
    user_id: int = Depends(get_current_user_id),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    return await TweetsRepository.create_media(
        user_id=user_id, file=file, session=session
    )


@tweets_router.delete(
    "/tweets/{id}",
    response_model=OkResponse,
    status_code=200,
    summary="Удалить твит",
    description="Удаляет твит, только если он " "принадлежит текущему пользователю.",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        403: {"model": ErrorResponse, "description": "Нельзя удалить чужой твит"},
        404: {"model": ErrorResponse, "description": "Твит не найден"},
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def delete_tweets(
    user_id: int = Depends(get_current_user_id),
    id: int = Path(gt=0, description="Id должен быть > 0"),
    session: AsyncSession = Depends(get_session),
):
    return await TweetsRepository.delete_tweets(
        user_id=user_id, tweet_id=id, session=session
    )


@tweets_router.post(
    "/tweets/{id}/likes",
    response_model=OkResponse,
    status_code=201,
    summary="Поставить лайк",
    description="Ставит лайк на твит. Нельзя лайкнуть свой твит. "
    "Повторный лайк не создаётся.",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        403: {"model": ErrorResponse, "description": "Нельзя лайкнуть свой твит"},
        404: {"model": ErrorResponse, "description": "Твит не найден"},
        409: {"model": ErrorResponse, "description": "Лайк уже поставлен"},
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def like_tweets(
    user_id: int = Depends(get_current_user_id),
    id: int = Path(gt=0, description="Id должен быть > 0"),
    session: AsyncSession = Depends(get_session),
):
    return await TweetsRepository.like_tweet(
        user_id=user_id, tweet_id=id, session=session
    )


@tweets_router.delete(
    "/tweets/{id}/likes",
    response_model=OkResponse,
    status_code=200,
    summary="Убрать лайк",
    description="Убирает лайк текущего пользователя с твита.",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        404: {"model": ErrorResponse, "description": "Твит или лайк не найден"},
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def delete_like_tweets(
    user_id: int = Depends(get_current_user_id),
    id: int = Path(gt=0, description="Id должен быть > 0"),
    session: AsyncSession = Depends(get_session),
):
    return await TweetsRepository.delete_like_tweet(
        user_id=user_id, tweet_id=id, session=session
    )


@users_router.post(
    "/users/{id}/follow",
    response_model=OkResponse,
    status_code=200,
    summary="Подписаться на пользователя",
    description="Создаёт подписку follower -> followed.",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        400: {"model": ErrorResponse, "description": "Нельзя подписаться на себя"},
        404: {"model": ErrorResponse, "description": "Пользователь не найден"},
        409: {"model": ErrorResponse, "description": "Подписка уже существует"},
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def follow_user(
    user_id: int = Depends(get_current_user_id),
    id: int = Path(gt=0, description="Id должен быть > 0"),
    session: AsyncSession = Depends(get_session),
):
    return await UsersRepository.follow_user(
        follower_id=user_id, followed_id=id, session=session
    )


@users_router.delete(
    "/users/{id}/follow",
    response_model=OkResponse,
    status_code=200,
    summary="Отписаться от пользователя",
    description="Удаляет подписку follower -> followed, если она существует.",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        400: {"model": ErrorResponse, "description": "Нельзя отписаться от себя"},
        404: {"model": ErrorResponse, "description": "Подписка не найдена"},
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def unfollow_user(
    user_id: int = Depends(get_current_user_id),
    id: int = Path(gt=0, description="Id должен быть > 0"),
    session: AsyncSession = Depends(get_session),
):
    return await UsersRepository.unfollow_user(
        follower_id=user_id, followed_id=id, session=session
    )


@tweets_router.get(
    "/tweets",
    response_model=TweetsFeedOut,
    status_code=200,
    summary="Получить ленту",
    description="Возвращает ленту твитов: свои твиты + твиты пользователей, "
    "на которых подписан текущий пользователь.",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def get_tweets(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await TweetsRepository.get_tweets(user_id=user_id, session=session)


@users_router.get(
    "/users/me",
    response_model=UserProfileResponse,
    status_code=200,
    summary="Мой профиль",
    description="Возвращает профиль текущего пользователя: "
    "id, name, followers, following.",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        404: {"model": ErrorResponse, "description": "Пользователь не найден"},
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def get_user_profile(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await UsersRepository.user_profile(user_id=user_id, session=session)


@users_router.get(
    "/users/{id}",
    response_model=UserProfileResponse,
    status_code=200,
    summary="Профиль пользователя по id",
    description="Возвращает профиль пользователя по id: "
    "id, name, followers, following.",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный api-key"},
        404: {"model": ErrorResponse, "description": "Пользователь не найден"},
        500: {"model": ErrorResponse, "description": "Ошибка базы данных"},
    },
)
async def selected_user(
    id: int = Path(gt=0, description="Id должен быть > 0"),
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await UsersRepository.selected_profile(user_id=id, session=session)
