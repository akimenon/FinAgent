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

    async def get_earnings_calendar(self, symbol: str) -> List[Dict]:
        """Get earnings calendar for a symbol (past and upcoming earnings dates)"""
        return await self._request("earning-calendar-confirmed", {"symbol": symbol})

    async def get_stock_news(self, symbol: str = None, limit: int = 10) -> List[Dict]:
        """Get stock news for a specific symbol"""
        params = {"limit": limit, "page": 0}
        if symbol:
            params["symbols"] = symbol
        return await self._request("news/stock", params)

    async def get_insider_trading(self, symbol: str = None, limit: int = 10) -> List[Dict]:
        """Get insider trading activity for a symbol"""
        params = {"limit": limit, "page": 0}
        if symbol:
            params["symbol"] = symbol
        return await self._request("insider-trading/search", params)

    async def get_senate_trades(self, symbol: str = None, limit: int = 10) -> List[Dict]:
        """Get senate trading disclosures"""
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        return await self._request("senate-trades", params)

    async def get_top_gainers(self, limit: int = 10) -> List[Dict]:
        """Get top gaining stocks of the day"""
        return await self._request("biggest-gainers", {"limit": limit})

    async def get_top_losers(self, limit: int = 10) -> List[Dict]:
        """Get top losing stocks of the day"""
        return await self._request("biggest-losers", {"limit": limit})

    async def get_quote(self, symbol: str) -> Dict:
        """Get real-time quote for a symbol"""
        data = await self._request("quote", {"symbol": symbol})
        return data[0] if data else {}

    async def get_financial_growth(self, symbol: str, period: str = "quarter", limit: int = 4) -> List[Dict]:
        """Get financial growth metrics (QoQ/YoY growth rates)"""
        return await self._request(
            "financial-growth",
            {"symbol": symbol, "period": period, "limit": limit}
        )

    async def get_price_target_consensus(self, symbol: str) -> Dict:
        """Get consensus price target (high, low, median, average)"""
        data = await self._request("price-target-consensus", {"symbol": symbol})
        return data[0] if data else {}

    async def get_price_target_summary(self, symbol: str) -> Dict:
        """Get price target summary with historical averages"""
        data = await self._request("price-target-summary", {"symbol": symbol})
        return data[0] if data else {}

    async def get_analyst_grades(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get recent analyst grades/ratings with firm names"""
        return await self._request("grades", {"symbol": symbol, "limit": limit})

    async def get_analyst_grades_consensus(self, symbol: str) -> Dict:
        """Get consensus grades (strong buy/buy/hold/sell/strong sell counts)"""
        data = await self._request("grades-consensus", {"symbol": symbol})
        return data[0] if data else {}

    async def get_market_earnings_calendar(
        self, from_date: str, to_date: str, fmp_cache=None
    ) -> List[Dict]:
        """
        Get market-wide earnings calendar for a date range.

        Args:
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            fmp_cache: Unused, kept for API compatibility
        """
        return await self._request(
            "earnings-calendar",
            {"from": from_date, "to": to_date}
        )

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
fmp_service = FMPService()
