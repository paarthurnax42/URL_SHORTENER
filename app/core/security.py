from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import hashlib
import os

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверить пароль против хеша."""
    # Формат хеша: salt$hash
    try:
        salt, hash_value = hashed_password.split('$')
        new_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000)
        return new_hash.hex() == hash_value
    except (ValueError, AttributeError):
        return False


def get_password_hash(password: str) -> str:
    """Создать хеш пароля."""
    salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${pwd_hash.hex()}"


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> str:
    """Создать JWT access токен."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
    }

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """Декодировать JWT токен."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
