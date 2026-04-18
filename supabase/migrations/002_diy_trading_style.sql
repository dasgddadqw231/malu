-- DIY Trading Style: user's own trade history → custom bot strategy

-- Human trades imported from exchange (non-bot trades)
CREATE TABLE diy_trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id      UUID REFERENCES user_api_keys(id) ON DELETE CASCADE,
    bybit_order_id  TEXT NOT NULL UNIQUE,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL CHECK (side IN ('Buy', 'Sell')),
    order_type      TEXT NOT NULL,
    qty             NUMERIC(20,8) NOT NULL,
    avg_price       NUMERIC(20,8),
    pnl             NUMERIC(20,8),
    fee             NUMERIC(20,8),
    leverage        TEXT DEFAULT '1',
    -- Pair tracking: groups entry + exit as one "trade"
    trade_pair_id   UUID,
    pair_role       TEXT CHECK (pair_role IN ('entry', 'exit')),
    -- User annotation
    rationale       TEXT,
    tags            TEXT[] DEFAULT '{}',
    -- Timestamps
    filled_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Custom trading styles derived from annotated trades
CREATE TABLE diy_styles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT,
    -- Source trades used to build this style
    source_trade_ids UUID[] DEFAULT '{}',
    -- Generated strategy_config (same schema as bot_instances.strategy_config)
    strategy_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Extracted rules in human-readable form
    rules           JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Stats from source trades
    stats           JSONB DEFAULT '{}'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_diy_trades_symbol ON diy_trades(symbol);
CREATE INDEX idx_diy_trades_filled_at ON diy_trades(filled_at DESC);
CREATE INDEX idx_diy_trades_trade_pair_id ON diy_trades(trade_pair_id);
CREATE INDEX idx_diy_styles_is_active ON diy_styles(is_active);

-- Auto-update updated_at for diy_styles
CREATE TRIGGER diy_styles_updated_at
    BEFORE UPDATE ON diy_styles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Enable realtime
ALTER PUBLICATION supabase_realtime ADD TABLE diy_trades;
ALTER PUBLICATION supabase_realtime ADD TABLE diy_styles;
