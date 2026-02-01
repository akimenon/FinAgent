"""
Pytest configuration and fixtures.

Uses cached JSON files as mock data - no API calls during testing.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(symbol: str, endpoint: str):
    """Load fixture data from JSON file."""
    file_path = FIXTURES_DIR / symbol.upper() / f"{endpoint}.json"
    if file_path.exists():
        with open(file_path, "r") as f:
            data = json.load(f)
            return data.get("data")
    return None


class MockFMPCache:
    """Mock FMP cache that returns fixture data instead of calling API."""

    async def get(self, endpoint: str, symbol: str, **kwargs):
        """Return fixture data for the endpoint."""
        data = load_fixture(symbol, endpoint)
        if data is None:
            raise ValueError(f"No fixture found for {symbol}/{endpoint}")
        return data

    def get_cache_status(self, symbol: str):
        """Return mock cache status."""
        symbol_dir = FIXTURES_DIR / symbol.upper()
        if not symbol_dir.exists():
            return {"symbol": symbol, "cached": False, "endpoints": {}}

        endpoints = {}
        for file_path in symbol_dir.glob("*.json"):
            endpoints[file_path.stem] = {
                "fetched_at": "2026-01-31T12:00:00",
                "is_fresh": True,
                "ttl_days": 90
            }

        return {"symbol": symbol, "cached": True, "endpoints": endpoints}

    def clear_cache(self, symbol=None, endpoint=None):
        """Mock clear cache - does nothing in tests."""
        pass


@pytest.fixture
def mock_fmp_cache():
    """Fixture that provides a mock FMP cache."""
    return MockFMPCache()


@pytest.fixture
def aapl_profile():
    """Load AAPL profile fixture."""
    return load_fixture("AAPL", "profile")


@pytest.fixture
def aapl_income():
    """Load AAPL income statement fixture."""
    return load_fixture("AAPL", "income_quarterly")


@pytest.fixture
def aapl_balance_sheet():
    """Load AAPL balance sheet fixture."""
    return load_fixture("AAPL", "balance_sheet")


@pytest.fixture
def aapl_cash_flow():
    """Load AAPL cash flow fixture."""
    return load_fixture("AAPL", "cash_flow")


@pytest.fixture
def aapl_earnings():
    """Load AAPL earnings fixture."""
    return load_fixture("AAPL", "earnings")


@pytest.fixture
def aapl_product_segments():
    """Load AAPL product segments fixture."""
    return load_fixture("AAPL", "product_segments")


@pytest.fixture
def aapl_geo_segments():
    """Load AAPL geographic segments fixture."""
    return load_fixture("AAPL", "geo_segments")


@pytest.fixture
def all_aapl_data(aapl_profile, aapl_income, aapl_balance_sheet,
                  aapl_cash_flow, aapl_earnings, aapl_product_segments,
                  aapl_geo_segments):
    """Load all AAPL fixtures as a combined dict."""
    return {
        "profile": aapl_profile,
        "income_quarterly": aapl_income,
        "balance_sheet": aapl_balance_sheet,
        "cash_flow": aapl_cash_flow,
        "earnings": aapl_earnings,
        "product_segments": aapl_product_segments,
        "geo_segments": aapl_geo_segments,
    }
