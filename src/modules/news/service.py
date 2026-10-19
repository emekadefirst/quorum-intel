"""News service: cached wrapper around build_news_digest.

Digest is relatively expensive (RSS fetches + parsing) so we cache it for 10 minutes.
"""

from __future__ import annotations

import time
from typing import Any

from src.news.digest import abuild_news_digest

_CACHE: dict[tuple[float, int], tuple[float, dict[str, Any]]] = {}
_TTL = 600  # 10 minutes


class NewsService:
    @classmethod
    async def get_digest(
        cls, lookback_hours: float = 48, max_items: int = 25
    ) -> dict[str, Any]:
        key = (lookback_hours, max_items)
        now = time.monotonic()
        hit = _CACHE.get(key)
        if hit and now - hit[0] < _TTL:
            return hit[1]

        digest = await abuild_news_digest(
            lookback_hours=lookback_hours, max_items=max_items
        )
        _CACHE[key] = (now, digest)
        return digest
