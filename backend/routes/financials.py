from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timedelta
import asyncio
from services.fmp_service import fmp_service
from agents.data_fetcher import DataFetcherAgent
from agents.analysis_agent import AnalysisAgent
from agents.guidance_tracker import GuidanceTrackerAgent

router = APIRouter(prefix="/api/financials", tags=["financials"])

data_fetcher = DataFetcherAgent()
analyzer = AnalysisAgent()
guidance_tracker = GuidanceTrackerAgent()


@router.get("/{symbol}/overview")
async def get_quick_overview(symbol: str):
    """
    Get quick overview with key metrics - loads instantly without AI.
    Returns profile, latest quarter financials, balance sheet highlights, and cash flow.
    """
    symbol = symbol.upper()

    try:
        # Fetch all data in parallel for speed
        profile_task = fmp_service.get_company_profile(symbol)
        income_task = fmp_service.get_income_statement(symbol, period="quarter", limit=1)
        balance_task = fmp_service.get_balance_sheet(symbol, period="quarter", limit=1)
        cashflow_task = fmp_service.get_cash_flow(symbol, period="quarter", limit=1)
        earnings_task = fmp_service.get_earnings_surprises(symbol, limit=1)
        product_seg_task = fmp_service.get_revenue_product_segmentation(symbol)
        geo_seg_task = fmp_service.get_revenue_geographic_segmentation(symbol)

        profile, income, balance, cashflow, earnings, product_seg, geo_seg = await asyncio.gather(
            profile_task, income_task, balance_task, cashflow_task, earnings_task,
            product_seg_task, geo_seg_task
        )

        # Check for premium restriction errors
        if income and isinstance(income, list) and len(income) > 0:
            if "error" in str(income[0]).lower() or "premium" in str(income).lower():
                raise HTTPException(
                    status_code=403,
                    detail=f"{symbol} requires FMP premium subscription. Try major stocks like AAPL, MSFT, GOOGL."
                )

        if not income or len(income) == 0:
            raise HTTPException(status_code=404, detail=f"No financial data found for {symbol}")

        latest_income = income[0] if income else {}
        latest_balance = balance[0] if balance else {}
        latest_cashflow = cashflow[0] if cashflow else {}
        latest_earnings = earnings[0] if earnings and earnings[0].get("epsActual") else {}

        # Calculate key metrics
        revenue = latest_income.get("revenue", 0) or 0
        net_income = latest_income.get("netIncome", 0) or 0
        gross_profit = latest_income.get("grossProfit", 0) or 0
        operating_income = latest_income.get("operatingIncome", 0) or 0

        return {
            "symbol": symbol,
            "profile": {
                "name": profile.get("companyName", symbol),
                "sector": profile.get("sector"),
                "industry": profile.get("industry"),
                "ceo": profile.get("ceo"),
                "employees": profile.get("fullTimeEmployees"),
                "description": profile.get("description"),
                "website": profile.get("website"),
                "image": profile.get("image"),
            },
            "price": {
                "current": profile.get("price"),
                "change": profile.get("change"),
                "changePercent": profile.get("changePercentage"),
                "marketCap": profile.get("marketCap"),
                "volume": profile.get("volume"),
                "avgVolume": profile.get("averageVolume"),
                "range52Week": profile.get("range"),
                "beta": profile.get("beta"),
            },
            "latestQuarter": {
                "period": f"{latest_income.get('period', 'Q?')} {latest_income.get('fiscalYear', '')}".strip(),
                "date": latest_income.get("date"),
                "revenue": revenue,
                "netIncome": net_income,
                "grossProfit": gross_profit,
                "operatingIncome": operating_income,
                "eps": latest_income.get("eps"),
                "epsDiluted": latest_income.get("epsdiluted"),
                "grossMargin": round((gross_profit / revenue * 100), 2) if revenue else 0,
                "operatingMargin": round((operating_income / revenue * 100), 2) if revenue else 0,
                "netMargin": round((net_income / revenue * 100), 2) if revenue else 0,
            },
            "balanceSheet": {
                "cash": latest_balance.get("cashAndCashEquivalents", 0),
                "shortTermInvestments": latest_balance.get("shortTermInvestments", 0),
                "totalCash": latest_balance.get("cashAndShortTermInvestments", 0),
                "totalAssets": latest_balance.get("totalAssets", 0),
                "totalLiabilities": latest_balance.get("totalLiabilities", 0),
                "totalDebt": (latest_balance.get("shortTermDebt", 0) or 0) + (latest_balance.get("longTermDebt", 0) or 0),
                "shareholderEquity": latest_balance.get("totalStockholdersEquity", 0),
            },
            "cashFlow": {
                "operatingCashFlow": latest_cashflow.get("operatingCashFlow", 0),
                "capex": latest_cashflow.get("capitalExpenditure", 0),
                "freeCashFlow": latest_cashflow.get("freeCashFlow", 0),
                "dividendsPaid": latest_cashflow.get("commonDividendsPaid", 0),
                "stockBuyback": latest_cashflow.get("commonStockRepurchased", 0),
            },
            "earnings": {
                "actualEps": latest_earnings.get("epsActual"),
                "estimatedEps": latest_earnings.get("epsEstimated"),
                "surprise": round((latest_earnings.get("epsActual", 0) or 0) - (latest_earnings.get("epsEstimated", 0) or 0), 4) if latest_earnings else None,
                "beat": (latest_earnings.get("epsActual", 0) or 0) > (latest_earnings.get("epsEstimated", 0) or 0) if latest_earnings else None,
            },
            "revenuePillars": _process_revenue_pillars(product_seg, geo_seg),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _process_revenue_pillars(product_seg: list, geo_seg: list) -> dict:
    """
    Process segment data to identify key revenue drivers with trends.
    Automatically detects what matters for each company.
    """
    result = {"products": [], "geographies": []}

    # Process product segments
    if product_seg and len(product_seg) >= 2:
        current = product_seg[0]  # Latest year
        previous = product_seg[1]  # Previous year

        current_data = current.get("data", {})
        previous_data = previous.get("data", {})
        total_revenue = sum(current_data.values())

        for product, revenue in sorted(current_data.items(), key=lambda x: x[1], reverse=True):
            prev_revenue = previous_data.get(product, 0)
            yoy_change = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 0
            share = (revenue / total_revenue * 100) if total_revenue else 0

            result["products"].append({
                "name": product,
                "revenue": revenue,
                "previousRevenue": prev_revenue,
                "yoyChange": round(yoy_change, 1),
                "share": round(share, 1),
                "trend": "up" if yoy_change > 2 else "down" if yoy_change < -2 else "stable",
                "fiscalYear": current.get("fiscalYear"),
            })
    elif product_seg and len(product_seg) == 1:
        current = product_seg[0]
        current_data = current.get("data", {})
        total_revenue = sum(current_data.values())

        for product, revenue in sorted(current_data.items(), key=lambda x: x[1], reverse=True):
            share = (revenue / total_revenue * 100) if total_revenue else 0
            result["products"].append({
                "name": product,
                "revenue": revenue,
                "share": round(share, 1),
                "fiscalYear": current.get("fiscalYear"),
            })

    # Process geographic segments
    if geo_seg and len(geo_seg) >= 2:
        current = geo_seg[0]
        previous = geo_seg[1]

        current_data = current.get("data", {})
        previous_data = previous.get("data", {})
        total_revenue = sum(current_data.values())

        for region, revenue in sorted(current_data.items(), key=lambda x: x[1], reverse=True):
            prev_revenue = previous_data.get(region, 0)
            yoy_change = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 0
            share = (revenue / total_revenue * 100) if total_revenue else 0

            # Clean up region names
            clean_name = region.replace(" Segment", "")

            result["geographies"].append({
                "name": clean_name,
                "revenue": revenue,
                "previousRevenue": prev_revenue,
                "yoyChange": round(yoy_change, 1),
                "share": round(share, 1),
                "trend": "up" if yoy_change > 2 else "down" if yoy_change < -2 else "stable",
                "fiscalYear": current.get("fiscalYear"),
            })
    elif geo_seg and len(geo_seg) == 1:
        current = geo_seg[0]
        current_data = current.get("data", {})
        total_revenue = sum(current_data.values())

        for region, revenue in sorted(current_data.items(), key=lambda x: x[1], reverse=True):
            share = (revenue / total_revenue * 100) if total_revenue else 0
            clean_name = region.replace(" Segment", "")
            result["geographies"].append({
                "name": clean_name,
                "revenue": revenue,
                "share": round(share, 1),
                "fiscalYear": current.get("fiscalYear"),
            })

    return result


@router.get("/{symbol}/quarterly")
async def get_quarterly_results(symbol: str, limit: int = 5):
    """
    Get quarterly financial results.
    """
    try:
        data = await data_fetcher.fetch_income_statement(symbol.upper(), limit=limit)
        if data and "error" in str(data[0]) if data else True:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        return {
            "symbol": symbol.upper(),
            "quarters": data,
            "count": len(data),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/estimates")
async def get_analyst_estimates(symbol: str, limit: int = 5):
    """
    Get analyst estimates for upcoming quarters.
    """
    try:
        data = await fmp_service.get_analyst_estimates(symbol.upper(), limit=limit)
        return {
            "symbol": symbol.upper(),
            "estimates": data,
            "count": len(data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/surprises")
async def get_earnings_surprises(symbol: str, limit: int = 12):
    """
    Get historical earnings surprises (beat/miss history).
    """
    try:
        data = await data_fetcher.fetch_earnings_surprises(symbol.upper())
        # Limit results
        limited_data = data[:limit] if data else []

        return {
            "symbol": symbol.upper(),
            "surprises": limited_data,
            "count": len(limited_data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/price-history")
async def get_price_history(symbol: str, period: str = "1y"):
    """
    Get historical stock prices.
    Period options: 1m, 3m, 6m, 1y, 2y, 5y
    """
    # Calculate date range based on period
    period_days = {
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
    }

    days = period_days.get(period, 365)

    try:
        data = await data_fetcher.fetch_historical_prices(symbol.upper(), days=days)
        return {
            "symbol": symbol.upper(),
            "period": period,
            "prices": data.get("historical", []) if isinstance(data, dict) else data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/guidance")
async def get_guidance_tracking(symbol: str):
    """
    Get guidance tracking information.
    """
    try:
        # Fetch data and run guidance tracking
        financial_data = await data_fetcher.fetch_all(symbol.upper())
        guidance_result = guidance_tracker.track(financial_data)

        return {
            "symbol": symbol.upper(),
            "accuracy_score": guidance_result.get("accuracy_score"),
            "history": guidance_result.get("guidance_history"),
            "patterns": guidance_result.get("patterns"),
            "recommendation": guidance_result.get("recommendation"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/analysis")
async def get_analysis(symbol: str):
    """
    Get comprehensive analysis of a stock.
    """
    try:
        # Fetch all data
        financial_data = await data_fetcher.fetch_all(symbol.upper())

        # Run analysis
        analysis_result = analyzer.analyze(financial_data)

        return {
            "symbol": symbol.upper(),
            "company": financial_data.get("profile", {}),
            "metrics": analysis_result.get("metrics"),
            "trends": analysis_result.get("trends"),
            "concerns": analysis_result.get("concerns"),
            "beat_rate": analysis_result.get("beat_rate"),
            "summary": analysis_result.get("summary"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
