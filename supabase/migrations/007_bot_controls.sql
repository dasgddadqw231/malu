-- Bot Controls: risk management, scheduling, and position sizing overrides
-- These are bot-level operational settings independent of strategy_config (signature)

ALTER TABLE bot_instances
ADD COLUMN bot_controls JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN bot_instances.bot_controls IS
'Bot-level operational controls: risk limits, schedule, sizing overrides.
Example:
{
  "risk": {
    "max_daily_loss_pct": 5.0,
    "max_consecutive_losses": 3,
    "max_single_loss_pct": 2.0
  },
  "schedule": {
    "trading_hours": [{"start": "08:00", "end": "22:00"}],
    "cooldown_seconds": 60,
    "max_trades_per_day": 10
  },
  "sizing": {
    "mode": "pct",
    "fixed_amount_usd": null,
    "compound": false
  }
}';
