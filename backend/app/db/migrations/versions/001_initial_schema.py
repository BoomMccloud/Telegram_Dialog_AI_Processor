"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-03-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create enum types first
    op.execute("""
        CREATE TYPE sessionstatus AS ENUM ('active', 'expired', 'revoked');
        CREATE TYPE tokentype AS ENUM ('access', 'refresh');
        CREATE TYPE dialogtype AS ENUM ('user', 'assistant');
        CREATE TYPE processingstatus AS ENUM ('pending', 'processing', 'completed', 'failed');
        CREATE TYPE authmethod AS ENUM ('unknown', 'phone', 'qr', 'telegram', 'password');
    """)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=True),
        sa.Column('username', sa.String(length=32), nullable=True),
        sa.Column('first_name', sa.String(length=64), nullable=True),
        sa.Column('last_name', sa.String(length=64), nullable=True),
        sa.Column('is_temporary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    
    # Create sessions table with auth_method as enum from the start
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),  # Nullable for pre-auth sessions
        sa.Column('status', postgresql.ENUM('active', 'expired', 'revoked', name='sessionstatus'), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('token_type', postgresql.ENUM('access', 'refresh', name='tokentype'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_activity', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('session_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('device_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('auth_method', postgresql.ENUM('unknown', 'phone', 'qr', 'telegram', 'password', name='authmethod'), 
                 nullable=False, server_default='unknown'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create dialogs table
    op.create_table(
        'dialogs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', postgresql.ENUM('user', 'assistant', name='dialogtype'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create processed_responses table
    op.create_table(
        'processed_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dialog_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='processingstatus'), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['dialog_id'], ['dialogs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_selected_models table
    op.create_table(
        'user_selected_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create authentication_data table
    op.create_table(
        'authentication_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('auth_type', sa.String(), nullable=False),
        sa.Column('auth_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'])
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_auth_method', 'sessions', ['auth_method'])
    op.create_index('ix_dialogs_user_id', 'dialogs', ['user_id'])
    op.create_index('ix_processed_responses_dialog_id', 'processed_responses', ['dialog_id'])
    op.create_index('ix_user_selected_models_user_id', 'user_selected_models', ['user_id'])
    op.create_index('ix_authentication_data_user_id', 'authentication_data', ['user_id'])

def downgrade() -> None:
    # Drop tables
    op.drop_table('authentication_data')
    op.drop_table('user_selected_models')
    op.drop_table('processed_responses')
    op.drop_table('dialogs')
    op.drop_table('sessions')
    op.drop_table('users')
    
    # Drop enum types
    op.execute("""
        DROP TYPE IF EXISTS authmethod;
        DROP TYPE IF EXISTS sessionstatus;
        DROP TYPE IF EXISTS tokentype;
        DROP TYPE IF EXISTS dialogtype;
        DROP TYPE IF EXISTS processingstatus;
    """) 