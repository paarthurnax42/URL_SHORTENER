from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.crud.user import get_user_by_id
from app.core.security import decode_token
from app.schemas.auth import UserResponse


# HTTP Bearer схема
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(http_bearer)],
) -> Optional[UserResponse]:
    """
    Получить текущего пользователя из JWT токена.
    Возвращает None если токен не предоставлен или невалиден.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        return None

    # Проверяем тип токена
    if payload.get("type") != "access":
        return None

    # Получаем пользователя
    user_id = payload.get("sub")
    if not user_id:
        return None

    async with async_session_maker() as session:
        user = await get_user_by_id(session, int(user_id))
        if not user or not user.is_active:
            return None

        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
        )


async def get_current_user_required(
    current_user: Annotated[Optional[UserResponse], Depends(get_current_user)],
) -> UserResponse:
    """
    Получить текущего пользователя (обязательно).
    Выбрасывает 401 если пользователь не аутентифицирован.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


# Type aliases для удобства
OptionalUser = Annotated[Optional[UserResponse], Depends(get_current_user)]
RequiredUser = Annotated[UserResponse, Depends(get_current_user_required)]
