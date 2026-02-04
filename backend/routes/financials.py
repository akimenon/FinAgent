from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timedelta
import asyncio
from services.fmp_service import fmp_service
from services.fmp_cache import fmp_cache
from services.insights_cache import insights_cache
from services.company_assets import enrich_with_company_info
from agents.data_fetcher import DataFetcherAgent
from agents.analysis_agent import AnalysisAgent
from agents.guidance_tracker import GuidanceTrackerAgent
from agents.deep_insights_agent import deep_insights_agent

router = APIRouter(prefix="/api/financials", tags=["financials"])


@router.get("/earnings-calendar")
async def get_upcoming_earnings_calendar(days: int = 7, enrich: bool = True):
    """
    Get market-wide earnings calendar for the next N days.

    Args:
        days: Number of days to look ahead (default 7, max 30)
        enrich: If True, include company name and logo (slower but richer data)

    Returns:
        Upcoming earnings announcements with estimates and company info
    """
    # Limit days to reasonable range
    days = min(max(days, 1), 30)

    today = datetime.now()
    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        # Fetch earnings calendar from cache or API
        # Include days in cache key so different ranges don't conflict
        data = await fmp_cache.get_market_data(
            f"market_earnings_calendar_{days}d",
            from_date=from_date,
            to_date=to_date
        )

        if not data:
            return {
                "earnings": [],
                "count": 0,
                "dateRange": {"from": from_date, "to": to_date}
            }

        # Process earnings data
        earnings = []
        for item in data:
            # Only include items with valid dates and symbols
            if not item.get("date") or not item.get("symbol"):
                continue

            earnings.append({
                "symbol": item.get("symbol"),
                "date": item.get("date"),
                "epsEstimate": item.get("epsEstimated"),
                "revenueEstimate": item.get("revenueEstimated"),
                "fiscalDateEnding": item.get("fiscalDateEnding"),
                "updatedAt": item.get("lastUpdated"),
            })

        # Sort by date, then by symbol for consistent ordering
        earnings.sort(key=lambda x: (x["date"], x["symbol"]))

        # Enrich with company profiles (name, logo, sector, industry) from static assets
        # This is instant - no API calls needed
        if enrich and earnings:
            enrich_with_company_info(earnings, symbol_key="symbol")

        return {
            "earnings": earnings,
            "count": len(earnings),
            "dateRange": {"from": from_date, "to": to_date}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch earnings calendar: {str(e)}")

data_fetcher = DataFetcherAgent()
analyzer = AnalysisAgent()
guidance_tracker = GuidanceTrackerAgent()


def _safe_float(value, default=0):
    """Safely convert a value to float, handling None and strings."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=0):
    """Safely convert a value to int, handling None and strings."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


@router.get("/{symbol}/deep-insights")
async def get_deep_insights(symbol: str, refresh: bool = False):
    """
    Get LLM-powered deep insights for a company.

    This endpoint uses AI to analyze comprehensive financial data and surface
    insights that regular retail investors typically miss. Analysis is cached
    for 24 hours.

    Args:
        symbol: Stock symbol
        refresh: If True, bypass cache and generate fresh analysis

    Returns:
        Deep insights including industry context, operational metrics,
        hidden patterns, risks, opportunities, and beginner explanation
    """
    symbol = symbol.upper()

    # Check cache first (unless refresh requested)
    if not refresh:
        cached_insights = insights_cache.get(symbol)
        if cached_insights:
            return {
                "symbol": symbol,
                "fromCache": True,
                "insights": cached_insights
            }

    try:
        # Gather comprehensive data for analysis
        print(f"[DEEP INSIGHTS] Gathering data for {symbol}...")

        # Fetch all data in parallel
        profile_task = fmp_cache.get("profile", symbol)
        income_task = fmp_cache.get("income_quarterly", symbol, limit=12)  # 3 years
        income_annual_task = fmp_cache.get("income_annual", symbol, limit=3)
        balance_task = fmp_cache.get("balance_sheet", symbol, limit=4)
        cashflow_task = fmp_cache.get("cash_flow", symbol, limit=4)
        earnings_task = fmp_cache.get("earnings", symbol, limit=12)
        product_seg_task = fmp_cache.get("product_segments", symbol)
        geo_seg_task = fmp_cache.get("geo_segments", symbol)
        ratios_task = fmp_cache.get("ratios", symbol, limit=4)
        growth_task = fmp_service.get_financial_growth(symbol, period="quarter", limit=4)

        results = await asyncio.gather(
            profile_task, income_task, income_annual_task, balance_task,
            cashflow_task, earnings_task, product_seg_task, geo_seg_task,
            ratios_task, growth_task,
            return_exceptions=True
        )

        profile, income, income_annual, balance, cashflow, earnings, \
            product_seg, geo_seg, ratios, growth = results

        # Handle exceptions gracefully
        def safe_result(r):
            return r if not isinstance(r, Exception) else []

        # Prepare comprehensive data for the agent
        comprehensive_data = {
            "profile": profile if not isinstance(profile, Exception) else {},
            "income_statements": safe_result(income),
            "income_annual": safe_result(income_annual),
            "balance_sheet": safe_result(balance),
            "cash_flow": safe_result(cashflow),
            "earnings_surprises": safe_result(earnings),
            "product_segments": safe_result(product_seg),
            "geo_segments": safe_result(geo_seg),
            "ratios": safe_result(ratios),
            "financial_growth": safe_result(growth),
        }

        # Run deep insights analysis
        print(f"[DEEP INSIGHTS] Running LLM analysis for {symbol}...")
        insights = await deep_insights_agent.analyze(comprehensive_data)

        # Cache the results
        if insights.get("_meta", {}).get("success", True):
            insights_cache.set(symbol, insights)

        return {
            "symbol": symbol,
            "fromCache": False,
            "insights": insights
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep insights analysis failed: {str(e)}")


@router.get("/{symbol}/deep-insights/status")
async def get_deep_insights_status(symbol: str):
    """Get cache status for deep insights."""
    return insights_cache.get_status(symbol)


@router.delete("/{symbol}/deep-insights/cache")
async def invalidate_deep_insights_cache(symbol: str):
    """Invalidate cached deep insights for a symbol."""
    invalidated = insights_cache.invalidate(symbol)
    return {
        "symbol": symbol.upper(),
        "invalidated": invalidated,
        "message": f"Cache {'cleared' if invalidated else 'was not present'} for {symbol.upper()}"
    }


@router.get("/{symbol}/overview")
async def get_quick_overview(symbol: str):
    """
    Get quick overview with key metrics - loads instantly without AI.
    Returns profile, latest quarter financials, balance sheet highlights, and cash flow.
    """
    symbol = symbol.upper()

    try:
        # Fetch all data in parallel using cache (minimizes API calls)
        profile_task = fmp_cache.get("profile", symbol)
        income_task = fmp_cache.get("income_quarterly", symbol, limit=5)  # Get 5 quarters for comparison
        balance_task = fmp_cache.get("balance_sheet", symbol, limit=5)  # Get 5 quarters for 4Q comparison
        cashflow_task = fmp_cache.get("cash_flow", symbol, limit=5)  # Get 5 quarters for 4Q comparison
        earnings_task = fmp_cache.get("earnings", symbol, limit=5)  # Historical earnings for beat/miss
        earnings_calendar_task = fmp_cache.get("earnings_calendar", symbol)  # Confirmed upcoming earnings
        product_seg_task = fmp_cache.get("product_segments", symbol)
        geo_seg_task = fmp_cache.get("geo_segments", symbol)
        price_changes_task = _calculate_price_changes(symbol)
        # Analyst data
        price_target_task = fmp_cache.get("price_target_consensus", symbol)
        grades_consensus_task = fmp_cache.get("analyst_grades_consensus", symbol)

        results = await asyncio.gather(
            profile_task, income_task, balance_task, cashflow_task, earnings_task,
            earnings_calendar_task, product_seg_task, geo_seg_task, price_changes_task,
            price_target_task, grades_consensus_task,
            return_exceptions=True  # Don't fail if one endpoint errors
        )

        profile, income, balance, cashflow, earnings, earnings_calendar, product_seg, geo_seg, price_changes, \
            price_target, grades_consensus = results

        # Handle any exceptions gracefully
        if isinstance(profile, Exception):
            raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {profile}")
        if isinstance(income, Exception):
            income = []
        if isinstance(balance, Exception):
            balance = []
        if isinstance(cashflow, Exception):
            cashflow = []
        if isinstance(earnings, Exception):
            earnings = []
        if isinstance(earnings_calendar, Exception):
            earnings_calendar = []
        if isinstance(product_seg, Exception):
            product_seg = []
        if isinstance(geo_seg, Exception):
            geo_seg = []
        if isinstance(price_changes, Exception):
            price_changes = {"momChangePercent": None, "yoyChangePercent": None}
        if isinstance(price_target, Exception):
            price_target = {}
        if isinstance(grades_consensus, Exception):
            grades_consensus = {}

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
        revenue = _safe_float(latest_income.get("revenue", 0))
        net_income = _safe_float(latest_income.get("netIncome", 0))
        gross_profit = _safe_float(latest_income.get("grossProfit", 0))
        operating_income = _safe_float(latest_income.get("operatingIncome", 0))

        # Process quarterly comparison with all data sources for 4Q view
        quarterly_comparison = _process_quarterly_comparison(income, balance, cashflow, profile)

        # Build balance sheet and cash flow data for insights
        balance_sheet_data = {
            "cash": _safe_float(latest_balance.get("cashAndCashEquivalents", 0)),
            "totalCash": _safe_float(latest_balance.get("cashAndShortTermInvestments", 0)),
            "totalAssets": _safe_float(latest_balance.get("totalAssets", 0)),
            "totalLiabilities": _safe_float(latest_balance.get("totalLiabilities", 0)),
            "totalDebt": _safe_float(latest_balance.get("shortTermDebt", 0)) + _safe_float(latest_balance.get("longTermDebt", 0)),
            "shareholderEquity": _safe_float(latest_balance.get("totalStockholdersEquity", 0)),
        }

        cash_flow_data = {
            "operatingCashFlow": _safe_float(latest_cashflow.get("operatingCashFlow", 0)),
            "capex": _safe_float(latest_cashflow.get("capitalExpenditure", 0)),
            "freeCashFlow": _safe_float(latest_cashflow.get("freeCashFlow", 0)),
        }

        # Generate smart insights
        smart_insights = _generate_smart_insights(
            quarterly_comparison,
            balance_sheet_data,
            cash_flow_data,
            latest_earnings,
            profile
        )

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
                "momChangePercent": price_changes.get("momChangePercent"),
                "yoyChangePercent": price_changes.get("yoyChangePercent"),
            },
            "latestQuarter": {
                "period": f"{latest_income.get('period', 'Q?')} {latest_income.get('fiscalYear', '')}".strip(),
                "date": latest_income.get("date"),
                "reportedDate": latest_income.get("acceptedDate"),  # SEC filing accepted date
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
                "announcementDate": latest_earnings.get("date"),  # Actual earnings release date
            },
            "revenuePillars": _process_revenue_pillars(product_seg, geo_seg),
            "nextEarnings": _get_next_earnings(earnings_calendar, earnings),
            "quarterlyComparison": quarterly_comparison,
            "smartInsights": smart_insights,
            "analystRatings": _process_analyst_data(price_target, grades_consensus, profile.get("price")),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _find_price_near_date(prices: list, target_date, tolerance_days: int = 7):
    """Find closing price for trading day closest to target_date."""
    target_dt = target_date.date() if hasattr(target_date, 'date') else target_date
    best_match = None
    best_diff = float('inf')

    for record in prices:
        date_str = record.get("date", "")
        if not date_str:
            continue
        try:
            record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            diff = abs((record_date - target_dt).days)
            if diff <= tolerance_days and diff < best_diff:
                best_diff = diff
                best_match = record.get("close") or record.get("adjClose")
                if diff == 0:
                    break
        except ValueError:
            continue
    return best_match


async def _calculate_price_changes(symbol: str) -> dict:
    """Calculate MoM and YoY price changes using historical data."""
    today = datetime.now()
    one_month_ago = today - timedelta(days=30)
    one_year_ago = today - timedelta(days=365)

    # Fetch 400 days of history to ensure we have YoY data
    from_date = (today - timedelta(days=400)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")

    try:
        price_data = await fmp_cache.get(
            "price_history", symbol,
            from_date=from_date, to_date=to_date
        )

        if not price_data or not isinstance(price_data, list):
            return {"momChangePercent": None, "yoyChangePercent": None}

        prices = sorted(price_data, key=lambda x: x.get("date", ""), reverse=True)
        if not prices:
            return {"momChangePercent": None, "yoyChangePercent": None}

        current_price = _safe_float(prices[0].get("close") or prices[0].get("adjClose"), None)
        mom_price = _safe_float(_find_price_near_date(prices, one_month_ago), None)
        yoy_price = _safe_float(_find_price_near_date(prices, one_year_ago), None)

        result = {"momChangePercent": None, "yoyChangePercent": None}

        if current_price and mom_price:
            result["momChangePercent"] = round((current_price - mom_price) / mom_price * 100, 2)

        if current_price and yoy_price:
            result["yoyChangePercent"] = round((current_price - yoy_price) / yoy_price * 100, 2)

        return result
    except Exception as e:
        print(f"Error calculating price changes for {symbol}: {e}")
        return {"momChangePercent": None, "yoyChangePercent": None}


def _get_next_earnings(earnings_calendar: list, earnings_history: list = None) -> dict:
    """
    Extract the next upcoming earnings date.
    First tries the confirmed earnings calendar, then falls back to earnings history
    (future dates where epsActual is null).
    """
    today = datetime.now().date()
    upcoming = []

    # Try earnings calendar first (confirmed dates)
    if earnings_calendar:
        for entry in earnings_calendar:
            earnings_date_str = entry.get("date")
            if not earnings_date_str:
                continue

            try:
                earnings_date = datetime.strptime(earnings_date_str, "%Y-%m-%d").date()
                if earnings_date >= today:
                    upcoming.append({
                        "date": earnings_date,
                        "date_str": earnings_date_str,
                        "epsEstimate": entry.get("eps") or entry.get("epsEstimated"),
                        "revenueEstimate": entry.get("revenue") or entry.get("revenueEstimated"),
                    })
            except ValueError:
                continue

    # Fallback to earnings history (future dates with epsActual = null)
    if not upcoming and earnings_history:
        for entry in earnings_history:
            earnings_date_str = entry.get("date")
            if not earnings_date_str:
                continue

            try:
                earnings_date = datetime.strptime(earnings_date_str, "%Y-%m-%d").date()
                # Future date with no actual results = upcoming earnings
                if earnings_date >= today and entry.get("epsActual") is None:
                    upcoming.append({
                        "date": earnings_date,
                        "date_str": earnings_date_str,
                        "epsEstimate": entry.get("epsEstimated"),
                        "revenueEstimate": entry.get("revenueEstimated"),
                    })
            except ValueError:
                continue

    if not upcoming:
        return None

    # Sort by date and return the earliest (closest) upcoming earnings
    upcoming.sort(key=lambda x: x["date"])
    next_earnings = upcoming[0]
    days_until = (next_earnings["date"] - today).days

    return {
        "date": next_earnings["date_str"],
        "daysUntil": days_until,
        "epsEstimate": next_earnings["epsEstimate"],
        "revenueEstimate": next_earnings["revenueEstimate"],
    }


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
        total_revenue = sum(_safe_float(v) for v in current_data.values())

        for product, rev in sorted(current_data.items(), key=lambda x: _safe_float(x[1]), reverse=True):
            revenue = _safe_float(rev)
            prev_revenue = _safe_float(previous_data.get(product, 0))
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
        total_revenue = sum(_safe_float(v) for v in current_data.values())

        for product, rev in sorted(current_data.items(), key=lambda x: _safe_float(x[1]), reverse=True):
            revenue = _safe_float(rev)
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
        total_revenue = sum(_safe_float(v) for v in current_data.values())

        for region, rev in sorted(current_data.items(), key=lambda x: _safe_float(x[1]), reverse=True):
            revenue = _safe_float(rev)
            prev_revenue = _safe_float(previous_data.get(region, 0))
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
        total_revenue = sum(_safe_float(v) for v in current_data.values())

        for region, rev in sorted(current_data.items(), key=lambda x: _safe_float(x[1]), reverse=True):
            revenue = _safe_float(rev)
            share = (revenue / total_revenue * 100) if total_revenue else 0
            clean_name = region.replace(" Segment", "")
            result["geographies"].append({
                "name": clean_name,
                "revenue": revenue,
                "share": round(share, 1),
                "fiscalYear": current.get("fiscalYear"),
            })

    return result


def _process_quarterly_comparison(income_data: list, balance_data: list = None,
                                   cashflow_data: list = None, profile: dict = None) -> dict:
    """
    Process financial data into comprehensive quarterly comparison format.
    Merges income statement, balance sheet, and cash flow by matching quarters.
    Returns ~28 metrics across 6 categories (A-F).
    """
    if not income_data or len(income_data) == 0:
        return {"latest": None, "quarters": [], "yoyComparison": None}

    # Build lookup dicts for balance sheet and cash flow by period
    balance_by_period = {}
    cashflow_by_period = {}

    if balance_data:
        for b in balance_data:
            key = f"{b.get('period')} {b.get('fiscalYear')}"
            balance_by_period[key] = b

    if cashflow_data:
        for c in cashflow_data:
            key = f"{c.get('period')} {c.get('fiscalYear')}"
            cashflow_by_period[key] = c

    # Get headcount from profile (same for all quarters - latest available)
    headcount = _safe_int(profile.get("fullTimeEmployees"), None) if profile else None

    quarters = []
    prev_revenue = None

    for q in income_data[:5]:  # Get up to 5 quarters
        revenue = _safe_float(q.get("revenue", 0))
        gross_profit = _safe_float(q.get("grossProfit", 0))
        operating_income = _safe_float(q.get("operatingIncome", 0))
        net_income = _safe_float(q.get("netIncome", 0))
        cost_of_revenue = _safe_float(q.get("costOfRevenue", 0))
        rd_expense = _safe_float(q.get("researchAndDevelopmentExpenses", 0))
        sga_expense = _safe_float(q.get("sellingGeneralAndAdministrativeExpenses", 0))
        op_expenses = _safe_float(q.get("operatingExpenses", 0))
        interest_expense = _safe_float(q.get("interestExpense", 0))

        period_key = f"{q.get('period')} {q.get('fiscalYear')}"
        balance = balance_by_period.get(period_key, {})
        cashflow = cashflow_by_period.get(period_key, {})

        # Calculate QoQ revenue growth (comparing to next item which is previous quarter)
        qoq_growth = None
        if prev_revenue and prev_revenue > 0:
            qoq_growth = round((revenue - prev_revenue) / prev_revenue * 100, 2)

        # Get stock-based compensation for SBC % calculation
        sbc = _safe_float(cashflow.get("stockBasedCompensation", 0))

        quarter_data = {
            "period": period_key.strip(),
            "date": q.get("date"),
            "fiscalYear": q.get("fiscalYear"),
            "fiscalQuarter": q.get("period"),

            # A. Growth & Profitability
            "revenue": revenue,
            "revenueQoQ": qoq_growth,
            "grossProfit": gross_profit,
            "operatingIncome": operating_income,
            "netIncome": net_income,
            "eps": q.get("eps"),
            "epsDiluted": q.get("epsdiluted"),
            "grossMargin": round((gross_profit / revenue * 100), 2) if revenue else 0,
            "operatingMargin": round((operating_income / revenue * 100), 2) if revenue else 0,
            "netMargin": round((net_income / revenue * 100), 2) if revenue else 0,

            # B. Cost Structure
            "costOfRevenue": cost_of_revenue,
            "cogsPercent": round((cost_of_revenue / revenue * 100), 2) if revenue else 0,
            "rdExpense": rd_expense,
            "sgaExpense": sga_expense,
            "totalOpex": op_expenses,

            # C. Cash Flow
            "operatingCashFlow": cashflow.get("operatingCashFlow"),
            "freeCashFlow": cashflow.get("freeCashFlow"),
            "capex": cashflow.get("capitalExpenditure"),

            # D. Balance Sheet & Liquidity
            "cash": balance.get("cashAndCashEquivalents"),
            "totalDebt": balance.get("totalDebt"),
            "shortTermDebt": balance.get("shortTermDebt"),
            "longTermDebt": balance.get("longTermDebt"),
            "netDebt": balance.get("netDebt"),
            "interestExpense": interest_expense,

            # E. Efficiency & Dilution
            "stockBasedComp": sbc,
            "sbcPercent": round((sbc / revenue * 100), 2) if revenue and sbc else None,
            "headcount": headcount,
            "revenuePerEmployee": round(revenue / headcount) if headcount and revenue else None,

            # F. Leading Indicators
            "deferredRevenue": balance.get("deferredRevenue"),
        }

        quarters.append(quarter_data)
        prev_revenue = revenue

    # Calculate YoY comparison (Q1 vs Q5 if same quarter, otherwise find matching quarter)
    yoy_comparison = None
    if len(quarters) >= 5:
        current = quarters[0]
        # Find the same quarter from last year (typically 4 quarters ago)
        year_ago = quarters[4]

        if current["fiscalQuarter"] == year_ago["fiscalQuarter"]:
            yoy_comparison = {
                "currentPeriod": current["period"],
                "previousPeriod": year_ago["period"],
                "revenueChange": _calc_pct_change(current["revenue"], year_ago["revenue"]),
                "grossProfitChange": _calc_pct_change(current["grossProfit"], year_ago["grossProfit"]),
                "operatingIncomeChange": _calc_pct_change(current["operatingIncome"], year_ago["operatingIncome"]),
                "netIncomeChange": _calc_pct_change(current["netIncome"], year_ago["netIncome"]),
                "epsChange": _calc_pct_change(current["eps"], year_ago["eps"]),
                "marginChange": round(current["netMargin"] - year_ago["netMargin"], 2) if year_ago["netMargin"] else None,
            }

    return {
        "latest": quarters[0] if quarters else None,
        "quarters": quarters[:4],  # Last 4 quarters for comparison view
        "yoyComparison": yoy_comparison,
    }


def _calc_pct_change(current, previous):
    """Calculate percentage change between two values."""
    current = _safe_float(current, None)
    previous = _safe_float(previous, None)
    if current is None or previous is None or previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 2)


def _generate_smart_insights(quarterly_comparison: dict, balance_sheet: dict, cash_flow: dict, earnings: dict, profile: dict) -> dict:
    """
    Analyze financial data and generate smart insights.
    Returns warnings (red flags), positives (green flags), and key metrics to watch.
    """
    warnings = []
    positives = []
    metrics = []

    yoy = quarterly_comparison.get("yoyComparison", {}) if quarterly_comparison else {}
    latest = quarterly_comparison.get("latest", {}) if quarterly_comparison else {}

    # === EARNINGS & REVENUE ANALYSIS ===
    if yoy:
        # Revenue decline warning
        rev_change = yoy.get("revenueChange")
        if rev_change is not None:
            if rev_change < -10:
                warnings.append({
                    "type": "revenue_decline",
                    "severity": "high",
                    "title": "Significant Revenue Decline",
                    "message": f"Revenue dropped {abs(rev_change):.1f}% YoY - indicates weakening demand or market share loss",
                    "value": rev_change
                })
            elif rev_change < -5:
                warnings.append({
                    "type": "revenue_decline",
                    "severity": "medium",
                    "title": "Revenue Decline",
                    "message": f"Revenue down {abs(rev_change):.1f}% YoY - monitor for sustained trend",
                    "value": rev_change
                })
            elif rev_change > 15:
                positives.append({
                    "type": "revenue_growth",
                    "title": "Strong Revenue Growth",
                    "message": f"Revenue up {rev_change:.1f}% YoY - healthy demand",
                    "value": rev_change
                })

        # EPS change
        eps_change = yoy.get("epsChange")
        if eps_change is not None:
            if eps_change < -50:
                warnings.append({
                    "type": "eps_collapse",
                    "severity": "high",
                    "title": "EPS Collapse",
                    "message": f"Earnings per share down {abs(eps_change):.1f}% YoY - serious profitability concern",
                    "value": eps_change
                })
            elif eps_change < -20:
                warnings.append({
                    "type": "eps_decline",
                    "severity": "medium",
                    "title": "EPS Decline",
                    "message": f"Earnings per share down {abs(eps_change):.1f}% YoY",
                    "value": eps_change
                })
            elif eps_change > 20:
                positives.append({
                    "type": "eps_growth",
                    "title": "Strong EPS Growth",
                    "message": f"Earnings per share up {eps_change:.1f}% YoY",
                    "value": eps_change
                })

        # Margin compression
        margin_change = yoy.get("marginChange")
        if margin_change is not None:
            if margin_change < -5:
                warnings.append({
                    "type": "margin_compression",
                    "severity": "high",
                    "title": "Margin Compression",
                    "message": f"Net margin contracted {abs(margin_change):.1f}pp YoY - pricing pressure or cost increases",
                    "value": margin_change
                })
            elif margin_change < -2:
                warnings.append({
                    "type": "margin_compression",
                    "severity": "medium",
                    "title": "Margin Pressure",
                    "message": f"Net margin down {abs(margin_change):.1f}pp YoY",
                    "value": margin_change
                })
            elif margin_change > 3:
                positives.append({
                    "type": "margin_expansion",
                    "title": "Margin Expansion",
                    "message": f"Net margin improved {margin_change:.1f}pp YoY - better cost control",
                    "value": margin_change
                })

    # === MARGIN ANALYSIS ===
    if latest:
        net_margin = latest.get("netMargin")
        gross_margin = latest.get("grossMargin")

        if net_margin is not None:
            if net_margin < 0:
                warnings.append({
                    "type": "negative_margin",
                    "severity": "high",
                    "title": "Negative Profitability",
                    "message": f"Net margin is {net_margin:.1f}% - company is losing money",
                    "value": net_margin
                })
            metrics.append({
                "name": "Net Margin",
                "value": f"{net_margin:.1f}%",
                "interpretation": "good" if net_margin > 15 else "neutral" if net_margin > 5 else "concern"
            })

        if gross_margin is not None:
            metrics.append({
                "name": "Gross Margin",
                "value": f"{gross_margin:.1f}%",
                "interpretation": "good" if gross_margin > 40 else "neutral" if gross_margin > 25 else "concern"
            })

    # === BALANCE SHEET ANALYSIS ===
    if balance_sheet:
        total_debt = _safe_float(balance_sheet.get("totalDebt", 0))
        total_cash = _safe_float(balance_sheet.get("totalCash", 0))
        equity = _safe_float(balance_sheet.get("shareholderEquity", 0))
        total_assets = _safe_float(balance_sheet.get("totalAssets", 0))

        # Debt-to-Equity ratio
        if equity and equity > 0:
            debt_to_equity = total_debt / equity
            metrics.append({
                "name": "Debt-to-Equity",
                "value": f"{debt_to_equity:.2f}x",
                "interpretation": "good" if debt_to_equity < 0.5 else "neutral" if debt_to_equity < 1.5 else "concern"
            })
            if debt_to_equity > 2:
                warnings.append({
                    "type": "high_leverage",
                    "severity": "medium",
                    "title": "High Debt Levels",
                    "message": f"Debt-to-equity of {debt_to_equity:.1f}x indicates significant leverage",
                    "value": debt_to_equity
                })
        elif equity and equity < 0:
            warnings.append({
                "type": "negative_equity",
                "severity": "high",
                "title": "Negative Shareholder Equity",
                "message": "Liabilities exceed assets - critical balance sheet concern",
                "value": equity
            })

        # Net cash position
        net_cash = total_cash - total_debt
        if net_cash > 0:
            positives.append({
                "type": "net_cash",
                "title": "Net Cash Position",
                "message": f"Company has ${net_cash/1e9:.1f}B more cash than debt",
                "value": net_cash
            })
        elif total_debt > total_cash * 3:
            warnings.append({
                "type": "debt_burden",
                "severity": "medium",
                "title": "Significant Debt Burden",
                "message": f"Debt (${total_debt/1e9:.1f}B) significantly exceeds cash (${total_cash/1e9:.1f}B)",
                "value": total_debt - total_cash
            })

    # === CASH FLOW ANALYSIS ===
    if cash_flow:
        operating_cf = _safe_float(cash_flow.get("operatingCashFlow", 0))
        free_cf = _safe_float(cash_flow.get("freeCashFlow", 0))
        capex = _safe_float(cash_flow.get("capex", 0))

        if free_cf < 0:
            warnings.append({
                "type": "negative_fcf",
                "severity": "medium",
                "title": "Negative Free Cash Flow",
                "message": f"FCF of ${free_cf/1e9:.1f}B - company burning cash",
                "value": free_cf
            })
        elif free_cf > 0:
            metrics.append({
                "name": "Free Cash Flow",
                "value": f"${free_cf/1e9:.1f}B",
                "interpretation": "good"
            })

        if operating_cf < 0:
            warnings.append({
                "type": "negative_operating_cf",
                "severity": "high",
                "title": "Negative Operating Cash Flow",
                "message": "Core operations not generating cash - sustainability concern",
                "value": operating_cf
            })

    # === VALUATION CONTEXT ===
    if profile:
        pe = _safe_float(profile.get("pe"), None)
        if pe is not None:
            if pe > 50:
                warnings.append({
                    "type": "high_valuation",
                    "severity": "low",
                    "title": "High Valuation",
                    "message": f"P/E of {pe:.1f}x implies high growth expectations",
                    "value": pe
                })
            elif pe < 0:
                warnings.append({
                    "type": "negative_pe",
                    "severity": "medium",
                    "title": "Negative P/E",
                    "message": "Company has negative earnings",
                    "value": pe
                })
            metrics.append({
                "name": "P/E Ratio",
                "value": f"{pe:.1f}x" if pe > 0 else "N/A (negative)",
                "interpretation": "good" if 10 < pe < 25 else "neutral" if pe > 0 else "concern"
            })

    # Sort warnings by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    warnings.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 2))

    return {
        "warnings": warnings,
        "positives": positives,
        "keyMetrics": metrics,
        "summary": {
            "warningCount": len(warnings),
            "highSeverityCount": len([w for w in warnings if w.get("severity") == "high"]),
            "positiveCount": len(positives),
        }
    }


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


@router.get("/{symbol}/cache-status")
async def get_cache_status(symbol: str):
    """
    Get cache status for a symbol - shows what's cached and when it expires.
    Useful for monitoring API usage.
    """
    return fmp_cache.get_cache_status(symbol.upper())


@router.delete("/{symbol}/cache")
async def clear_symbol_cache(symbol: str):
    """
    Clear all cached data for a symbol to force fresh API calls.
    Clears both FMP API cache and LLM insights cache.
    """
    symbol = symbol.upper()
    fmp_cache.clear_cache(symbol)
    insights_invalidated = insights_cache.invalidate(symbol)
    return {
        "message": f"All cache cleared for {symbol}",
        "symbol": symbol,
        "fmpCacheCleared": True,
        "insightsCacheCleared": insights_invalidated
    }


@router.get("/{symbol}/market-feed")
async def get_market_feed(symbol: str):
    """
    Get market feed data: news, insider trading, and senate trades for a symbol.
    Returns data for the two-column layout (news on left, trades on right).
    """
    symbol = symbol.upper()

    try:
        # Fetch all feed data in parallel
        news_task = fmp_cache.get("stock_news", symbol, limit=10)
        insider_task = fmp_cache.get("insider_trading", symbol, limit=10)
        senate_task = fmp_cache.get("senate_trades", symbol, limit=10)

        results = await asyncio.gather(
            news_task, insider_task, senate_task,
            return_exceptions=True
        )

        news, insider, senate = results

        # Handle exceptions gracefully
        if isinstance(news, Exception):
            news = []
        if isinstance(insider, Exception):
            insider = []
        if isinstance(senate, Exception):
            senate = []

        # Process news items
        processed_news = []
        for item in (news or [])[:10]:
            processed_news.append({
                "title": item.get("title"),
                "publisher": item.get("publisher"),
                "publishedDate": item.get("publishedDate"),
                "image": item.get("image"),
                "url": item.get("url"),
                "text": item.get("text", "")[:200] + "..." if item.get("text") else None,
            })

        # Process insider trades
        processed_insider = []
        for item in (insider or [])[:10]:
            processed_insider.append({
                "filingDate": item.get("filingDate"),
                "transactionDate": item.get("transactionDate"),
                "reportingName": item.get("reportingName"),
                "typeOfOwner": item.get("typeOfOwner"),
                "transactionType": item.get("transactionType"),
                "securitiesTransacted": item.get("securitiesTransacted"),
                "price": item.get("price"),
                "securityName": item.get("securityName"),
                "formType": item.get("formType"),
                "url": item.get("url"),
            })

        # Process senate trades
        processed_senate = []
        for item in (senate or [])[:10]:
            processed_senate.append({
                "disclosureDate": item.get("disclosureDate"),
                "transactionDate": item.get("transactionDate"),
                "firstName": item.get("firstName"),
                "lastName": item.get("lastName"),
                "office": item.get("office"),
                "district": item.get("district"),
                "owner": item.get("owner"),
                "type": item.get("type"),  # Buy/Sale
                "amount": item.get("amount"),
                "assetDescription": item.get("assetDescription"),
                "link": item.get("link"),
            })

        return {
            "symbol": symbol,
            "news": processed_news,
            "insiderTrades": processed_insider,
            "senateTrades": processed_senate,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _process_analyst_data(price_target: dict, grades_consensus: dict, current_price) -> dict:
    """
    Process analyst data into a summary format for the overview.
    Includes consensus rating, price target, and upside/downside.
    """
    if not price_target and not grades_consensus:
        return None

    result = {
        "consensus": None,
        "priceTarget": None,
        "totalAnalysts": 0,
    }

    # Process grades consensus (Strong Buy, Buy, Hold, Sell, Strong Sell)
    if grades_consensus:
        strong_buy = _safe_int(grades_consensus.get("strongBuy", 0))
        buy = _safe_int(grades_consensus.get("buy", 0))
        hold = _safe_int(grades_consensus.get("hold", 0))
        sell = _safe_int(grades_consensus.get("sell", 0))
        strong_sell = _safe_int(grades_consensus.get("strongSell", 0))

        total = strong_buy + buy + hold + sell + strong_sell
        result["totalAnalysts"] = total

        if total > 0:
            # Calculate weighted score (5=Strong Buy, 1=Strong Sell)
            weighted_score = (
                (strong_buy * 5) + (buy * 4) + (hold * 3) + (sell * 2) + (strong_sell * 1)
            ) / total

            # Determine consensus label
            if weighted_score >= 4.5:
                consensus_label = "Strong Buy"
            elif weighted_score >= 3.5:
                consensus_label = "Buy"
            elif weighted_score >= 2.5:
                consensus_label = "Hold"
            elif weighted_score >= 1.5:
                consensus_label = "Sell"
            else:
                consensus_label = "Strong Sell"

            result["consensus"] = {
                "rating": consensus_label,
                "score": round(weighted_score, 2),
                "strongBuy": strong_buy,
                "buy": buy,
                "hold": hold,
                "sell": sell,
                "strongSell": strong_sell,
            }

    # Process price targets
    if price_target:
        target_high = _safe_float(price_target.get("targetHigh"), None)
        target_low = _safe_float(price_target.get("targetLow"), None)
        target_median = _safe_float(price_target.get("targetMedian"), None)
        target_consensus = _safe_float(price_target.get("targetConsensus"), None)
        current = _safe_float(current_price, None)

        if target_consensus and current:
            upside = ((target_consensus - current) / current) * 100

            result["priceTarget"] = {
                "high": target_high,
                "low": target_low,
                "median": target_median,
                "consensus": target_consensus,
                "current": current,
                "upside": round(upside, 2),
            }

    return result if result["consensus"] or result["priceTarget"] else None


@router.get("/{symbol}/analyst-ratings")
async def get_analyst_ratings(symbol: str):
    """
    Get detailed analyst ratings including:
    - Consensus rating (Strong Buy/Buy/Hold/Sell/Strong Sell)
    - Price targets (high, low, median, consensus)
    - Recent upgrades/downgrades with firm names
    """
    symbol = symbol.upper()

    try:
        # Fetch all analyst data in parallel
        price_target_task = fmp_cache.get("price_target_consensus", symbol)
        grades_consensus_task = fmp_cache.get("analyst_grades_consensus", symbol)
        grades_history_task = fmp_cache.get("analyst_grades", symbol, limit=15)
        profile_task = fmp_cache.get("profile", symbol)

        results = await asyncio.gather(
            price_target_task, grades_consensus_task, grades_history_task, profile_task,
            return_exceptions=True
        )

        price_target, grades_consensus, grades_history, profile = results

        # Handle exceptions
        if isinstance(price_target, Exception):
            price_target = {}
        if isinstance(grades_consensus, Exception):
            grades_consensus = {}
        if isinstance(grades_history, Exception):
            grades_history = []
        if isinstance(profile, Exception):
            profile = {}

        current_price = profile.get("price")

        # Process consensus data
        analyst_summary = _process_analyst_data(price_target, grades_consensus, current_price)

        # Process recent grades/actions
        recent_actions = []
        for grade in (grades_history or [])[:15]:
            action = grade.get("action") or grade.get("gradingAction")
            previous = grade.get("previousGrade") or grade.get("previousScore")
            new_grade = grade.get("newGrade") or grade.get("newScore") or grade.get("grade")

            recent_actions.append({
                "date": grade.get("date"),
                "firm": grade.get("gradingCompany") or grade.get("company"),
                "action": action,  # upgrade, downgrade, maintain, init
                "previousGrade": previous,
                "newGrade": new_grade,
            })

        return {
            "symbol": symbol,
            "currentPrice": current_price,
            "consensus": analyst_summary.get("consensus") if analyst_summary else None,
            "priceTarget": analyst_summary.get("priceTarget") if analyst_summary else None,
            "totalAnalysts": analyst_summary.get("totalAnalysts", 0) if analyst_summary else 0,
            "recentActions": recent_actions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
