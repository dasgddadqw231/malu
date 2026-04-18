-- Manual Datasets: named collections of trades for signature reference
CREATE TABLE IF NOT EXISTS manual_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    trade_ids UUID[] NOT NULL DEFAULT '{}',
    auto_sync BOOLEAN NOT NULL DEFAULT FALSE,
    sync_symbol TEXT,
    sync_category TEXT DEFAULT 'linear',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_manual_datasets_created ON manual_datasets(created_at DESC);
