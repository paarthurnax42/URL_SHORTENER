from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import UserCreate, UserLogin, Token, UserResponse
from app.api.v1.dependencies import DbSession
from app.crud import user as user_crud
from app.core.security import create_access_token
from app.api.v1.auth_dependencies import get_current_user_required, RequiredUser

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    responses={
        400: {"description": "Невалидный email или пароль"},
        409: {"description": "Email уже зарегистрирован"},
    },
)
async def register(
    data: UserCreate,
    session: DbSession,
) -> dict:
    """
    Зарегистрировать нового пользователя.

    - **email**: Email адрес (должен быть уникальным)
    - **password**: Пароль (минимум 6 символов)
    """
    try:
        user = await user_crud.create_user(
            session=session,
            email=data.email,
            password=data.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Создаём токен
    access_token = create_access_token(subject=user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post(
    "/login",
    response_model=Token,
    summary="Вход пользователя",
    responses={
        401: {"description": "Неверный email или пароль"},
    },
)
async def login(
    data: UserLogin,
    session: DbSession,
) -> dict:
    """
    Войти в систему.

    - **email**: Email адрес
    - **password**: Пароль
    """
    user = await user_crud.authenticate_user(
        session=session,
        email=data.email,
        password=data.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Создаём токен
    access_token = create_access_token(subject=user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Информация о текущем пользователе",
)
async def get_me(
    current_user: RequiredUser,
) -> UserResponse:
    """Получить информацию о текущем пользователе."""
    return current_user
