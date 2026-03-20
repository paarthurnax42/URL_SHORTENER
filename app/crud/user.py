from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import get_password_hash, verify_password


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> User | None:

    result = await session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> User | None:

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User:
    existing = await get_user_by_email(session, email)
    if existing:
        raise ValueError(f"User with email '{email}' already exists")

    user = User(
        email=email,
        password_hash=get_password_hash(password),
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    user = await get_user_by_email(session, email)
    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    return user
