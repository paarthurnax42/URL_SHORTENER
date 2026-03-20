from fastapi import APIRouter, HTTPException, status

from app.schemas.tag import TagCreate, TagResponse
from app.api.v1.dependencies import DbSession
from app.api.v1.auth_dependencies import RequiredUser
from app.crud import tag as tag_crud
from app.crud import link as link_crud
from app.models.tag import Tag

router = APIRouter(prefix="/tags")


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать тег",
    responses={
        400: {"description": "Тег с таким именем уже существует"},
    },
)
async def create_tag(
    data: TagCreate,
    session: DbSession,
    current_user: RequiredUser,
) -> Tag:
    """Создать новый тег."""
    try:
        tag = await tag_crud.create_tag(
            session=session,
            name=data.name.lower(),
            owner_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return tag


@router.get(
    "",
    response_model=list[TagResponse],
    summary="Мои теги",
)
async def get_my_tags(
    session: DbSession,
    current_user: RequiredUser,
) -> list[Tag]:
    """Получить все теги текущего пользователя."""
    return await tag_crud.get_tags(session, owner_id=current_user.id)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить тег",
    responses={
        404: {"description": "Тег не найден"},
    },
)
async def delete_tag(
    tag_id: int,
    session: DbSession,
    current_user: RequiredUser,
) -> None:
    """Удалить тег."""
    tag = await tag_crud.get_tag_by_id(session, tag_id, owner_id=current_user.id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    await tag_crud.delete_tag(session, tag)


@router.get(
    "/{tag_id}/links",
    response_model=list[dict],
    summary="Ссылки с тегом",
)
async def get_links_by_tag(
    tag_id: int,
    session: DbSession,
    current_user: RequiredUser,
) -> list[dict]:
    """Получить все ссылки с данным тегом."""
    tag = await tag_crud.get_tag_by_id(session, tag_id, owner_id=current_user.id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    links = await tag_crud.get_links_by_tag(session, tag)
    return [
        {
            "id": link.id,
            "short": link.short,
            "original": link.original,
            "alias": link.alias,
            "clicks_count": link.clicks_count,
        }
        for link in links
    ]
