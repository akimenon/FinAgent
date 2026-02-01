"""
Insights Cache Service

File-based cache for LLM-generated deep insights.
Caches analysis results for 24 hours to avoid repeated LLM calls.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path


class InsightsCache:
    """
    File-based cache for deep insights analysis results.

    Structure:
    data/insights_cache/
    ├── AAPL_insights.json
    ├── LCID_insights.json
    └── ...
    """

    # Cache TTL in hours
    DEFAULT_TTL_HOURS = 24

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            base_dir = Path(__file__).parent.parent
            cache_dir = base_dir / "data" / "insights_cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, symbol: str) -> Path:
        """Get the file path for a cached insight."""
        return self.cache_dir / f"{symbol.upper()}_insights.json"

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached insights for a symbol.

        Returns:
            Cached insights if fresh, None if stale or missing
        """
        cache_path = self._get_cache_path(symbol)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)

            # Check if cache is still fresh
            cached_at = datetime.fromisoformat(cached.get("_cachedAt", "2000-01-01"))
            ttl_hours = cached.get("_ttlHours", self.DEFAULT_TTL_HOURS)
            expires_at = cached_at + timedelta(hours=ttl_hours)

            if datetime.now() < expires_at:
                print(f"[INSIGHTS CACHE HIT] {symbol}")
                return cached.get("insights")
            else:
                print(f"[INSIGHTS CACHE STALE] {symbol} - expired {datetime.now() - expires_at} ago")
                return None

        except (json.JSONDecodeError, IOError) as e:
            print(f"[INSIGHTS CACHE ERROR] {symbol} - {e}")
            return None

    def set(self, symbol: str, insights: Dict[str, Any], ttl_hours: int = None) -> None:
        """
        Cache insights for a symbol.

        Args:
            symbol: Stock symbol
            insights: The insights data to cache
            ttl_hours: Optional custom TTL (defaults to 24 hours)
        """
        cache_path = self._get_cache_path(symbol)
        ttl = ttl_hours or self.DEFAULT_TTL_HOURS

        cache_entry = {
            "_cachedAt": datetime.now().isoformat(),
            "_ttlHours": ttl,
            "_symbol": symbol.upper(),
            "insights": insights
        }

        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_entry, f, indent=2, default=str)
            print(f"[INSIGHTS CACHE SET] {symbol} - TTL: {ttl}h")
        except IOError as e:
            print(f"[INSIGHTS CACHE WRITE ERROR] {symbol} - {e}")

    def invalidate(self, symbol: str) -> bool:
        """
        Invalidate (delete) cached insights for a symbol.

        Returns:
            True if cache was deleted, False if it didn't exist
        """
        cache_path = self._get_cache_path(symbol)

        if cache_path.exists():
            cache_path.unlink()
            print(f"[INSIGHTS CACHE INVALIDATED] {symbol}")
            return True
        return False

    def get_status(self, symbol: str) -> Dict[str, Any]:
        """
        Get cache status for a symbol.

        Returns:
            Dict with cache status information
        """
        cache_path = self._get_cache_path(symbol)

        if not cache_path.exists():
            return {
                "symbol": symbol.upper(),
                "cached": False,
                "message": "No cached insights"
            }

        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)

            cached_at = datetime.fromisoformat(cached.get("_cachedAt", "2000-01-01"))
            ttl_hours = cached.get("_ttlHours", self.DEFAULT_TTL_HOURS)
            expires_at = cached_at + timedelta(hours=ttl_hours)
            is_fresh = datetime.now() < expires_at

            return {
                "symbol": symbol.upper(),
                "cached": True,
                "isFresh": is_fresh,
                "cachedAt": cached_at.isoformat(),
                "expiresAt": expires_at.isoformat(),
                "ttlHours": ttl_hours,
                "ageHours": round((datetime.now() - cached_at).total_seconds() / 3600, 1)
            }

        except (json.JSONDecodeError, IOError):
            return {
                "symbol": symbol.upper(),
                "cached": False,
                "message": "Cache file corrupted"
            }

    def clear_all(self) -> int:
        """
        Clear all cached insights.

        Returns:
            Number of cache files deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*_insights.json"):
            cache_file.unlink()
            count += 1

        print(f"[INSIGHTS CACHE CLEARED] Removed {count} cached insights")
        return count


# Singleton instance
insights_cache = InsightsCache()
