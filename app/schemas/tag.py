from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class TagCreate(BaseModel):
    """Схема создания тега."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "project1"},
                {"name": "social-media"},
            ]
        }
    )

    name: str = Field(..., min_length=1, max_length=50, description="Название тега")


class TagResponse(BaseModel):
    """Схема ответа с тегом."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    owner_id: int | None = None
