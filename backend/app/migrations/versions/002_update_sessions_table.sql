-- Update sessions table for enhanced session management
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS refresh_token VARCHAR(500) UNIQUE,
ADD COLUMN IF NOT EXISTS token_type VARCHAR(20) NOT NULL DEFAULT 'access',
ADD COLUMN IF NOT EXISTS last_activity TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS device_info JSONB DEFAULT '{}'::jsonb;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_sessions_token_type ON sessions(token_type);

-- Down migration
-- ALTER TABLE sessions
--   DROP COLUMN refresh_token,
--   DROP COLUMN token_type,
--   DROP COLUMN last_activity,
--   DROP COLUMN device_info;
-- DROP INDEX IF EXISTS idx_sessions_last_activity;
-- DROP INDEX IF EXISTS idx_sessions_token_type; 