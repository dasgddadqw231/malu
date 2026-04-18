-- Add conversation history to signatures for iterative refinement
ALTER TABLE signatures ADD COLUMN IF NOT EXISTS messages JSONB DEFAULT '[]'::jsonb;
ALTER TABLE signatures ADD COLUMN IF NOT EXISTS dataset_id UUID REFERENCES manual_datasets(id);
