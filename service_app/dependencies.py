from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from service_app.database import UserORM, new_session
from service_app.security import api_key_header


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with new_session() as session:
        yield session


async def get_current_user_id(
    session: AsyncSession = Depends(get_session),
    api_key: str = Security(api_key_header),
) -> int:
    """Проверка user_id"""
    stmt = select(UserORM.id).where(UserORM.api_key == api_key)
    result = await session.execute(stmt)
    user_id = result.scalar_one_or_none()

    if user_id is None:
        raise HTTPException(status_code=401, detail="Неверный api-key")

    return user_id
