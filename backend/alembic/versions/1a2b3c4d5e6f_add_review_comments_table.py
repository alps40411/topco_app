"""Add review_comments table

Revision ID: 1a2b3c4d5e6f
Revises: f0e1d2c3b4a5
Create Date: 2025-08-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = 'f0e1d2c3b4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('review_comments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('report_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('parent_comment_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['parent_comment_id'], ['review_comments.id'], ),
    sa.ForeignKeyConstraint(['report_id'], ['daily_reports.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_review_comments_id'), 'review_comments', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_review_comments_id'), table_name='review_comments')
    op.drop_table('review_comments')
