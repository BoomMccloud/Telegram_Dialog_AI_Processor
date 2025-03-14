"""Add unread_count, last_message and last_processed_at to dialogs table

Revision ID: 002
Revises: 001
Create Date: 2024-03-14 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add our new columns to dialogs table
    op.add_column('dialogs', sa.Column('unread_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('dialogs', sa.Column('last_message', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    op.add_column('dialogs', sa.Column('last_processed_at', sa.TIMESTAMP(timezone=True), nullable=True))
    
    # Safely rename metadata column to dialog_metadata to avoid SQLAlchemy conflict
    connection = op.get_bind()
    columns = connection.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'dialogs' AND column_name = 'metadata'
    """)).fetchall()
    
    if columns:
        op.alter_column('dialogs', 'metadata', new_column_name='dialog_metadata')
    
    # Update the comment to reflect the changes
    op.execute("""
    COMMENT ON TABLE dialogs IS 'Stores Telegram dialog data including unread count and last message';
    """)

def downgrade() -> None:
    connection = op.get_bind()
    
    # Safely rename dialog_metadata back to metadata if it exists
    columns = connection.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'dialogs' AND column_name = 'dialog_metadata'
    """)).fetchall()
    
    if columns:
        op.alter_column('dialogs', 'dialog_metadata', new_column_name='metadata')
    
    # Safely drop columns if they exist
    for column_name in ['last_processed_at', 'last_message', 'unread_count']:
        columns = connection.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'dialogs' AND column_name = '{column_name}'
        """)).fetchall()
        
        if columns:
            op.drop_column('dialogs', column_name) 