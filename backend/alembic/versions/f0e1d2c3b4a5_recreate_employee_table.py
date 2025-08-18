"""Recreate employee table

Revision ID: f0e1d2c3b4a5
Revises: dbc2cea2c5b9
Create Date: 2025-08-14 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0e1d2c3b4a5'
down_revision: Union[str, Sequence[str], None] = 'dbc2cea2c5b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration has been consolidated into dbc2cea2c5b9_create_initial_tables.py
    pass


def downgrade() -> None:
    # This migration has been consolidated into dbc2cea2c5b9_create_initial_tables.py
    pass