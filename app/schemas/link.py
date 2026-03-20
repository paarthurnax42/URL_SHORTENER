from datetime import datetime

from pydantic import BaseModel, Field, AnyHttpUrl, ConfigDict


class LinkCreate(BaseModel):
    """Схема для создания короткой ссылки."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "original": "https://example.com/very/long/url",
                    "alias": "my-link",
                    "expired_at": 60,  # минут
                }
            ]
        }
    )

    original: AnyHttpUrl = Field(..., description="Оригинальный URL")
    alias: str | None = Field(None, min_length=1, max_length=100, description="Пользовательский алиас")
    expired_at: int | None = Field(None, ge=1, description="Время жизни в минутах")


class LinkUpdate(BaseModel):
    """Схема для обновления ссылки."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "original": "https://new-example.com/url",
                    "alias": "new-short-code",
                    "expired_at": 120,
                }
            ]
        }
    )

    original: AnyHttpUrl | None = Field(None, description="Новый оригинальный URL")
    alias: str | None = Field(None, min_length=1, max_length=100, description="Новый алиас (короткий код)")
    expired_at: int | None = Field(None, ge=1, description="Новое время жизни в минутах")


class LinkResponse(BaseModel):
    """Базовая схема ответа со ссылкой."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    original: str
    short: str
    alias: str | None = None
    created_at: datetime
    expired_at: datetime | None = None
    last_used_at: datetime | None = None
    clicks_count: int = 0
    is_active: bool = True
