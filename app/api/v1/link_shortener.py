from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from datetime import datetime, timezone

from app.schemas.link import LinkCreate, LinkUpdate, LinkResponse
from app.api.v1.dependencies import DbSession
from app.crud import link as link_crud
from app.models.links import Link
from app.api.v1.auth_dependencies import OptionalUser, RequiredUser
from app.crud.link import is_owner
from app.crud import tag as tag_crud


router = APIRouter(prefix="/links")


@router.get(
    "/my",
    response_model=list[LinkResponse],
    summary="Мои ссылки",
    responses={
        401: {"description": "Не авторизован"},
    },
)
async def get_my_links(
    current_user: RequiredUser,
    session: DbSession,
    skip: int = 0,
    limit: int = 50,
) -> list[Link]:
    """Получить список ссылок текущего пользователя."""
    from sqlalchemy import select
    links = await session.execute(
        select(Link).where(
            Link.owner_id == current_user.id,
            Link.deleted_at.is_(None)
        ).order_by(Link.created_at.desc()).offset(skip).limit(limit)
    )
    return list(links.scalars().all())


@router.get(
    "/search",
    response_model=list[LinkResponse],
    summary="Поиск ссылок по URL",
)
async def search(
    original_url: str,
    session: DbSession,
    current_user: RequiredUser,
) -> list[Link]:
    """Поиск ссылок по частичному совпадению оригинального URL."""
    links = await link_crud.search_by_original(session, original_url)
    # Фильтруем только ссылки текущего пользователя
    return [link for link in links if link.owner_id == current_user.id]


@router.post(
    "/shorten",
    response_model=LinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать короткую ссылку",
    responses={
        400: {"description": "Невалидный URL"},
        409: {"description": "Алиас уже занят"},
        429: {"description": "Превышен лимит запросов"},
    },
)
async def create_short_link(
    data: LinkCreate,
    session: DbSession,
    current_user: OptionalUser,
) -> Link:
    """
    Создать короткую ссылку для длинного URL.

    - **original**: Оригинальный URL (обязательно)
    - **alias**: Пользовательский алиас (опционально)
    - **expired_at**: Время жизни в минутах (опционально)
    """
    try:
        link = await link_crud.create_link(
            session=session,
            original=str(data.original),
            alias=data.alias,
            expired_at=data.expired_at,
            owner_id=current_user.id if current_user else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return link


@router.get(
    "/{short_code}/info",
    response_model=LinkResponse,
    summary="Получить информацию о ссылке",
)
async def get_link_info(
    short_code: str,
    session: DbSession,
) -> Link:
    """Получить информацию о ссылке по короткому коду."""
    # Сначала пробуем найти по короткому коду
    link = await link_crud.get_by_short_code(session, short_code)

    # Если не найдено, пробуем найти по алиасу
    if not link:
        link = await link_crud.get_by_alias(session, short_code)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Link with short code '{short_code}' not found",
        )

    return link


@router.delete(
    "/{short_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить ссылку",
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Нет прав на удаление"},
        404: {"description": "Ссылка не найдена"},
    },
)
async def delete_short_link(
    short_code: str,
    session: DbSession,
    current_user: RequiredUser,
) -> None:
    """Удалить ссылку (мягкое удаление)."""
    link = await link_crud.get_by_short_code(session, short_code)

    if not link:
        link = await link_crud.get_by_alias(session, short_code)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Link with short code '{short_code}' not found",
        )

    # Проверяем владельца
    if not is_owner(link, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this link",
        )

    await link_crud.delete_link(session, link)


