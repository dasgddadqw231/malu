-- Comprehensive schema sync: ensure all columns used by the engine exist
-- Safe to run multiple times (uses IF NOT EXISTS)

-- bot_instances: leverage column
ALTER TABLE bot_instances
ADD COLUMN IF NOT EXISTS leverage INTEGER NOT NULL DEFAULT 1;

-- bot_instances: bot_controls column
ALTER TABLE bot_instances
ADD COLUMN IF NOT EXISTS bot_controls JSONB NOT NULL DEFAULT '{}'::jsonb;

-- manual_datasets: auto-update trigger for updated_at (was missing in 005)
DROP TRIGGER IF EXISTS manual_datasets_updated_at ON manual_datasets;
CREATE TRIGGER manual_datasets_updated_at
    BEFORE UPDATE ON manual_datasets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
