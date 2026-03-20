from sqlalchemy import select, and_, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag, link_tags
from app.models.links import Link


async def create_tag(
    session: AsyncSession,
    name: str,
    owner_id: int | None = None,
) -> Tag:
    """Создать тег."""
    # Проверяем существует ли тег с таким именем у этого владельца
    existing = await session.execute(
        select(Tag).where(
            Tag.name.ilike(name),
            Tag.owner_id == owner_id if owner_id else Tag.owner_id.is_(None)
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Tag '{name}' already exists")

    tag = Tag(name=name, owner_id=owner_id)
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


async def get_tags(
    session: AsyncSession,
    owner_id: int | None = None,
) -> list[Tag]:
    """Получить все теги владельца."""
    tags = await session.execute(
        select(Tag).where(
            Tag.owner_id == owner_id if owner_id else Tag.owner_id.is_(None)
        ).order_by(Tag.name)
    )
    return list(tags.scalars().all())


async def get_tag_by_id(
    session: AsyncSession,
    tag_id: int,
    owner_id: int | None = None,
) -> Tag | None:
    """Получить тег по ID."""
    query = select(Tag).where(Tag.id == tag_id)
    if owner_id:
        query = query.where(Tag.owner_id == owner_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def delete_tag(
    session: AsyncSession,
    tag: Tag,
) -> None:
    """Удалить тег."""
    await session.delete(tag)
    await session.commit()


async def add_tag_to_link(
    session: AsyncSession,
    link: Link,
    tag: Tag,
) -> None:
    """Добавить тег к ссылке."""
    # Check if association already exists using direct query
    exists = await session.execute(
        select(link_tags).where(
            link_tags.c.link_id == link.id,
            link_tags.c.tag_id == tag.id
        )
    )
    
    if not exists.first():
        # Insert directly into association table
        await session.execute(
            link_tags.insert().values(link_id=link.id, tag_id=tag.id)
        )
        await session.commit()


async def remove_tag_from_link(
    session: AsyncSession,
    link: Link,
    tag: Tag,
) -> None:
    """Удалить тег у ссылки."""
    # Delete directly from association table
    await session.execute(
        sql_delete(link_tags).where(
            link_tags.c.link_id == link.id,
            link_tags.c.tag_id == tag.id
        )
    )
    await session.commit()


async def get_links_by_tag(
    session: AsyncSession,
    tag: Tag,
) -> list[Link]:
    """Получить все ссылки с данным тегом."""
    links = await session.execute(
        select(Link).where(
            Link.tags.any(Tag.id == tag.id),
            Link.deleted_at.is_(None)
        )
    )
    return list(links.scalars().all())


async def search_links_by_tags(
    session: AsyncSession,
    tag_names: list[str],
    owner_id: int | None = None,
) -> list[Link]:
    """Поиск ссылок по нескольким тегам (AND логика)."""
    # Получаем теги по именам
    tags = await session.execute(
        select(Tag).where(
            Tag.name.in_([name.lower() for name in tag_names]),
            Tag.owner_id == owner_id if owner_id else Tag.owner_id.is_(None)
        )
    )
    tags_list = list(tags.scalars().all())
    
    if not tags_list:
        return []
    
    # Ищем ссылки со всеми тегами
    links = await session.execute(
        select(Link).where(
            Link.deleted_at.is_(None),
            *[Link.tags.any(Tag.id == tag.id) for tag in tags_list]
        )
    )
    return list(links.scalars().all())
