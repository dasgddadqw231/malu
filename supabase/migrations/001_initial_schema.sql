-- Malu Phase 1: Initial Schema
-- Single user, multi-bot trading system

-- API key storage (single user, but extensible)
CREATE TABLE user_api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange    TEXT NOT NULL DEFAULT 'bybit',
    api_key     TEXT NOT NULL,
    api_secret  TEXT NOT NULL,
    label       TEXT,
    is_testnet  BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bot instances
CREATE TABLE bot_instances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id      UUID REFERENCES user_api_keys(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    bot_tag         TEXT NOT NULL UNIQUE,
    status          TEXT NOT NULL DEFAULT 'stopped'
                    CHECK (status IN ('stopped', 'running', 'waiting', 'in_position', 'judging', 'acting', 'defending', 'killed', 'error')),
    symbol          TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'linear'
                    CHECK (category IN ('linear', 'spot', 'inverse')),
    seed_budget     NUMERIC(20,8) NOT NULL,
    strategy_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    cycle_interval  NUMERIC(6,2) NOT NULL DEFAULT 5.0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trade history
CREATE TABLE trade_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id          UUID REFERENCES bot_instances(id) ON DELETE CASCADE,
    order_link_id   TEXT NOT NULL,
    bybit_order_id  TEXT,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL CHECK (side IN ('Buy', 'Sell')),
    order_type      TEXT NOT NULL CHECK (order_type IN ('Market', 'Limit')),
    qty             NUMERIC(20,8) NOT NULL,
    price           NUMERIC(20,8),
    status          TEXT NOT NULL DEFAULT 'New'
                    CHECK (status IN ('New', 'Filled', 'PartiallyFilled', 'Cancelled', 'Rejected')),
    pnl             NUMERIC(20,8),
    fee             NUMERIC(20,8),
    raw_response    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    filled_at       TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_bot_instances_status ON bot_instances(status);
CREATE INDEX idx_trade_history_bot_id ON trade_history(bot_id);
CREATE INDEX idx_trade_history_order_link_id ON trade_history(order_link_id);
CREATE INDEX idx_trade_history_created_at ON trade_history(created_at DESC);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bot_instances_updated_at
    BEFORE UPDATE ON bot_instances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Enable realtime for dashboard
ALTER PUBLICATION supabase_realtime ADD TABLE bot_instances;
ALTER PUBLICATION supabase_realtime ADD TABLE trade_history;
