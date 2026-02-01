from fastapi import APIRouter, HTTPException
from services.fmp_service import fmp_service

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/search")
async def search_companies(q: str, limit: int = 10):
    """
    Search for companies by name or symbol.
    Prioritizes exact symbol matches and stocks over ETFs.
    """
    if not q or len(q) < 1:
        raise HTTPException(status_code=400, detail="Search query required")

    try:
        # Fetch more results to allow for filtering/sorting
        results = await fmp_service.search_companies(q, limit=min(limit * 3, 30))

        query_upper = q.upper()

        def sort_key(item):
            symbol = item.get("symbol", "").upper()
            name = item.get("name", "").lower()

            # Priority 1: Exact symbol match (AMZN → Amazon)
            if symbol == query_upper:
                return (0, 0, symbol)

            # Priority 2: Symbol starts with query
            if symbol.startswith(query_upper):
                # Prefer shorter symbols (AMZN over AMZN.PA)
                is_etf = "etf" in name.lower() or "yield" in name.lower() or "daily" in name.lower()
                return (1, 1 if is_etf else 0, len(symbol), symbol)

            # Priority 3: Stocks over ETFs for other matches
            is_etf = "etf" in name.lower() or "yield" in name.lower() or "daily" in name.lower()
            return (2, 1 if is_etf else 0, symbol)

        # Sort and limit results
        sorted_results = sorted(results, key=sort_key)[:limit]

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
