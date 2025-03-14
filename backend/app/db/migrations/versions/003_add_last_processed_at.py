"""Add last_processed_at column to dialogs table

Revision ID: 003
Revises: 002
Create Date: 2024-03-14 15:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if column exists first to avoid errors
    connection = op.get_bind()
    columns = connection.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'dialogs' AND column_name = 'last_processed_at'
    """)).fetchall()
    
    if not columns:
        # Add last_processed_at column
        op.add_column('dialogs', sa.Column('last_processed_at', sa.TIMESTAMP(timezone=True), nullable=True))
        
        # If last_processed_message_id has data, set last_processed_at to current time
        op.execute("""
        UPDATE dialogs 
        SET last_processed_at = now() 
        WHERE last_processed_message_id IS NOT NULL
        """)

def downgrade() -> None:
    # Check if column exists first to avoid errors
    connection = op.get_bind()
    columns = connection.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'dialogs' AND column_name = 'last_processed_at'
    """)).fetchall()
    
    if columns:
        op.drop_column('dialogs', 'last_processed_at') 