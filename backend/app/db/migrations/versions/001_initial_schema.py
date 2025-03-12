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
    # Create tables with enums
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
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
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),  # Nullable for pre-auth sessions
        sa.Column('status', sa.Enum('PENDING', 'AUTHENTICATED', 'ERROR', 'EXPIRED', name='session_status'), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('token_type', sa.Enum('ACCESS', 'REFRESH', name='token_type'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_activity', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('session_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('device_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('auth_method', sa.String(length=16), nullable=False, server_default='unknown'),  # 'unknown', 'phone', 'qr', 'telegram', 'password'
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create dialogs table
    op.create_table(
        'dialogs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_dialog_id', sa.String(length=255), nullable=False),
        sa.Column('type', sa.Enum('PRIVATE', 'GROUP', 'CHANNEL', name='dialog_type'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('is_processing_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_send_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_processed_message_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'telegram_dialog_id', name='uq_user_dialog')
    )
    
    # Create processed_responses table
    op.create_table(
        'processed_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('dialog_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('last_message_id', sa.String(length=255), nullable=False),
        sa.Column('last_message_timestamp', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('suggested_response', sa.Text(), nullable=False),
        sa.Column('edited_response', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'SENT', 'FAILED', name='processing_status'), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['dialog_id'], ['dialogs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_selected_models table
    op.create_table(
        'user_selected_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_id', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'model_id', name='uq_user_model')
    )
    
    # Create background_tasks table
    op.create_table(
        'background_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('task_type', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', name='task_status'), nullable=False),
        sa.Column('priority', sa.Enum('LOW', 'NORMAL', 'HIGH', name='task_priority'), nullable=False, server_default='NORMAL'),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    # Drop tables
    op.drop_table('background_tasks')
    op.drop_table('user_selected_models')
    op.drop_table('processed_responses')
    op.drop_table('dialogs')
    op.drop_table('sessions')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS task_priority')
    op.execute('DROP TYPE IF EXISTS task_status')
    op.execute('DROP TYPE IF EXISTS processing_status')
    op.execute('DROP TYPE IF EXISTS dialog_type')
    op.execute('DROP TYPE IF EXISTS token_type')
    op.execute('DROP TYPE IF EXISTS session_status') 