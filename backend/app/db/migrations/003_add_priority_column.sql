-- Add priority column to dialogs table
ALTER TABLE dialogs
ADD COLUMN priority INTEGER NOT NULL DEFAULT 0; 