from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import RedirectResponse

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.crud.link import get_by_short_code, get_by_alias
from datetime import datetime, timezone

router = APIRouter()


async def get_db_session_redirect():
    """Get DB session for redirect endpoint."""
    async with async_session_maker() as session:
        yield session


@router.get("/links/{short_code}")
async def redirect_short_link(
    short_code: str,
    session: AsyncSession = Depends(get_db_session_redirect)
):
    """Перенаправить на оригинальный URL по короткому коду."""
    # Сначала пробуем найти по короткому коду (без инкремента)
    link = await get_by_short_code(session, short_code, increment_clicks=False)
    if not link:
        link = await get_by_alias(session, short_code)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Link with short code '{short_code}' not found",
        )

    now = datetime.now(timezone.utc)
    if link.expired_at and link.expired_at < now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Link has expired",
        )

    # Инкрементируем счётчик и обновляем last_used_at
    link.clicks_count += 1
    link.last_used_at = datetime.now(timezone.utc)
    await session.commit()

    # Инвалидируем кэш
    from app.core.cache import link_cache
    await link_cache.delete(link.short)
    if link.alias:
        await link_cache.delete(link.alias)

    return RedirectResponse(url=link.original)
