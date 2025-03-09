"""add priority column

Revision ID: 0376ed06f4eb
Revises: f231678720fb
Create Date: 2025-03-09 14:11:43.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0376ed06f4eb'
down_revision: Union[str, None] = 'f231678720fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add priority column to dialogs table
    op.add_column('dialogs', sa.Column('priority', sa.Integer(), nullable=False, server_default='0'))
    op.create_index(op.f('ix_dialogs_priority'), 'dialogs', ['priority'], unique=False)


def downgrade() -> None:
    # Remove priority column from dialogs table
    op.drop_index(op.f('ix_dialogs_priority'), table_name='dialogs')
    op.drop_column('dialogs', 'priority') 