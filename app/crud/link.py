from datetime import datetime, timedelta, timezone

from sqids import Sqids
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.cache import link_cache
from app.models.links import Link


sqids = Sqids(min_length=settings.LINK_LENGHT)


def encode_id(id: int) -> str:
    return sqids.encode([id])


def decode_short_code(short_code: str) -> int | None:
    decoded = sqids.decode(short_code)
    return decoded[0] if decoded else None


async def create_link(
    session: AsyncSession,
    original: str,
    alias: str | None = None,
    expired_at: int | None = None,
    owner_id: int | None = None,
) -> Link:
    """Создать новую короткую ссылку."""
    if alias:
        existing = await session.execute(
            select(Link).where(
                Link.alias == alias,
                Link.deleted_at.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Alias '{alias}' already exists")

    existing = await session.execute(
        select(Link).where(
            Link.original == original,
            Link.deleted_at.is_(None),
            Link.expired_at.is_(None)
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Link with this URL already exists")

    link = Link(
        original=original,
        alias=alias,
        short="",
        owner_id=owner_id,
    )

    if expired_at:
        link.expired_at = datetime.now(timezone.utc) + timedelta(minutes=expired_at)

    session.add(link)
    await session.flush()

    link.short = encode_id(link.id)

    await session.commit()
    await session.refresh(link)

    return link


async def get_by_short_code(
    session: AsyncSession,
    short_code: str,
    increment_clicks: bool = False,
) -> Link | None:
    """Получить ссылку по короткому коду."""
    cached = await link_cache.get(short_code)
    if cached and not increment_clicks:
        return Link(**cached)

    link = await session.execute(
        select(Link).where(
            Link.short == short_code,
            Link.deleted_at.is_(None)
        )
    )
    result = link.scalar_one_or_none()

    if result:
        if increment_clicks:
            result.clicks_count += 1
            result.last_used_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(result)

        # Кэшируем после обновления
        await link_cache.set(short_code, {
            "id": result.id,
            "original": result.original,
            "short": result.short,
            "alias": result.alias,
            "clicks_count": result.clicks_count,
            "created_at": result.created_at,
            "expired_at": result.expired_at,
            "last_used_at": result.last_used_at,
            "owner_id": result.owner_id,
        })

    return result


async def get_by_alias(
    session: AsyncSession,
    alias: str,
) -> Link | None:
    """Получить ссылку по алиасу."""
    cached = await link_cache.get(alias)
    if cached:
        return Link(**cached)

    link = await session.execute(
        select(Link).where(
            Link.alias == alias,
            Link.deleted_at.is_(None)
        )
    )
    result = link.scalar_one_or_none()

    if result:
        await link_cache.set(alias, {
            "id": result.id,
            "original": result.original,
            "short": result.short,
            "alias": result.alias,
            "clicks_count": result.clicks_count,
            "created_at": result.created_at,
            "expired_at": result.expired_at,
            "last_used_at": result.last_used_at,
            "owner_id": result.owner_id,
        })

    return result


async def search_by_original(
    session: AsyncSession,
    original: str,
) -> list[Link]:
    """Поиск ссылок по частичному совпадению оригинального URL."""
    links = await session.execute(
        select(Link).where(
            Link.original.ilike(f"%{original}%"),
            Link.deleted_at.is_(None)
        ).limit(50)
    )
    return list(links.scalars().all())


async def delete_link(
    session: AsyncSession,
    link: Link,
) -> None:
    """Мягкое удаление ссылки."""
    link.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    await link_cache.delete(link.short)
    if link.alias:
        await link_cache.delete(link.alias)


def is_owner(link: Link, user_id: int) -> bool:
    """Проверить, является ли пользователь владельцем ссылки."""
    return link.owner_id == user_id


async def update_link(
    session: AsyncSession,
    link: Link,
    original: str | None = None,
    alias: str | None = None,
    expired_at: int | None = None,
) -> Link:
    """Обновить ссылку."""
    if original:
        link.original = original
    if alias:
        link.alias = alias
    if expired_at:
        link.expired_at = datetime.now(timezone.utc) + timedelta(minutes=expired_at)

    await session.commit()
    await session.refresh(link)

    # Инвалидация кэша
    await link_cache.delete(link.short)
    if link.alias:
        await link_cache.delete(link.alias)

    return link


async def get_stats(
    link: Link,
) -> dict:
    """Получить статистику ссылки."""
    now = datetime.now(timezone.utc)
    is_active = (
        link.deleted_at is None and
        (link.expired_at is None or link.expired_at > now)
    )

    return {
        "id": link.id,
        "short": link.short,
        "original": link.original,
        "alias": link.alias,
        "clicks_count": link.clicks_count,
        "created_at": link.created_at,
        "expired_at": link.expired_at,
        "last_used_at": link.last_used_at,
        "is_active": is_active,
    }


async def get_expired_links(
    session: AsyncSession,
    limit: int = 100,
) -> list[Link]:
    """Получить список истекших ссылок."""
    now = datetime.now(timezone.utc)
    links = await session.execute(
        select(Link).where(
            Link.expired_at < now,
            Link.deleted_at.is_(None)
        ).order_by(Link.expired_at).limit(limit)
    )
    return list(links.scalars().all())


async def get_unused_links(
    session: AsyncSession,
    days: int = 30,
    limit: int = 100,
) -> list[Link]:
    """Получить ссылки, по которым не было переходов заданное количество дней."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    links = await session.execute(
        select(Link).where(
            Link.deleted_at.is_(None),
            (Link.last_used_at.is_(None) | (Link.last_used_at < cutoff)),
            Link.created_at < cutoff
        ).order_by(Link.created_at).limit(limit)
    )
    return list(links.scalars().all())


async def cleanup_old_links(
    session: AsyncSession,
    days: int = 30,
) -> int:
    """Удалить старые неиспользуемые ссылки. Возвращает количество удаленных."""
    links = await get_unused_links(session, days)
    
    for link in links:
        link.deleted_at = datetime.now(timezone.utc)
        await link_cache.delete(link.short)
        if link.alias:
            await link_cache.delete(link.alias)
    
    await session.commit()
    return len(links)
