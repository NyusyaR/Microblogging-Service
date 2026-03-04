from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.pool import NullPool

from service_app.config import settings
from service_app.database import Microblogging, UserORM
from service_app.dependencies import get_session
from service_app.main import app


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)

    async with eng.begin() as conn:
        await conn.run_sync(Microblogging.metadata.drop_all)
        await conn.run_sync(Microblogging.metadata.create_all)

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    # сессия только для теста (arrange/assert)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    # приложение на каждый запрос получает НОВУЮ сессию
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session) -> UserORM:
    user = UserORM(name="Test", api_key="test")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db(engine):
    # Выполнится ПОСЛЕ каждого теста
    yield

    tables = [t.name for t in Microblogging.metadata.sorted_tables]
    if tables:
        sql = (
            "TRUNCATE "
            + ", ".join(f'"{name}"' for name in tables)
            + " RESTART IDENTITY CASCADE;"
        )
        async with engine.begin() as conn:
            await conn.execute(text(sql))
