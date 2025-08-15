"""Add rating to review_comments table

Revision ID: 20250815_110251
Revises: c717f1492737
Create Date: 2025-08-15T11:02:51.363473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250815_110251'
down_revision: Union[str, Sequence[str], None] = 'c717f1492737'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add rating column to review_comments table."""
    op.add_column('review_comments', sa.Column('rating', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove rating column from review_comments table."""
    op.drop_column('review_comments', 'rating')
