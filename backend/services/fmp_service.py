import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from config import settings


class FMPService:
    """Financial Modeling Prep API Client - Updated for new /stable/ endpoints"""

    def __init__(self):
        self.base_url = "https://financialmodelingprep.com/stable"
        self.api_key = settings.FMP_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make a request to the FMP API"""
        client = await self._get_client()
        params = params or {}
        params["apikey"] = self.api_key

        url = f"{self.base_url}/{endpoint}"
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_company_profile(self, symbol: str) -> Dict:
        """Get company profile information"""
        data = await self._request("profile", {"symbol": symbol})
        return data[0] if data else {}

    async def search_companies(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for companies by name or symbol"""
        return await self._request("search-name", {"query": query, "limit": limit})

    async def get_income_statement(
        self, symbol: str, period: str = "quarter", limit: int = 8
    ) -> List[Dict]:
        """
        Get income statement data
        period: 'quarter' or 'annual'
        """
        return await self._request(
            "income-statement",
            {"symbol": symbol, "period": period, "limit": limit}
        )

    async def get_earnings_surprises(self, symbol: str, limit: int = 5) -> List[Dict]:
        """Get historical earnings data (actual vs estimated EPS)"""
        return await self._request("earnings", {"symbol": symbol, "limit": limit})

    async def get_analyst_estimates(self, symbol: str, period: str = "quarter", limit: int = 8) -> List[Dict]:
        """Get analyst estimates for EPS and revenue"""
        return await self._request(
            "analyst-estimates",
            {"symbol": symbol, "period": period, "limit": limit}
        )

    async def get_historical_prices(
        self, symbol: str, from_date: Optional[str] = None, to_date: Optional[str] = None
    ) -> List[Dict]:
        """Get historical stock prices"""
        params = {"symbol": symbol}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return await self._request("historical-price-eod/full", params)

    async def get_key_metrics(self, symbol: str, period: str = "quarter", limit: int = 8) -> List[Dict]:
        """Get key financial metrics"""
        return await self._request(
            "key-metrics",
            {"symbol": symbol, "period": period, "limit": limit}
        )

    async def get_financial_growth(self, symbol: str, period: str = "quarter", limit: int = 8) -> List[Dict]:
        """Get financial growth metrics"""
        return await self._request(
            "financial-growth",
            {"symbol": symbol, "period": period, "limit": limit}
        )

    async def get_balance_sheet(self, symbol: str, period: str = "quarter", limit: int = 1) -> List[Dict]:
        """Get balance sheet data"""
        return await self._request(
            "balance-sheet-statement",
            {"symbol": symbol, "period": period, "limit": limit}
        )

    async def get_cash_flow(self, symbol: str, period: str = "quarter", limit: int = 1) -> List[Dict]:
        """Get cash flow statement data"""
        return await self._request(
            "cash-flow-statement",
            {"symbol": symbol, "period": period, "limit": limit}
        )

    async def get_shares_float(self, symbol: str) -> Dict:
        """Get shares outstanding/float data"""
        data = await self._request("shares-float", {"symbol": symbol})
        return data[0] if data else {}

    async def get_revenue_product_segmentation(self, symbol: str) -> List[Dict]:
        """Get revenue breakdown by product (iPhone, Mac, Services, etc.)"""
        return await self._request("revenue-product-segmentation", {"symbol": symbol})

    async def get_revenue_geographic_segmentation(self, symbol: str) -> List[Dict]:
        """Get revenue breakdown by geography (Americas, Europe, China, etc.)"""
        return await self._request("revenue-geographic-segmentation", {"symbol": symbol})

    async def get_ratios(self, symbol: str, period: str = "quarter", limit: int = 5) -> List[Dict]:
        """Get financial ratios (P/E, P/B, ROE, etc.)"""
        return await self._request(
            "ratios",
            {"symbol": symbol, "period": period, "limit": limit}
        )

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
fmp_service = FMPService()
