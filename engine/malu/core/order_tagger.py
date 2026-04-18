from __future__ import annotations

import secrets
import time


class OrderTagger:
    """Generates unique orderLinkId values prefixed with the bot's tag.

    Format: {bot_tag}_{timestamp_hex}_{random4}
    Example: b03_68a1f2c0_x9k2

    Bybit max orderLinkId length is 36 characters.
    """

    def __init__(self, bot_tag: str):
        if not bot_tag or len(bot_tag) > 6:
            raise ValueError(f"bot_tag must be 1-6 chars, got '{bot_tag}'")
        self.bot_tag = bot_tag

    def generate(self) -> str:
        ts_hex = format(int(time.time()), "x")
        rand = secrets.token_hex(2)  # 4 hex chars
        link_id = f"{self.bot_tag}_{ts_hex}_{rand}"
        if len(link_id) > 36:
            raise ValueError(f"orderLinkId too long: {link_id}")
        return link_id

    @staticmethod
    def extract_bot_tag(order_link_id: str) -> str:
        """Extract bot_tag from an orderLinkId."""
        parts = order_link_id.split("_", 1)
        return parts[0] if parts else ""
