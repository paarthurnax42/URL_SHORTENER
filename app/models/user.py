from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Boolean,
    func,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Связь с ссылками
    links: Mapped[list["Link"]] = relationship(back_populates="owner")

    # Связь с тегами (используем строку для lazy evaluation)
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        back_populates="owner",
        lazy="select",
    )
