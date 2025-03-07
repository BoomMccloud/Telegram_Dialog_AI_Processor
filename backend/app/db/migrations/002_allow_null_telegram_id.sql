-- Allow null telegram_id in users table for temporary users
ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL; 