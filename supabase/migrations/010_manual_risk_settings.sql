-- Manual trading risk management settings (single-user, single row)
CREATE TABLE IF NOT EXISTS manual_risk_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enabled BOOLEAN NOT NULL DEFAULT false,
    -- Position-level rules
    max_loss_pct NUMERIC(6,2) DEFAULT 5.0,          -- auto SL at X% loss per position
    max_profit_pct NUMERIC(6,2) DEFAULT 0,           -- auto TP at X% gain (0 = disabled)
    -- Daily aggregate rules
    max_daily_loss_usd NUMERIC(20,2) DEFAULT 0,      -- kill all if daily loss > $X (0 = disabled)
    max_daily_trades INT DEFAULT 0,                   -- max trades per day (0 = unlimited)
    -- Position sizing rules
    max_position_pct NUMERIC(6,2) DEFAULT 0,          -- max position as % of equity (0 = disabled)
    max_leverage INT DEFAULT 0,                        -- max allowed leverage (0 = unlimited)
    -- Notifications
    notify_on_close BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Insert default row
INSERT INTO manual_risk_settings (enabled) VALUES (false);
