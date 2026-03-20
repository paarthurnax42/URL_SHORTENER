from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    func,
    ForeignKey,
    Table,
    Column
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Таблица связи многие-ко-многим
link_tags = Table(
    "link_tags",
    Base.metadata,
    Column("link_id", Integer, ForeignKey("links.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Связь с ссылками
    links: Mapped[list["Link"]] = relationship(
        secondary=link_tags,
        back_populates="tags",
    )

    # Связь с владельцем
    owner: Mapped["User | None"] = relationship(back_populates="tags")

    __table_args__ = (
        # Уникальное имя тега в рамках владельца
        # (пользователь не может иметь два тега с одинаковым именем)
    )
