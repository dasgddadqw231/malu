-- Add leverage column to bot_instances
ALTER TABLE bot_instances
ADD COLUMN leverage INTEGER NOT NULL DEFAULT 1;
