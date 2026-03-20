from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Получить сессию БД."""
    async with async_session_maker() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
