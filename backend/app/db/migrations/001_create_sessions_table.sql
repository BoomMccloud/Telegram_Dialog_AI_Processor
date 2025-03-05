-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'authenticated', 'error', 'expired')),
    token VARCHAR(500) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Indexes for common queries
    CONSTRAINT sessions_token_unique UNIQUE (token)
); 