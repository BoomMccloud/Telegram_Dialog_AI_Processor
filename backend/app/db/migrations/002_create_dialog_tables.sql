-- Create dialogs table
CREATE TABLE IF NOT EXISTS dialogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_dialog_id VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    unread_count INTEGER DEFAULT 0,
    last_message JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    
    CONSTRAINT valid_dialog_type CHECK (type IN ('private', 'group', 'channel'))
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_message_id VARCHAR NOT NULL,
    dialog_id UUID NOT NULL REFERENCES dialogs(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    sender_id VARCHAR NOT NULL,
    sender_name VARCHAR NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    is_outgoing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(telegram_message_id, dialog_id)
);

-- Create enum type for processing status
CREATE TYPE processing_status AS ENUM ('pending', 'processing', 'completed', 'error');

-- Create processing_results table
CREATE TABLE IF NOT EXISTS processing_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    model_name VARCHAR NOT NULL,
    status processing_status NOT NULL DEFAULT 'pending',
    result JSONB,
    error VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT valid_status CHECK (
        (status = 'completed' AND result IS NOT NULL AND error IS NULL) OR
        (status = 'error' AND error IS NOT NULL AND result IS NULL) OR
        (status IN ('pending', 'processing'))
    )
);

-- Create indexes for performance
CREATE INDEX idx_messages_dialog_id ON messages(dialog_id);
CREATE INDEX idx_processing_results_message_id ON processing_results(message_id);
CREATE INDEX idx_processing_results_status ON processing_results(status);
CREATE INDEX idx_dialogs_telegram_id ON dialogs(telegram_dialog_id); 