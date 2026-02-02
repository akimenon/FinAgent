from fastapi import APIRouter, HTTPException
import asyncio
from services.fmp_service import fmp_service

router = APIRouter(prefix="/api/companies", tags=["companies"])

# Curated sector lists
SECTOR_STOCKS = {
    "tech": ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "NFLX", "CRM", "ORCL", "ADBE", "CSCO"],
    "semiconductors": ["NVDA", "AMD", "INTC", "TSM", "AVGO", "QCOM", "MU", "ASML", "TXN", "AMAT"],
    "ev": ["TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "F", "GM", "HYND", "STLA"],
}


@router.get("/market-movers")
async def get_market_movers():
    """
    Get market movers: top gainers, top losers.
    Filters out stocks trading below $5.
    Returns max 10 of each category.
    """
    try:
        # Fetch more than needed to account for filtering
        gainers_task = fmp_service.get_top_gainers(limit=30)
        losers_task = fmp_service.get_top_losers(limit=30)

        gainers, losers = await asyncio.gather(
            gainers_task, losers_task,
            return_exceptions=True
        )

        if isinstance(gainers, Exception):
            gainers = []
        if isinstance(losers, Exception):
            losers = []

        # Process gainers - filter out stocks below $5
        processed_gainers = []
        for item in (gainers or []):
            price = item.get("price", 0) or 0
            if price >= 5 and len(processed_gainers) < 10:
                processed_gainers.append({
                    "symbol": item.get("symbol"),
                    "name": item.get("name"),
                    "price": price,
                    "change": item.get("change"),
                    "changePercent": item.get("changesPercentage"),
                })

        # Process losers - filter out stocks below $5
        processed_losers = []
        for item in (losers or []):
            price = item.get("price", 0) or 0
            if price >= 5 and len(processed_losers) < 10:
                processed_losers.append({
                    "symbol": item.get("symbol"),
                    "name": item.get("name"),
                    "price": price,
                    "change": item.get("change"),
                    "changePercent": item.get("changesPercentage"),
                })

        return {
            "gainers": processed_gainers,
            "losers": processed_losers,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-indices")
async def get_market_indices():
    """
    Get real-time quotes for major market indicators.
    Returns indices, ETFs, crypto, and commodities.
    """
    # All market indicators grouped by category
    indicators = [
        # Major indices
        {"symbol": "^GSPC", "name": "S&P 500", "category": "index"},
        {"symbol": "^DJI", "name": "Dow", "category": "index"},
        {"symbol": "^IXIC", "name": "NASDAQ", "category": "index"},
        # Crypto
        {"symbol": "BTCUSD", "name": "BTC", "category": "crypto"},
        {"symbol": "ETHUSD", "name": "ETH", "category": "crypto"},
        # Commodities
        {"symbol": "GCUSD", "name": "Gold", "category": "commodity"},
        {"symbol": "SIUSD", "name": "Silver", "category": "commodity"},
    ]

    try:
        quote_tasks = [fmp_service.get_quote(ind["symbol"]) for ind in indicators]
        quotes = await asyncio.gather(*quote_tasks, return_exceptions=True)

        result = []
        for ind, quote in zip(indicators, quotes):
            if isinstance(quote, Exception) or not quote:
                result.append({
                    "symbol": ind["symbol"],
                    "name": ind["name"],
                    "category": ind["category"],
                    "price": None,
                    "change": None,
                    "changePercent": None,
                })
            else:
                price = quote.get("price")
                change = quote.get("change")
                change_pct = quote.get("changesPercentage")
                # Calculate change percent if not provided
                if change_pct is None and price and change:
                    prev_price = price - change
                    if prev_price != 0:
                        change_pct = (change / prev_price) * 100
                result.append({
                    "symbol": ind["symbol"],
                    "name": ind["name"],
                    "category": ind["category"],
                    "price": price,
                    "change": change,
                    "changePercent": change_pct,
                })

        return {"indices": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/{sector}")
async def get_sector_stocks(sector: str):
    """
    Get curated list of stocks for a sector with real-time quotes.
    Available sectors: tech, semiconductors, ev
    """
    sector = sector.lower()
    if sector not in SECTOR_STOCKS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sector. Available: {', '.join(SECTOR_STOCKS.keys())}"
        )

    symbols = SECTOR_STOCKS[sector]

    # Fetch quotes for all symbols in parallel
    quote_tasks = [fmp_service.get_quote(symbol) for symbol in symbols]
    quotes = await asyncio.gather(*quote_tasks, return_exceptions=True)

    stocks = []
    for symbol, quote in zip(symbols, quotes):
        if isinstance(quote, Exception) or not quote:
            stocks.append({
                "symbol": symbol,
                "price": None,
                "changePercent": None,
            })
        else:
            stocks.append({
                "symbol": symbol,
                "name": quote.get("name"),
                "price": quote.get("price"),
                "changePercent": quote.get("changePercentage"),
            })

    return {
        "sector": sector,
        "stocks": stocks,
    }


@router.get("/search")
async def search_companies(q: str, limit: int = 10):
    """
    Search for companies by name or symbol.
    Prioritizes exact symbol matches and stocks over ETFs.

    FMP's search-name endpoint has a quirk where it doesn't always return
    exact symbol matches (e.g., searching "AMZN" doesn't return Amazon).
    We work around this by also checking the profile endpoint for exact matches.
    """
    if not q or len(q) < 1:
        raise HTTPException(status_code=400, detail="Search query required")

    try:
        query_upper = q.upper().strip()

        # Fetch search results and check for exact symbol match in parallel
        search_task = fmp_service.search_companies(q, limit=min(limit * 3, 30))

        # If query looks like a symbol (1-5 uppercase letters), also try direct profile lookup
        exact_match = None
        if len(query_upper) <= 5 and query_upper.isalpha():
            try:
                profile = await fmp_service.get_company_profile(query_upper)
                if profile and profile.get("symbol") == query_upper:
                    exact_match = {
                        "symbol": profile.get("symbol"),
                        "name": profile.get("companyName"),
                        "currency": "USD",
                        "exchangeFullName": profile.get("exchange", ""),
                        "exchange": profile.get("exchange", ""),
                    }
            except:
                pass

        results = await search_task

        # US exchanges get priority
        us_exchanges = {"NASDAQ", "NYSE", "AMEX", "NASDAQ Global Select", "NASDAQ Global Market",
                        "New York Stock Exchange", "New York Stock Exchange Arca"}

        def sort_key(item):
            symbol = item.get("symbol", "").upper()
            name = item.get("name", "").lower()
            exchange = item.get("exchangeFullName", "") or item.get("exchange", "")

            is_us = exchange in us_exchanges or not any(c in symbol for c in ".:")
            is_etf = "etf" in name or "yield" in name or "daily" in name or "shares" in name or "etp" in name or "tracker" in name

            # Priority 1: Exact symbol match (AMZN → Amazon)
            if symbol == query_upper:
                return (0, 0 if is_us else 1, symbol)

            # Priority 2: Symbol starts with query + US exchange + not ETF
            if symbol.startswith(query_upper):
                return (1, 0 if is_us else 1, 1 if is_etf else 0, len(symbol), symbol)

            # Priority 3: Name contains query + US exchange + not ETF
            return (2, 0 if is_us else 1, 1 if is_etf else 0, symbol)

        # Sort results
        sorted_results = sorted(results, key=sort_key)

        # If we found an exact match via profile lookup, ensure it's first
        if exact_match:
            # Remove any duplicate from search results
            sorted_results = [r for r in sorted_results if r.get("symbol") != exact_match["symbol"]]
            sorted_results.insert(0, exact_match)

        # Limit results
        sorted_results = sorted_results[:limit]

        return {
            "query": q,
            "results": sorted_results,
            "count": len(sorted_results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}")
async def get_company(symbol: str):
    """
    Get company details by symbol.
    """
    try:
        profile = await fmp_service.get_company_profile(symbol.upper())
        if not profile:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/profile")
async def get_company_profile(symbol: str):
    """
    Get detailed company profile.
    """
    try:
        profile = await fmp_service.get_company_profile(symbol.upper())
        if not profile:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")
        return {
            "symbol": symbol.upper(),
            "profile": profile,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
