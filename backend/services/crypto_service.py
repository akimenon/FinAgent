"""
Crypto Service

CoinGecko API client for fetching cryptocurrency prices.
Free tier, no API key required.
"""

import httpx
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


class CryptoService:
    """CoinGecko API client for crypto prices."""

    def __init__(self):
        self.base_url = COINGECKO_BASE_URL
        self.timeout = 10.0
        # Cache for coin ID lookups
        self._coin_id_cache: Dict[str, Optional[str]] = {}

    async def get_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get current price for a crypto ticker.

        Returns dict with:
        - price: Current USD price
        - change24h: 24h price change percentage
        - marketCap: Market cap in USD
        - volume24h: 24h trading volume
        """
        ticker_upper = ticker.upper()

        # Get CoinGecko ID
        coin_id = await self._get_coin_id(ticker_upper)
        if not coin_id:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/simple/price",
                    params={
                        "ids": coin_id,
                        "vs_currencies": "usd",
                        "include_24hr_change": "true",
                        "include_market_cap": "true",
                        "include_24hr_vol": "true",
                    }
                )
                response.raise_for_status()
                data = response.json()

                if coin_id not in data:
                    return None

                coin_data = data[coin_id]
                return {
                    "ticker": ticker_upper,
                    "coinId": coin_id,
                    "price": coin_data.get("usd"),
                    "change24h": coin_data.get("usd_24h_change"),
                    "marketCap": coin_data.get("usd_market_cap"),
                    "volume24h": coin_data.get("usd_24h_vol"),
                }
        except Exception as e:
            print(f"Error fetching crypto price for {ticker}: {e}")
            return None

    async def get_prices_batch(
        self, tickers: list[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get prices for multiple crypto tickers."""
        results = {}

        # Get coin IDs for all tickers
        coin_ids = {}
        for ticker in tickers:
            ticker_upper = ticker.upper()
            coin_id = await self._get_coin_id(ticker_upper)
            if coin_id:
                coin_ids[ticker_upper] = coin_id

        if not coin_ids:
            return {t.upper(): None for t in tickers}

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

                for ticker_upper, coin_id in coin_ids.items():
                    if coin_id in data:
                        coin_data = data[coin_id]
                        results[ticker_upper] = {
                            "ticker": ticker_upper,
                            "coinId": coin_id,
                            "price": coin_data.get("usd"),
                            "change24h": coin_data.get("usd_24h_change"),
                            "marketCap": coin_data.get("usd_market_cap"),
                            "volume24h": coin_data.get("usd_24h_vol"),
                        }
                    else:
                        results[ticker_upper] = None

        except Exception as e:
            print(f"Error fetching batch crypto prices: {e}")
            return {t.upper(): None for t in tickers}

        # Add None for tickers we couldn't find IDs for
        for ticker in tickers:
            if ticker.upper() not in results:
                results[ticker.upper()] = None

        return results

    async def _get_coin_id(self, ticker: str) -> Optional[str]:
        """Get CoinGecko ID for a ticker, using cache and search API."""
        ticker_upper = ticker.upper()

        # Check direct mapping first
        if ticker_upper in CRYPTO_ID_MAP:
            return CRYPTO_ID_MAP[ticker_upper]

        # Check cache
        if ticker_upper in self._coin_id_cache:
            return self._coin_id_cache[ticker_upper]

        # Search CoinGecko API
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"query": ticker_upper}
                )
                response.raise_for_status()
                data = response.json()

                coins = data.get("coins", [])
                # Find exact symbol match
                for coin in coins:
                    if coin.get("symbol", "").upper() == ticker_upper:
                        coin_id = coin.get("id")
                        self._coin_id_cache[ticker_upper] = coin_id
                        return coin_id

                # No match found
                self._coin_id_cache[ticker_upper] = None
                return None

        except Exception as e:
            print(f"Error searching for crypto {ticker}: {e}")
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
