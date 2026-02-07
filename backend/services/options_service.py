"""
Options Service

Tradier API client for fetching live options chain prices.
Free sandbox tier — sign up at https://developer.tradier.com.

Prices are cached to backend/data/options_cache/ with a 15-minute TTL
since options prices change frequently during market hours.
"""

import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from config import settings


CACHE_TTL_MINUTES = 15


class OptionsService:
    """Tradier API client for options chain pricing."""

    def __init__(self):
        self.api_key = settings.TRADIER_API_KEY
        # Use sandbox (free) — switch to api.tradier.com for production
        self.base_url = "https://sandbox.tradier.com/v1"
        self.timeout = 10.0
        # File-based cache
        base_dir = Path(__file__).parent.parent
        self._cache_dir = base_dir / "data" / "options_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_configured(self) -> bool:
        """Check if a Tradier API key is configured."""
        return bool(self.api_key)

    def _cache_key(self, underlying: str, expiration: str) -> str:
        """Generate cache filename for an options chain."""
        return f"{underlying.upper()}_{expiration}"

    def _read_cache(self, cache_key: str) -> Optional[list]:
        """Read cached options chain if fresh (within TTL)."""
        cache_file = self._cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text())
            fetched_at = datetime.fromisoformat(data.get("fetchedAt", ""))
            if datetime.now() - fetched_at < timedelta(minutes=CACHE_TTL_MINUTES):
                return data.get("chain", [])
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _write_cache(self, cache_key: str, chain: Dict[str, Any]) -> None:
        """Write options chain to cache."""
        cache_file = self._cache_dir / f"{cache_key}.json"
        cache_file.write_text(json.dumps({
            "fetchedAt": datetime.now().isoformat(),
            "chain": chain,
        }, indent=2))

    async def get_option_price(
        self,
        underlying: str,
        strike: float,
        expiration: str,
        option_type: str,
    ) -> Optional[float]:
        """
        Get the last traded price for a specific option contract.

        Args:
            underlying: Underlying ticker (e.g. "AAPL")
            strike: Strike price (e.g. 200.0)
            expiration: Expiration date "YYYY-MM-DD"
            option_type: "call" or "put"

        Returns:
            Last traded price per contract, or None if unavailable
        """
        if not self.is_configured:
            return None

        chain = await self._get_chain(underlying, expiration)
        if not chain:
            return None

        # Find matching contract
        for contract in chain:
            if (
                contract.get("option_type") == option_type.lower()
                and abs(contract.get("strike", 0) - strike) < 0.01
            ):
                # Prefer last trade price; fall back to bid/ask midpoint
                last = contract.get("last")
                if last is not None and last > 0:
                    return last
                bid = contract.get("bid", 0) or 0
                ask = contract.get("ask", 0) or 0
                if bid > 0 and ask > 0:
                    return round((bid + ask) / 2, 2)
                return None

        return None

    async def get_option_prices_batch(
        self,
        holdings: list[Dict[str, Any]],
    ) -> Dict[str, Optional[float]]:
        """
        Get live prices for multiple option holdings.

        Groups holdings by underlying+expiration to minimize API calls.

        Args:
            holdings: List of option holding dicts with underlyingTicker,
                      strikePrice, expirationDate, optionType

        Returns:
            Dict mapping holding ID -> live price (or None)
        """
        if not self.is_configured:
            return {}

        results: Dict[str, Optional[float]] = {}

        # Group by underlying+expiration to batch chain fetches
        chain_groups: Dict[str, list[Dict[str, Any]]] = {}
        for h in holdings:
            underlying = (h.get("underlyingTicker") or "").upper()
            expiration = h.get("expirationDate") or ""
            if not underlying or not expiration:
                results[h["id"]] = None
                continue
            key = f"{underlying}_{expiration}"
            chain_groups.setdefault(key, []).append(h)

        # Fetch chains and match contracts
        for group_key, group_holdings in chain_groups.items():
            underlying, expiration = group_key.split("_", 1)
            chain = await self._get_chain(underlying, expiration)

            for h in group_holdings:
                if not chain:
                    results[h["id"]] = None
                    continue

                strike = h.get("strikePrice", 0)
                opt_type = (h.get("optionType") or "call").lower()

                price = None
                for contract in chain:
                    if (
                        contract.get("option_type") == opt_type
                        and abs(contract.get("strike", 0) - strike) < 0.01
                    ):
                        last = contract.get("last")
                        if last is not None and last > 0:
                            price = last
                        else:
                            bid = contract.get("bid", 0) or 0
                            ask = contract.get("ask", 0) or 0
                            if bid > 0 and ask > 0:
                                price = round((bid + ask) / 2, 2)
                        break

                results[h["id"]] = price

        return results

    async def _get_chain(
        self, underlying: str, expiration: str
    ) -> Optional[list[Dict[str, Any]]]:
        """Fetch options chain from cache or Tradier API."""
        underlying = underlying.upper()
        cache_key = self._cache_key(underlying, expiration)

        # Check cache
        cached = self._read_cache(cache_key)
        if cached is not None:
            print(f"[OPTIONS CACHE HIT] {underlying} exp {expiration}")
            return cached

        # Fetch from Tradier
        print(f"[OPTIONS CACHE MISS] {underlying} exp {expiration} - fetching from Tradier")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/markets/options/chains",
                    params={
                        "symbol": underlying,
                        "expiration": expiration,
                        "greeks": "false",
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                options = data.get("options")
                if options is None or options == "null":
                    print(f"[OPTIONS] No chain data for {underlying} exp {expiration}")
                    return None

                chain = options.get("option", [])
                if not chain:
                    return None

                # Cache the chain
                self._write_cache(cache_key, chain)
                print(f"[OPTIONS] Cached {len(chain)} contracts for {underlying} exp {expiration}")
                return chain

        except Exception as e:
            print(f"[OPTIONS ERROR] Failed to fetch chain for {underlying}: {e}")
            return None


# Singleton instance
options_service = OptionsService()
