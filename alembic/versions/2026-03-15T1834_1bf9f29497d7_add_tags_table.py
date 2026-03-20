"""add tags table

Revision ID: 1bf9f29497d7
Revises: 3162a24e6366
Create Date: 2026-03-15 18:34:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bf9f29497d7'
down_revision: Union[str, Sequence[str], None] = '3162a24e6366'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создаём таблицу tags
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=False)
    op.create_index(op.f('ix_tags_owner_id'), 'tags', ['owner_id'], unique=False)
    
    # Создаём таблицу связи link_tags
    op.create_table(
        'link_tags',
        sa.Column('link_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['link_id'], ['links.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('link_id', 'tag_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('link_tags')
    op.drop_index(op.f('ix_tags_owner_id'), table_name='tags')
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    op.drop_table('tags')
