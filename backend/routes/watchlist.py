"""
Watchlist API Routes

Endpoints for managing the user's stock watchlist.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
import asyncio

from services.watchlist_service import watchlist_service
from services.fmp_cache import fmp_cache
from utils import safe_float, find_price_near_date
from routes.portfolio import _extract_next_earnings_date


router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddToWatchlistRequest(BaseModel):
    notes: Optional[str] = None


class UpdateNotesRequest(BaseModel):
    notes: str


@router.get("")
async def get_watchlist(include_prices: bool = True):
    """
    Get all watchlist items with optional price data.

    Args:
        include_prices: If True, fetch current price data for each stock
    """
    items = watchlist_service.get_all()

    if not items:
        return {"items": [], "count": 0}

    if not include_prices:
        return {"items": items, "count": len(items)}

    # Fetch price data for all symbols in parallel
    async def fetch_stock_data(item):
        symbol = item["symbol"]
        try:
            profile_task = fmp_cache.get("profile", symbol)
            earnings_cal_task = fmp_cache.get("earnings_calendar", symbol)
            earnings_hist_task = fmp_cache.get("earnings", symbol)
            profile, earnings_cal, earnings_hist = await asyncio.gather(
                profile_task, earnings_cal_task, earnings_hist_task
            )
            if not profile:
                return {
                    **item,
                    "name": None,
                    "image": None,
                    "price": None,
                    "change": None,
                    "changePercent": None,
                    "momChangePercent": None,
                    "yoyChangePercent": None,
                    "nextEarningsDate": None,
                    "error": "Profile not found"
                }

            # Calculate MoM and YoY changes
            price_changes = await _calculate_price_changes(symbol)

            next_earnings_date = _extract_next_earnings_date(earnings_cal, earnings_hist)

            return {
                **item,
                "name": profile.get("companyName"),
                "image": profile.get("image"),
                "sector": profile.get("sector"),
                "industry": profile.get("industry"),
                "price": profile.get("price"),
                "change": profile.get("change"),
                "changePercent": profile.get("changePercentage"),
                "momChangePercent": price_changes.get("momChangePercent"),
                "yoyChangePercent": price_changes.get("yoyChangePercent"),
                "nextEarningsDate": next_earnings_date,
            }
        except Exception as e:
            return {
                **item,
                "error": str(e)
            }

    # Fetch all in parallel
    enriched_items = await asyncio.gather(
        *[fetch_stock_data(item) for item in items]
    )

    return {"items": list(enriched_items), "count": len(enriched_items)}


async def _calculate_price_changes(symbol: str) -> dict:
    """Calculate MoM and YoY price changes using historical data."""
    from datetime import datetime, timedelta

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

        current_price = safe_float(prices[0].get("close") or prices[0].get("adjClose"), None)
        mom_price = safe_float(find_price_near_date(prices, one_month_ago), None)
        yoy_price = safe_float(find_price_near_date(prices, one_year_ago), None)

        result = {"momChangePercent": None, "yoyChangePercent": None}

        if current_price and mom_price:
            result["momChangePercent"] = round((current_price - mom_price) / mom_price * 100, 2)

        if current_price and yoy_price:
            result["yoyChangePercent"] = round((current_price - yoy_price) / yoy_price * 100, 2)

        return result
    except Exception as e:
        print(f"Error calculating price changes for {symbol}: {e}")
        return {"momChangePercent": None, "yoyChangePercent": None}


@router.get("/{symbol}")
async def get_watchlist_item(symbol: str):
    """Get a specific watchlist item."""
    item = watchlist_service.get(symbol)
    if not item:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} not in watchlist")
    return item


@router.get("/{symbol}/status")
async def check_watchlist_status(symbol: str):
    """Check if a symbol is in the watchlist."""
    is_in_watchlist = watchlist_service.is_in_watchlist(symbol)
    return {
        "symbol": symbol.upper(),
        "inWatchlist": is_in_watchlist
    }


@router.post("/{symbol}")
async def add_to_watchlist(symbol: str, request: AddToWatchlistRequest = None):
    """Add a stock to the watchlist."""
    notes = request.notes if request else None
    result = watchlist_service.add(symbol, notes)
    return {
        "message": f"{symbol.upper()} {'already in' if result.get('alreadyExists') else 'added to'} watchlist",
        **result
    }


@router.delete("/{symbol}")
async def remove_from_watchlist(symbol: str):
    """Remove a stock from the watchlist."""
    removed = watchlist_service.remove(symbol)
    if not removed:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} not in watchlist")
    return {
        "message": f"{symbol.upper()} removed from watchlist",
        "symbol": symbol.upper(),
        "removed": True
    }


@router.patch("/{symbol}/notes")
async def update_watchlist_notes(symbol: str, request: UpdateNotesRequest):
    """Update notes for a watchlist item."""
    result = watchlist_service.update_notes(symbol, request.notes)
    if not result:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} not in watchlist")
    return {
        "message": f"Notes updated for {symbol.upper()}",
        **result
    }
