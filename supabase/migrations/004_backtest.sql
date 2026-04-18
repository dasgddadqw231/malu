-- Backtest runs and trade results
CREATE TABLE backtest_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol          TEXT NOT NULL,
    interval        TEXT NOT NULL DEFAULT '15',
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    initial_capital NUMERIC(20,8) NOT NULL,
    strategy_config JSONB NOT NULL DEFAULT '{}',
    slippage_bps    INT NOT NULL DEFAULT 5,
    fee_rate        NUMERIC(10,6) NOT NULL DEFAULT 0.000550,
    -- Results (filled when completed)
    total_pnl       NUMERIC(20,8),
    total_fees      NUMERIC(20,8),
    total_funding   NUMERIC(20,8),
    net_pnl         NUMERIC(20,8),
    win_rate        NUMERIC(6,2),
    max_drawdown    NUMERIC(6,2),
    sharpe_ratio    NUMERIC(10,4),
    total_trades    INT,
    equity_curve    JSONB,
    status          TEXT NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'completed', 'failed')),
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE backtest_trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    entry_time      TIMESTAMPTZ NOT NULL,
    exit_time       TIMESTAMPTZ NOT NULL,
    side            TEXT NOT NULL,
    entry_price     NUMERIC(20,8) NOT NULL,
    exit_price      NUMERIC(20,8) NOT NULL,
    qty             NUMERIC(20,8) NOT NULL,
    pnl             NUMERIC(20,8) NOT NULL,
    fee             NUMERIC(20,8) NOT NULL,
    funding_paid    NUMERIC(20,8) NOT NULL DEFAULT 0,
    exit_reason     TEXT NOT NULL
);

CREATE INDEX idx_backtest_runs_created ON backtest_runs(created_at DESC);
CREATE INDEX idx_backtest_trades_run ON backtest_trades(run_id);
