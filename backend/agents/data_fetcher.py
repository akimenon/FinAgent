from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from services.fmp_service import fmp_service


class DataFetcherAgent:
    """
    Agent responsible for fetching financial data from FMP API.
    Handles caching and data transformation.
    """

    def __init__(self):
        self.fmp = fmp_service

    async def fetch_all(self, symbol: str, quarters: int = 5) -> Dict[str, Any]:
        """
        Fetch all financial data for a symbol.
        Returns a consolidated data package.
        """
        import asyncio

        # Fetch data in parallel
        income_task = self.fetch_income_statement(symbol, quarters)
        surprises_task = self.fetch_earnings_surprises(symbol)
        estimates_task = self.fetch_analyst_estimates(symbol, quarters)
        profile_task = self.fetch_company_profile(symbol)

        income, surprises, estimates, profile = await asyncio.gather(
            income_task, surprises_task, estimates_task, profile_task
        )

        return {
            "symbol": symbol,
            "profile": profile,
            "income_statements": income,
            "earnings_surprises": surprises,
            "analyst_estimates": estimates,
            "fetched_at": datetime.utcnow().isoformat(),
        }

    async def fetch_company_profile(self, symbol: str) -> Dict:
        """Fetch company profile"""
        try:
            return await self.fmp.get_company_profile(symbol)
        except Exception as e:
            return {"error": str(e)}

    async def fetch_income_statement(self, symbol: str, limit: int = 5) -> List[Dict]:
        """
        Fetch quarterly income statements.
        Returns processed data with calculated metrics.
        """
        try:
            data = await self.fmp.get_income_statement(symbol, period="quarter", limit=limit)
            return self._process_income_data(data)
        except Exception as e:
            return [{"error": str(e)}]

    async def fetch_earnings_surprises(self, symbol: str) -> List[Dict]:
        """Fetch earnings surprises (beat/miss history)"""
        try:
            data = await self.fmp.get_earnings_surprises(symbol)
            return self._process_surprises_data(data)
        except Exception as e:
            return [{"error": str(e)}]

    async def fetch_analyst_estimates(self, symbol: str, limit: int = 5) -> List[Dict]:
        """Fetch analyst estimates"""
        try:
            data = await self.fmp.get_analyst_estimates(symbol, period="quarter", limit=limit)
            return data
        except Exception as e:
            return [{"error": str(e)}]

    async def fetch_historical_prices(
        self, symbol: str, days: int = 365
    ) -> Dict[str, Any]:
        """Fetch historical price data"""
        try:
            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            data = await self.fmp.get_historical_prices(symbol, from_date, to_date)
            return data
        except Exception as e:
            return {"error": str(e)}

    def _process_income_data(self, data: List[Dict]) -> List[Dict]:
        """Process income statement data and add calculated metrics"""
        processed = []
        for i, item in enumerate(data):
            revenue = item.get("revenue", 0) or 0
            gross_profit = item.get("grossProfit", 0) or 0
            operating_income = item.get("operatingIncome", 0) or 0
            net_income = item.get("netIncome", 0) or 0

            # Calculate margins
            gross_margin = (gross_profit / revenue * 100) if revenue else 0
            operating_margin = (operating_income / revenue * 100) if revenue else 0
            net_margin = (net_income / revenue * 100) if revenue else 0

            # Calculate YoY growth if we have year-ago data
            revenue_growth_yoy = None
            eps_growth_yoy = None
            if i + 4 < len(data):
                year_ago = data[i + 4]
                year_ago_revenue = year_ago.get("revenue", 0) or 0
                year_ago_eps = year_ago.get("eps", 0) or 0
                current_eps = item.get("eps", 0) or 0

                if year_ago_revenue:
                    revenue_growth_yoy = ((revenue - year_ago_revenue) / year_ago_revenue * 100)
                if year_ago_eps and year_ago_eps != 0:
                    eps_growth_yoy = ((current_eps - year_ago_eps) / abs(year_ago_eps) * 100)

            # Parse fiscal quarter from date
            date_str = item.get("date", "")
            fiscal_quarter = self._get_fiscal_quarter(item.get("period", ""))

            processed.append({
                "date": date_str,
                "fiscal_year": int(date_str[:4]) if date_str else None,
                "fiscal_quarter": fiscal_quarter,
                "revenue": revenue,
                "gross_profit": gross_profit,
                "operating_income": operating_income,
                "net_income": net_income,
                "eps": item.get("eps"),
                "eps_diluted": item.get("epsdiluted"),
                "gross_margin": round(gross_margin, 2),
                "operating_margin": round(operating_margin, 2),
                "net_margin": round(net_margin, 2),
                "revenue_growth_yoy": round(revenue_growth_yoy, 2) if revenue_growth_yoy is not None else None,
                "eps_growth_yoy": round(eps_growth_yoy, 2) if eps_growth_yoy is not None else None,
            })

        return processed

    def _process_surprises_data(self, data: List[Dict]) -> List[Dict]:
        """Process earnings surprises data from /stable/earnings endpoint"""
        processed = []
        for item in data:
            actual = item.get("epsActual") or 0
            estimated = item.get("epsEstimated") or 0

            # Skip future earnings (no actual data yet)
            if actual == 0 and estimated == 0:
                continue
            if item.get("epsActual") is None:
                continue

            surprise = actual - estimated
            surprise_percent = (surprise / abs(estimated) * 100) if estimated else 0

            # Determine beat/miss
            if surprise > 0.01:
                verdict = "BEAT"
            elif surprise < -0.01:
                verdict = "MISS"
            else:
                verdict = "MEET"

            processed.append({
                "date": item.get("date"),
                "symbol": item.get("symbol"),
                "actual_eps": actual,
                "estimated_eps": estimated,
                "eps_surprise": round(surprise, 4),
                "eps_surprise_percent": round(surprise_percent, 2),
                "beat_miss": verdict,
                "revenue_actual": item.get("revenueActual"),
                "revenue_estimated": item.get("revenueEstimated"),
            })

        return processed

    def _get_fiscal_quarter(self, period: str) -> str:
        """Extract fiscal quarter from period string"""
        period = period.upper()
        if "Q1" in period:
            return "Q1"
        elif "Q2" in period:
            return "Q2"
        elif "Q3" in period:
            return "Q3"
        elif "Q4" in period:
            return "Q4"
        return period
