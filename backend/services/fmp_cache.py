"""
FMP File-Based Cache Service

Stores API responses as JSON files to minimize API calls.
- Daily data (price/profile): Refreshes once per day
- Quarterly data (financials): Refreshes every 90 days
- Annual data (segments): Refreshes every 365 days
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

from services.fmp_service import fmp_service


class FMPCache:
    """
    File-based cache for FMP API responses.

    Structure:
    data/fmp_cache/
    ├── AAPL/
    │   ├── profile.json
    │   ├── income_quarterly.json
    │   └── ...
    └── _index.json
    """

    # TTL (Time To Live) in days for each endpoint type
    TTL_DAYS = {
        # Daily - stock price changes
        "profile": 1,
        "price_history": 1,
        "earnings_calendar": 1,  # Check daily for upcoming earnings

        # Quarterly - financial statements
        "income_quarterly": 90,
        "income_annual": 90,
        "balance_sheet": 90,
        "cash_flow": 90,
        "earnings": 90,
        "ratios": 90,
        "key_metrics": 90,
        "analyst_estimates": 30,  # Estimates update more frequently

        # Analyst data - updates frequently
        "price_target_consensus": 1,  # Price targets can change daily
        "price_target_summary": 1,
        "analyst_grades": 1,  # Upgrades/downgrades happen frequently
        "analyst_grades_consensus": 1,

        # Annual - segment data
        "product_segments": 365,
        "geo_segments": 365,

        # Search results - short cache
        "search": 7,

        # News & trading activity - refresh frequently
        "stock_news": 0.25,  # 6 hours
        "insider_trading": 1,
        "senate_trades": 1,
    }

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            # Default to backend/data/fmp_cache
            base_dir = Path(__file__).parent.parent
            cache_dir = base_dir / "data" / "fmp_cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fmp = fmp_service

    def _get_file_path(self, symbol: str, endpoint: str) -> Path:
        """Get the file path for a cached endpoint."""
        symbol_dir = self.cache_dir / symbol.upper()
        symbol_dir.mkdir(exist_ok=True)
        return symbol_dir / f"{endpoint}.json"

    def _is_fresh(self, cached_data: Dict, endpoint: str) -> bool:
        """Check if cached data is still fresh based on TTL."""
        if not cached_data:
            return False

        fetched_at = cached_data.get("fetched_at")
        if not fetched_at:
            return False

        fetched_time = datetime.fromisoformat(fetched_at)
        ttl_days = self.TTL_DAYS.get(endpoint, 1)
        expires_at = fetched_time + timedelta(days=ttl_days)

        return datetime.now() < expires_at

    def _read_cache(self, symbol: str, endpoint: str) -> Optional[Dict]:
        """Read cached data from file."""
        file_path = self._get_file_path(symbol, endpoint)

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _write_cache(self, symbol: str, endpoint: str, data: Any) -> None:
        """Write data to cache file."""
        file_path = self._get_file_path(symbol, endpoint)

        cache_entry = {
            "symbol": symbol.upper(),
            "endpoint": endpoint,
            "fetched_at": datetime.now().isoformat(),
            "ttl_days": self.TTL_DAYS.get(endpoint, 1),
            "data": data
        }

        with open(file_path, 'w') as f:
            json.dump(cache_entry, f, indent=2, default=str)

    async def get(self, endpoint: str, symbol: str, force_refresh: bool = False, **kwargs) -> Any:
        """
        Get data from cache or fetch from API.

        Args:
            endpoint: The endpoint name (e.g., 'profile', 'income_quarterly')
            symbol: Stock symbol
            force_refresh: If True, bypass cache and fetch fresh data
            **kwargs: Additional arguments for the API call

        Returns:
            The data (from cache or API)
        """
        symbol = symbol.upper()

        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = self._read_cache(symbol, endpoint)
            if cached and self._is_fresh(cached, endpoint):
                print(f"[CACHE HIT] {symbol}/{endpoint}")
                return cached["data"]

        # Cache miss or stale - fetch from API
        print(f"[CACHE MISS] {symbol}/{endpoint} - fetching from API")
        try:
            data = await self._fetch_from_api(endpoint, symbol, **kwargs)

            # Save to cache (only if we got valid data)
            if data is not None and not (isinstance(data, dict) and "Error" in str(data)):
                self._write_cache(symbol, endpoint, data)

            return data
        except Exception as e:
            print(f"[CACHE ERROR] {symbol}/{endpoint} - {e}")
            # Return stale cache if available, otherwise None
            if cached:
                print(f"[CACHE STALE] Using stale data for {symbol}/{endpoint}")
                return cached["data"]
            return None

    async def _fetch_from_api(self, endpoint: str, symbol: str, **kwargs) -> Any:
        """Fetch data from FMP API based on endpoint type."""

        endpoint_mapping = {
            "profile": lambda: self.fmp.get_company_profile(symbol),
            "income_quarterly": lambda: self.fmp.get_income_statement(
                symbol, period="quarter", limit=kwargs.get("limit", 5)
            ),
            "income_annual": lambda: self.fmp.get_income_statement(
                symbol, period="annual", limit=kwargs.get("limit", 3)
            ),
            "balance_sheet": lambda: self.fmp.get_balance_sheet(
                symbol, period="quarter", limit=kwargs.get("limit", 1)
            ),
            "cash_flow": lambda: self.fmp.get_cash_flow(
                symbol, period="quarter", limit=kwargs.get("limit", 1)
            ),
            "earnings": lambda: self.fmp.get_earnings_surprises(
                symbol, limit=kwargs.get("limit", 5)
            ),
            "product_segments": lambda: self.fmp.get_revenue_product_segmentation(symbol),
            "geo_segments": lambda: self.fmp.get_revenue_geographic_segmentation(symbol),
            "ratios": lambda: self.fmp.get_ratios(
                symbol, period="quarter", limit=kwargs.get("limit", 1)
            ),
            "key_metrics": lambda: self.fmp.get_key_metrics(
                symbol, period="quarter", limit=kwargs.get("limit", 1)
            ),
            "analyst_estimates": lambda: self.fmp.get_analyst_estimates(
                symbol, period="quarter", limit=kwargs.get("limit", 5)
            ),
            "price_history": lambda: self.fmp.get_historical_prices(
                symbol,
                from_date=kwargs.get("from_date"),
                to_date=kwargs.get("to_date")
            ),
            "earnings_calendar": lambda: self.fmp.get_earnings_calendar(symbol),
            "stock_news": lambda: self.fmp.get_stock_news(
                symbol, limit=kwargs.get("limit", 10)
            ),
            "insider_trading": lambda: self.fmp.get_insider_trading(
                symbol, limit=kwargs.get("limit", 10)
            ),
            "senate_trades": lambda: self.fmp.get_senate_trades(
                symbol, limit=kwargs.get("limit", 10)
            ),
            "price_target_consensus": lambda: self.fmp.get_price_target_consensus(symbol),
            "price_target_summary": lambda: self.fmp.get_price_target_summary(symbol),
            "analyst_grades": lambda: self.fmp.get_analyst_grades(
                symbol, limit=kwargs.get("limit", 10)
            ),
            "analyst_grades_consensus": lambda: self.fmp.get_analyst_grades_consensus(symbol),
        }

        fetcher = endpoint_mapping.get(endpoint)
        if fetcher:
            return await fetcher()

        raise ValueError(f"Unknown endpoint: {endpoint}")

    def get_cache_status(self, symbol: str) -> Dict[str, Any]:
        """Get cache status for a symbol - useful for debugging."""
        symbol = symbol.upper()
        symbol_dir = self.cache_dir / symbol

        if not symbol_dir.exists():
            return {"symbol": symbol, "cached": False, "endpoints": {}}

        status = {"symbol": symbol, "cached": True, "endpoints": {}}

        for file_path in symbol_dir.glob("*.json"):
            endpoint = file_path.stem
            cached = self._read_cache(symbol, endpoint)

            if cached:
                fetched_at = datetime.fromisoformat(cached["fetched_at"])
                ttl_days = self.TTL_DAYS.get(endpoint, 1)
                expires_at = fetched_at + timedelta(days=ttl_days)
                is_fresh = datetime.now() < expires_at

                status["endpoints"][endpoint] = {
                    "fetched_at": cached["fetched_at"],
                    "expires_at": expires_at.isoformat(),
                    "is_fresh": is_fresh,
                    "ttl_days": ttl_days
                }

        return status

    def clear_cache(self, symbol: str = None, endpoint: str = None) -> None:
        """
        Clear cache files.

        Args:
            symbol: If provided, clear only this symbol's cache
            endpoint: If provided with symbol, clear only this endpoint
        """
        if symbol and endpoint:
            # Clear specific endpoint
            file_path = self._get_file_path(symbol, endpoint)
            if file_path.exists():
                file_path.unlink()
                print(f"[CACHE CLEARED] {symbol}/{endpoint}")
        elif symbol:
            # Clear all endpoints for symbol
            symbol_dir = self.cache_dir / symbol.upper()
            if symbol_dir.exists():
                for file_path in symbol_dir.glob("*.json"):
                    file_path.unlink()
                symbol_dir.rmdir()
                print(f"[CACHE CLEARED] {symbol}/*")
        else:
            # Clear entire cache
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                print("[CACHE CLEARED] All cache files removed")

    def refresh_daily_data(self, symbol: str) -> None:
        """Force refresh of daily data (price/profile) for a symbol."""
        self.clear_cache(symbol, "profile")
        self.clear_cache(symbol, "price_history")


# Singleton instance
fmp_cache = FMPCache()
