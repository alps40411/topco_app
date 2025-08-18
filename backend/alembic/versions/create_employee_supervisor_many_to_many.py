"""Create employee supervisor many-to-many relationship

Revision ID: employee_supervisor_m2m
Revises: f0e1d2c3b4a5_recreate_employee_table
Create Date: 2025-08-18 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'employee_supervisor_m2m'
down_revision = '20250815_110251'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create employee_supervisors many-to-many table
    op.create_table('employee_supervisors',
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('supervisor_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supervisor_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('employee_id', 'supervisor_id')
    )
    
    # Create indexes for better performance
    op.create_index('ix_employee_supervisors_employee_id', 'employee_supervisors', ['employee_id'])
    op.create_index('ix_employee_supervisors_supervisor_id', 'employee_supervisors', ['supervisor_id'])


def downgrade() -> None:
    op.drop_index('ix_employee_supervisors_supervisor_id', table_name='employee_supervisors')
    op.drop_index('ix_employee_supervisors_employee_id', table_name='employee_supervisors')
    op.drop_table('employee_supervisors')