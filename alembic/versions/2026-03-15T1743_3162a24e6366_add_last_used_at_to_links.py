"""add last_used_at to links

Revision ID: 3162a24e6366
Revises: e2baa2b8f7f4
Create Date: 2026-03-15 17:43:49.170342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3162a24e6366'
down_revision: Union[str, Sequence[str], None] = 'e2baa2b8f7f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "links",
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Дата последнего перехода по ссылке",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("links", "last_used_at")
