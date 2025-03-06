-- Enable pgcrypto extension for UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- Create enums
CREATE TYPE sessionstatus AS ENUM ('PENDING', 'AUTHENTICATED', 'ERROR', 'EXPIRED');
CREATE TYPE tokentype AS ENUM ('access', 'refresh');
CREATE TYPE dialogtype AS ENUM ('private', 'group', 'channel');
CREATE TYPE processingstatus AS ENUM ('pending_approval', 'approved', 'rejected', 'sent', 'failed');

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create dialogs table
CREATE TABLE IF NOT EXISTS dialogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_dialog_id VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type dialogtype NOT NULL,
    unread_count INTEGER DEFAULT 0,
    last_message JSONB DEFAULT '{}'::jsonb,
    is_processing_enabled BOOLEAN NOT NULL DEFAULT false,
    auto_send_enabled BOOLEAN NOT NULL DEFAULT false,
    last_processed_message_id VARCHAR(255),
    last_processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, telegram_dialog_id)
);

-- Create processed_responses table
CREATE TABLE IF NOT EXISTS processed_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dialog_id UUID NOT NULL REFERENCES dialogs(id) ON DELETE CASCADE,
    last_message_id VARCHAR(255) NOT NULL,
    last_message_timestamp TIMESTAMPTZ NOT NULL,
    suggested_response TEXT NOT NULL,
    edited_response TEXT,
    status processingstatus NOT NULL DEFAULT 'pending_approval',
    model_name VARCHAR(255) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(dialog_id)
);

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status sessionstatus NOT NULL DEFAULT 'PENDING',
    token VARCHAR(500) NOT NULL UNIQUE,
    refresh_token VARCHAR(500) UNIQUE,
    token_type tokentype NOT NULL DEFAULT 'access',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    device_info JSONB DEFAULT '{}'::jsonb
);

-- Create user_selected_models table
CREATE TABLE IF NOT EXISTS user_selected_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model_name VARCHAR(255) NOT NULL,
    system_prompt TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create authentication_data table
CREATE TABLE IF NOT EXISTS authentication_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    telegram_id BIGINT UNIQUE NOT NULL,
    session_data JSONB,
    encrypted_credentials BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_dialogs_user_id ON dialogs(user_id);
CREATE INDEX IF NOT EXISTS idx_dialogs_processing ON dialogs(is_processing_enabled);
CREATE INDEX IF NOT EXISTS idx_processed_responses_status ON processed_responses(status);
CREATE INDEX IF NOT EXISTS idx_processed_responses_dialog_id ON processed_responses(dialog_id);
CREATE INDEX IF NOT EXISTS idx_processed_responses_created_at ON processed_responses(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_auth_data_user_id ON authentication_data(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_data_telegram_id ON authentication_data(telegram_id);
CREATE INDEX IF NOT EXISTS idx_user_selected_models_user_id ON user_selected_models(user_id);

-- Create migrations table
CREATE TABLE IF NOT EXISTS migrations (
    name VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
); 