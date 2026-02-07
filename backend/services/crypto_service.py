"""
Crypto Service

CoinGecko API client for fetching cryptocurrency prices.
Free tier, no API key required.

Prices are cached to backend/data/crypto_cache/ with a 12-hour TTL
to avoid CoinGecko rate limits.
"""

import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional


# Mapping of common crypto ticker symbols to CoinGecko IDs
CRYPTO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "SHIB": "shiba-inu",
    "LTC": "litecoin",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XLM": "stellar",
    "ALGO": "algorand",
    "VET": "vechain",
    "FIL": "filecoin",
    "HBAR": "hedera-hashgraph",
    "ICP": "internet-computer",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "NEAR": "near",
    "INJ": "injective-protocol",
    "TIA": "celestia",
    "SUI": "sui",
    "SEI": "sei-network",
    "JUP": "jupiter-exchange-solana",
    "RENDER": "render-token",
    "PEPE": "pepe",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "FLOKI": "floki",
    "MEME": "memecoin-2",
    "ONDO": "ondo-finance",
    "ENA": "ethena",
    "JASMY": "jasmycoin",
    "FET": "fetch-ai",
    "BCH": "bitcoin-cash",
    "TRX": "tron",
    "TON": "the-open-network",
    "MKR": "maker",
    "AAVE": "aave",
    "CRV": "curve-dao-token",
    "SNX": "havven",
    "COMP": "compound-governance-token",
    "GRT": "the-graph",
    "ENS": "ethereum-name-service",
    "LDO": "lido-dao",
    "RPL": "rocket-pool",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "APE": "apecoin",
    "AXS": "axie-infinity",
    "IMX": "immutable-x",
    "GALA": "gala",
}

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


CACHE_TTL_HOURS = 12


class CryptoService:
    """CoinGecko API client for crypto prices."""

    def __init__(self):
        self.base_url = COINGECKO_BASE_URL
        self.timeout = 10.0
        # Cache for coin ID lookups
        self._coin_id_cache: Dict[str, Optional[str]] = {}
        # File-based price cache
        base_dir = Path(__file__).parent.parent
        self._cache_dir = base_dir / "data" / "crypto_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_file = self._cache_dir / "prices.json"

    def _read_cache(self) -> Dict[str, Any]:
        """Read cached prices if fresh (within TTL)."""
        if not self._cache_file.exists():
            return {}
        try:
            data = json.loads(self._cache_file.read_text())
            fetched_at = datetime.fromisoformat(data.get("fetchedAt", ""))
            if datetime.now() - fetched_at < timedelta(hours=CACHE_TTL_HOURS):
                return data.get("prices", {})
        except (json.JSONDecodeError, ValueError):
            pass
        return {}

    def _write_cache(self, prices: Dict[str, Any]) -> None:
        """Write prices to cache with current timestamp."""
        # Merge with existing cache (don't lose tickers not fetched this time)
        existing = {}
        if self._cache_file.exists():
            try:
                data = json.loads(self._cache_file.read_text())
                fetched_at = datetime.fromisoformat(data.get("fetchedAt", ""))
                if datetime.now() - fetched_at < timedelta(hours=CACHE_TTL_HOURS):
                    existing = data.get("prices", {})
            except (json.JSONDecodeError, ValueError):
                pass
        existing.update(prices)
        self._cache_file.write_text(json.dumps({
            "fetchedAt": datetime.now().isoformat(),
            "prices": existing,
        }, indent=2))

    async def get_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get current price for a crypto ticker.
        Uses the batch method (which has caching) for consistency.
        """
        result = await self.get_prices_batch([ticker])
        return result.get(ticker.upper())

    async def get_prices_batch(
        self, tickers: list[str], force_refresh: bool = False
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get prices for multiple crypto tickers. Uses 12h file cache."""
        results = {}
        cached = {} if force_refresh else self._read_cache()

        # Check which tickers we already have cached
        tickers_to_fetch = []
        for ticker in tickers:
            t = ticker.upper()
            if t in cached:
                results[t] = cached[t]
            else:
                tickers_to_fetch.append(t)

        # If everything was cached, return early
        if not tickers_to_fetch:
            print(f"[CRYPTO CACHE HIT] All {len(tickers)} tickers served from cache")
            return results

        # Get coin IDs for uncached tickers
        coin_ids = {}
        for ticker_upper in tickers_to_fetch:
            coin_id = await self._get_coin_id(ticker_upper)
            if coin_id:
                coin_ids[ticker_upper] = coin_id

        if not coin_ids:
            # No valid coin IDs found, return cached + None for the rest
            for t in tickers_to_fetch:
                results[t] = None
            return results

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/simple/price",
                    params={
                        "ids": ",".join(coin_ids.values()),
                        "vs_currencies": "usd",
                        "include_24hr_change": "true",
                        "include_market_cap": "true",
                        "include_24hr_vol": "true",
                    }
                )
                response.raise_for_status()
                data = response.json()

                fresh_prices = {}
                for ticker_upper, coin_id in coin_ids.items():
                    if coin_id in data:
                        coin_data = data[coin_id]
                        price_data = {
                            "ticker": ticker_upper,
                            "coinId": coin_id,
                            "price": coin_data.get("usd"),
                            "change24h": coin_data.get("usd_24h_change"),
                            "marketCap": coin_data.get("usd_market_cap"),
                            "volume24h": coin_data.get("usd_24h_vol"),
                        }
                        results[ticker_upper] = price_data
                        fresh_prices[ticker_upper] = price_data
                    else:
                        results[ticker_upper] = None

                # Save freshly fetched prices to cache
                if fresh_prices:
                    self._write_cache(fresh_prices)
                    print(f"[CRYPTO CACHE] Fetched & cached {len(fresh_prices)} tickers, {len(cached)} from cache")

        except Exception as e:
            print(f"Error fetching batch crypto prices: {e}")
            # Return whatever we had cached + None for the rest
            for t in tickers_to_fetch:
                if t not in results:
                    results[t] = None

        # Add None for tickers we couldn't find IDs for
        for ticker in tickers:
            if ticker.upper() not in results:
                results[ticker.upper()] = None

        return results

    async def _get_coin_id(self, ticker: str) -> Optional[str]:
        """Get CoinGecko ID for a ticker. Only uses CRYPTO_ID_MAP — no search fallback."""
        ticker_upper = ticker.upper()

        if ticker_upper in CRYPTO_ID_MAP:
            return CRYPTO_ID_MAP[ticker_upper]

        # Unknown ticker (e.g. LEDGER) — skip CoinGecko lookup
        return None

    async def search(self, query: str) -> list[Dict[str, Any]]:
        """Search for cryptocurrencies by name or symbol."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"query": query}
                )
                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "id": coin.get("id"),
                        "symbol": coin.get("symbol", "").upper(),
                        "name": coin.get("name"),
                        "thumb": coin.get("thumb"),
                        "marketCapRank": coin.get("market_cap_rank"),
                    }
                    for coin in data.get("coins", [])[:10]
                ]
        except Exception as e:
            print(f"Error searching crypto: {e}")
            return []


# Singleton instance
crypto_service = CryptoService()
