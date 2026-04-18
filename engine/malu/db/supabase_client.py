from __future__ import annotations

from supabase import create_client, Client

from malu.config import Settings


_client: Client | None = None


def get_supabase(settings: Settings | None = None) -> Client:
    global _client
    if _client is None:
        if settings is None:
            settings = Settings()
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client
