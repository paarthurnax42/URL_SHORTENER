from datetime import datetime

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserCreate(BaseModel):
    """Схема регистрации пользователя."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "secure123",
                }
            ]
        }
    )

    email: EmailStr = Field(..., description="Email адрес")
    password: str = Field(..., min_length=6, max_length=72, description="Пароль (6-72 символа)")


class UserLogin(BaseModel):
    """Схема входа пользователя."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "securepassword123",
                }
            ]
        }
    )

    email: EmailStr = Field(..., description="Email адрес")
    password: str = Field(..., description="Пароль")


class Token(BaseModel):
    """Схема ответа с токеном."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Схема ответа с информацией о пользователе."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    created_at: datetime