@router.put(
    "/{short_code}",
    response_model=LinkResponse,
    summary="Обновить ссылку",
    responses={
        400: {"description": "Невалидные данные"},
        401: {"description": "Не авторизован"},
        403: {"description": "Нет прав на редактирование"},
        404: {"description": "Ссылка не найдена"},
    },
)
async def edit_short_link(
    short_code: str,
    data: LinkUpdate,
    session: DbSession,
    current_user: RequiredUser,
) -> Link:
    """
    Обновить ссылку.

    - **original**: Новый оригинальный URL (опционально)
    - **alias**: Новый алиас/короткий код (опционально)
    - **expired_at**: Новое время жизни в минутах (опционально)
    """
    link = await link_crud.get_by_short_code(session, short_code)

    if not link:
        link = await link_crud.get_by_alias(session, short_code)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Link with short code '{short_code}' not found",
        )

    # Проверяем владельца
    if not is_owner(link, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update this link",
        )

    try:
        return await link_crud.update_link(
            session=session,
            link=link,
            original=str(data.original) if data.original else None,
            alias=data.alias,
            expired_at=data.expired_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{short_code}/stats",
    summary="Получить статистику ссылки",
    responses={
        404: {"description": "Ссылка не найдена"},
    },
)
async def get_stats(
    short_code: str,
    session: DbSession,
) -> dict:
    """Получить статистику по ссылке."""
    link = await link_crud.get_by_short_code(session, short_code)

    if not link:
        link = await link_crud.get_by_alias(session, short_code)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Link with short code '{short_code}' not found",
        )

    return await link_crud.get_stats(link)


@router.get(
    "/expired/history",
    response_model=list[LinkResponse],
    summary="История истекших ссылок",
)
async def get_expired_links(
    session: DbSession,
    current_user: RequiredUser,
    limit: int = 50,
) -> list[Link]:
    """Получить список истекших ссылок текущего пользователя."""
    links = await link_crud.get_expired_links(session, limit)
    return [link for link in links if link.owner_id == current_user.id]


@router.post(
    "/cleanup/unused",
    summary="Удалить неиспользуемые ссылки",
    responses={
        401: {"description": "Не авторизован"},
    },
)
async def cleanup_unused_links(
    session: DbSession,
    current_user: RequiredUser,
    days: int = 30,
) -> dict:
    """
    Удалить неиспользуемые ссылки текущего пользователя.
    
    - **days**: Количество дней без активности (по умолчанию 30)
    """
    from sqlalchemy import select
    links = await link_crud.get_unused_links(session, days, limit=1000)
    
    # Фильтруем только ссылки текущего пользователя
    user_links = [link for link in links if link.owner_id == current_user.id]
    
    deleted_count = 0
    for link in user_links:
        await link_crud.delete_link(session, link)
        deleted_count += 1
    
    return {
        "deleted_count": deleted_count,
        "days_threshold": days,
    }


@router.post(
    "/{short_code}/tags/{tag_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Добавить тег к ссылке",
    responses={
        404: {"description": "Ссылка или тег не найдены"},
    },
)
async def add_tag_to_link(
    short_code: str,
    tag_id: int,
    session: DbSession,
    current_user: RequiredUser,
) -> dict:
    """Добавить тег к ссылке."""
    link = await link_crud.get_by_short_code(session, short_code)
    if not link:
        link = await link_crud.get_by_alias(session, short_code)
    
    if not link or link.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )
    
    tag = await tag_crud.get_tag_by_id(session, tag_id, owner_id=current_user.id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    await tag_crud.add_tag_to_link(session, link, tag)
    return {"message": "Tag added successfully"}


@router.delete(
    "/{short_code}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить тег у ссылки",
    responses={
        404: {"description": "Ссылка или тег не найдены"},
    },
)
async def remove_tag_from_link(
    short_code: str,
    tag_id: int,
    session: DbSession,
    current_user: RequiredUser,
) -> None:
    """Удалить тег у ссылки."""
    link = await link_crud.get_by_short_code(session, short_code)
    if not link:
        link = await link_crud.get_by_alias(session, short_code)
    
    if not link or link.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )
    
    tag = await tag_crud.get_tag_by_id(session, tag_id, owner_id=current_user.id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    await tag_crud.remove_tag_from_link(session, link, tag)
