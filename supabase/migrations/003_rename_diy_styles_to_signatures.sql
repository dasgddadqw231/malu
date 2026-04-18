-- Rename diy_styles → signatures

ALTER TABLE diy_styles RENAME TO signatures;

-- Rename indexes
ALTER INDEX idx_diy_styles_is_active RENAME TO idx_signatures_is_active;

-- Rename trigger
DROP TRIGGER IF EXISTS diy_styles_updated_at ON signatures;
CREATE TRIGGER signatures_updated_at
    BEFORE UPDATE ON signatures
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
