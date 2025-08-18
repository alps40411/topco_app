"""Remove rating and feedback from daily_reports

Revision ID: c717f1492737
Revises: 1a2b3c4d5e6f
Create Date: 2025-08-15 10:11:38.484421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c717f1492737'
down_revision: Union[str, Sequence[str], None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration is no longer needed as the initial schema is now correct.
    pass


def downgrade() -> None:
    # This migration is no longer needed as the initial schema is now correct.
    pass