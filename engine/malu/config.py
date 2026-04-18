from pathlib import Path

from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Bybit
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    bybit_testnet: bool = True

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Gemini LLM
    gemini_api_key: str = ""

    # Engine
    bot_cycle_interval_sec: float = 5.0
    reconcile_interval_sec: float = 30.0
    rate_limit_per_second: int = 10

    # WebSocket
    ws_enabled: bool = True
    ws_kline_intervals: str = "1,5,15"  # comma-separated

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "env_file_encoding": "utf-8"}
