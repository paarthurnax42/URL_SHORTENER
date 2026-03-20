from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    func,
    Index,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    original: Mapped[str] = mapped_column(String(2048), nullable=False)
    short: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    alias: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    clicks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Связь с тегами (многие-ко-многим)
    tags: Mapped[list["Tag"]] = relationship(
        secondary="link_tags",
        back_populates="links",
    )

    # Связь с владельцем
    owner: Mapped["User | None"] = relationship(back_populates="links")

    __table_args__ = (
        Index("ix_links_short", "short"),
        Index("ix_links_original", "original"),
        Index("ix_links_deleted_at", "deleted_at"),
    )
