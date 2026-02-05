"""
Portfolio API Routes

Endpoints for managing user portfolio holdings with prices and ROI calculations.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from pathlib import Path
import asyncio
import json

from services.portfolio_service import portfolio_service, categorize_ticker
from services.crypto_service import crypto_service
from services.portfolio_snapshot_service import portfolio_snapshot_service
from services.fmp_cache import fmp_cache


router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

PIN_FILE = Path(__file__).parent.parent / "data" / "portfolio" / "pin.json"


def _read_pin() -> str:
    """Read the stored PIN from file. Returns empty string if no PIN is set."""
    if not PIN_FILE.exists():
        return ""
    try:
        data = json.loads(PIN_FILE.read_text())
        return data.get("pin", "")
    except (json.JSONDecodeError, OSError):
        return ""


def _write_pin(pin: str):
    """Write PIN to file."""
    PIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PIN_FILE.write_text(json.dumps({"pin": pin}))


class VerifyPinRequest(BaseModel):
    pin: str


class SetPinRequest(BaseModel):
    pin: str
    current_pin: str = ""


class AddHoldingRequest(BaseModel):
    ticker: str
    quantity: float
    costBasis: float
    accountName: str
    assetType: Optional[str] = None  # stock, etf, or crypto - auto-detected if not provided


class UpdateHoldingRequest(BaseModel):
    quantity: Optional[float] = None
    costBasis: Optional[float] = None
    accountName: Optional[str] = None


@router.post("/verify-pin")
async def verify_pin(request: VerifyPinRequest):
    """Verify the portfolio PIN. Returns verified=True if PIN matches or no PIN is configured."""
    stored_pin = _read_pin()
    if not stored_pin:
        return {"verified": True, "pinSet": False}
    return {"verified": request.pin == stored_pin, "pinSet": True}


@router.post("/set-pin")
async def set_pin(request: SetPinRequest):
    """Set or update the portfolio PIN. Requires current PIN if one is already set."""
    stored_pin = _read_pin()
    if stored_pin and request.current_pin != stored_pin:
        raise HTTPException(status_code=403, detail="Current PIN is incorrect")
    if not request.pin or len(request.pin) != 4 or not request.pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
    _write_pin(request.pin)
    return {"message": "PIN set successfully"}


@router.delete("/pin")
async def remove_pin(request: VerifyPinRequest):
    """Remove the portfolio PIN. Requires current PIN to remove."""
    stored_pin = _read_pin()
    if not stored_pin:
        return {"message": "No PIN is set"}
    if request.pin != stored_pin:
        raise HTTPException(status_code=403, detail="Incorrect PIN")
    if PIN_FILE.exists():
        PIN_FILE.unlink()
    return {"message": "PIN removed"}


@router.get("")
async def get_portfolio():
    """
    Get all portfolio holdings with current prices and ROI calculations.

    Returns holdings grouped by asset type with:
    - Current price
    - Total value
    - Gain/loss ($ and %)
    - Summary totals
    """
    holdings = portfolio_service.get_all()

    if not holdings:
        return {
            "holdings": [],
            "summary": {
                "totalValue": 0,
                "totalCost": 0,
                "totalGainLoss": 0,
                "totalGainLossPercent": 0,
                "byAssetType": {
                    "stock": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
                    "etf": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
                    "crypto": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
                    "custom": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
                    "cash": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
                },
            },
            "count": 0,
        }

    # Separate by asset type for different price fetching
    crypto_holdings = [h for h in holdings if h.get("assetType") == "crypto"]
    custom_holdings = [h for h in holdings if h.get("assetType") == "custom"]
    cash_holdings = [h for h in holdings if h.get("assetType") == "cash"]
    stock_etf_holdings = [h for h in holdings if h.get("assetType") not in ("crypto", "custom", "cash")]

    # Fetch prices in parallel
    enriched_holdings = []

    # Fetch stock/ETF prices
    async def fetch_stock_price(holding):
        ticker = holding["ticker"]
        try:
            profile = await fmp_cache.get("profile", ticker)
            price = profile.get("price") if profile else None
            name = profile.get("companyName") if profile else None
            image = profile.get("image") if profile else None
            industry = profile.get("industry") if profile else None

            return enrich_holding(holding, price, name, image, industry)
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return enrich_holding(holding, None, None, None, None)

    # Fetch crypto prices in batch
    crypto_prices = {}
    if crypto_holdings:
        crypto_tickers = list(set(h["ticker"] for h in crypto_holdings))
        crypto_prices = await crypto_service.get_prices_batch(crypto_tickers)

    def enrich_crypto_holding(holding):
        ticker = holding["ticker"]
        price_data = crypto_prices.get(ticker)
        price = price_data.get("price") if price_data else None
        return enrich_holding(holding, price, ticker, None, None)

    def enrich_holding(holding, price, name, image, industry=None):
        """Add price and ROI calculations to a holding."""
        quantity = holding.get("quantity", 0)
        cost_basis = holding.get("costBasis", 0)
        total_cost = quantity * cost_basis

        if price is not None:
            current_value = quantity * price
            gain_loss = current_value - total_cost
            gain_loss_percent = (gain_loss / total_cost * 100) if total_cost > 0 else 0
        else:
            current_value = None
            gain_loss = None
            gain_loss_percent = None

        return {
            **holding,
            "name": name,
            "image": image,
            "industry": industry,
            "currentPrice": price,
            "currentValue": current_value,
            "totalCost": total_cost,
            "gainLoss": gain_loss,
            "gainLossPercent": gain_loss_percent,
        }

    # Fetch all stock/ETF prices in parallel
    if stock_etf_holdings:
        stock_etf_results = await asyncio.gather(
            *[fetch_stock_price(h) for h in stock_etf_holdings]
        )
        enriched_holdings.extend(stock_etf_results)

    # Enrich crypto holdings
    for holding in crypto_holdings:
        enriched_holdings.append(enrich_crypto_holding(holding))

    # Enrich custom holdings (cost basis = current price, no external price fetch)
    for holding in custom_holdings:
        price = holding.get("costBasis", 0)
        enriched_holdings.append(enrich_holding(holding, price, holding["ticker"], None))

    # Enrich cash holdings (value = costBasis, no price fetch)
    for holding in cash_holdings:
        amount = holding.get("costBasis", 0)
        enriched_holdings.append(enrich_holding(holding, amount, "Cash", None))

    # Calculate summary
    summary = calculate_summary(enriched_holdings)

    return {
        "holdings": enriched_holdings,
        "summary": summary,
        "count": len(enriched_holdings),
    }


def calculate_summary(holdings):
    """Calculate portfolio summary statistics."""
    summary = {
        "totalValue": 0,
        "totalCost": 0,
        "totalGainLoss": 0,
        "totalGainLossPercent": 0,
        "byAssetType": {
            "stock": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
            "etf": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
            "crypto": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
            "custom": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
            "cash": {"count": 0, "value": 0, "cost": 0, "gainLoss": 0},
        },
    }

    for holding in holdings:
        asset_type = holding.get("assetType", "stock")
        total_cost = holding.get("totalCost", 0)
        current_value = holding.get("currentValue")
        gain_loss = holding.get("gainLoss")

        if asset_type in summary["byAssetType"]:
            summary["byAssetType"][asset_type]["count"] += 1
            summary["byAssetType"][asset_type]["cost"] += total_cost

            if current_value is not None:
                summary["byAssetType"][asset_type]["value"] += current_value
                summary["totalValue"] += current_value

            if gain_loss is not None:
                summary["byAssetType"][asset_type]["gainLoss"] += gain_loss
                summary["totalGainLoss"] += gain_loss

        # Exclude cash from totalCost (cash is not invested capital)
        if asset_type != "cash":
            summary["totalCost"] += total_cost

    # Calculate return % based on invested capital (excludes cash)
    if summary["totalCost"] > 0:
        summary["totalGainLossPercent"] = (
            summary["totalGainLoss"] / summary["totalCost"] * 100
        )

    return summary


@router.post("")
async def add_holding(request: AddHoldingRequest):
    """Add a new holding to the portfolio."""
    # Validate ticker exists (for stocks/ETFs)
    asset_type = request.assetType or categorize_ticker(request.ticker)

    if asset_type not in ("crypto", "custom", "cash"):
        # Verify stock/ETF exists via FMP
        profile = await fmp_cache.get("profile", request.ticker.upper())
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Ticker {request.ticker.upper()} not found"
            )

    holding = portfolio_service.add(
        ticker=request.ticker,
        quantity=request.quantity,
        cost_basis=request.costBasis,
        account_name=request.accountName,
        asset_type=asset_type,
    )

    return {
        "message": f"Added {request.quantity} {request.ticker.upper()} to portfolio",
        **holding,
    }


@router.put("/{holding_id}")
async def update_holding(holding_id: str, request: UpdateHoldingRequest):
    """Update an existing holding."""
    existing = portfolio_service.get(holding_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Holding {holding_id} not found")

    updated = portfolio_service.update(
        holding_id=holding_id,
        quantity=request.quantity,
        cost_basis=request.costBasis,
        account_name=request.accountName,
    )

    return {
        "message": f"Updated holding {holding_id}",
        **updated,
    }


@router.post("/snapshot")
async def take_snapshot(force: bool = False):
    """
    Take a daily snapshot of portfolio value.
    Skips if a snapshot has already been taken today (unless force=True).
    Called automatically on app load, or manually via the snapshot button.
    """
    # Skip if already taken today (unless forced)
    if not force and portfolio_snapshot_service.has_today_snapshot():
        return {"message": "Snapshot already taken today", "alreadyExists": True}

    # Get current portfolio with prices to calculate summary
    holdings = portfolio_service.get_all()
    if not holdings:
        return {"message": "No holdings to snapshot", "skipped": True}

    # Fetch prices (same logic as get_portfolio)
    crypto_holdings = [h for h in holdings if h.get("assetType") == "crypto"]
    custom_holdings = [h for h in holdings if h.get("assetType") == "custom"]
    cash_holdings = [h for h in holdings if h.get("assetType") == "cash"]
    stock_etf_holdings = [h for h in holdings if h.get("assetType") not in ("crypto", "custom", "cash")]

    enriched_holdings = []

    async def fetch_stock_price(holding):
        ticker = holding["ticker"]
        try:
            profile = await fmp_cache.get("profile", ticker)
            price = profile.get("price") if profile else None
            return _enrich_for_snapshot(holding, price)
        except Exception:
            return _enrich_for_snapshot(holding, None)

    crypto_prices = {}
    if crypto_holdings:
        crypto_tickers = list(set(h["ticker"] for h in crypto_holdings))
        crypto_prices = await crypto_service.get_prices_batch(crypto_tickers)

    if stock_etf_holdings:
        results = await asyncio.gather(
            *[fetch_stock_price(h) for h in stock_etf_holdings]
        )
        enriched_holdings.extend(results)

    for holding in crypto_holdings:
        price_data = crypto_prices.get(holding["ticker"])
        price = price_data.get("price") if price_data else None
        enriched_holdings.append(_enrich_for_snapshot(holding, price))

    # Custom holdings: cost basis = current price
    for holding in custom_holdings:
        enriched_holdings.append(_enrich_for_snapshot(holding, holding.get("costBasis", 0)))

    # Cash holdings: cost basis = value
    for holding in cash_holdings:
        enriched_holdings.append(_enrich_for_snapshot(holding, holding.get("costBasis", 0)))

    summary = calculate_summary(enriched_holdings)
    snapshot = portfolio_snapshot_service.save_snapshot(summary, force=force)

    return {"message": "Snapshot saved", **snapshot}


def _enrich_for_snapshot(holding, price):
    """Minimal enrichment for snapshot calculation."""
    quantity = holding.get("quantity", 0)
    cost_basis = holding.get("costBasis", 0)
    total_cost = quantity * cost_basis

    if price is not None:
        current_value = quantity * price
        gain_loss = current_value - total_cost
        gain_loss_percent = (gain_loss / total_cost * 100) if total_cost > 0 else 0
    else:
        current_value = None
        gain_loss = None
        gain_loss_percent = None

    return {
        **holding,
        "currentPrice": price,
        "currentValue": current_value,
        "totalCost": total_cost,
        "gainLoss": gain_loss,
        "gainLossPercent": gain_loss_percent,
    }


@router.get("/performance")
async def get_performance():
    """
    Get portfolio performance over various time periods (1W, 1M, 3M, YTD).
    Includes per-asset-type breakdown showing how stocks vs ETFs vs crypto moved.
    """
    return portfolio_snapshot_service.get_performance()


@router.get("/snapshots")
async def get_snapshots(days: int = 90):
    """Get portfolio snapshots for the last N days."""
    return portfolio_snapshot_service.get_snapshots(days=days)


@router.delete("/{holding_id}")
async def delete_holding(holding_id: str):
    """Delete a holding from the portfolio."""
    existing = portfolio_service.get(holding_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Holding {holding_id} not found")

    removed = portfolio_service.remove(holding_id)
    if not removed:
        raise HTTPException(status_code=500, detail="Failed to remove holding")

    return {
        "message": f"Removed {existing['ticker']} from portfolio",
        "id": holding_id,
        "removed": True,
    }


@router.get("/{holding_id}")
async def get_holding(holding_id: str):
    """Get a specific holding by ID."""
    holding = portfolio_service.get(holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail=f"Holding {holding_id} not found")
    return holding
