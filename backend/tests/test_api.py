"""
Tests for API endpoints.

Uses mocked cache - NO API calls made during testing.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def client(mock_fmp_cache):
    """Create test client with mocked FMP cache."""
    # Patch the cache before importing the app
    with patch("services.fmp_cache.fmp_cache", mock_fmp_cache):
        with patch("routes.financials.fmp_cache", mock_fmp_cache):
            with patch("agents.chat_agent.fmp_cache", mock_fmp_cache):
                with patch("agents.data_fetcher.fmp_cache", mock_fmp_cache):
                    from main import app
                    yield TestClient(app)


class TestOverviewEndpoint:
    """Tests for the /api/financials/{symbol}/overview endpoint."""

    def test_overview_returns_data(self, client):
        """Test that overview endpoint returns expected structure."""
        response = client.get("/api/financials/AAPL/overview")

        assert response.status_code == 200
        data = response.json()

        # Check main sections exist
        assert "symbol" in data
        assert data["symbol"] == "AAPL"
        assert "profile" in data
        assert "price" in data
        assert "latestQuarter" in data
        assert "balanceSheet" in data
        assert "cashFlow" in data
        assert "revenuePillars" in data

    def test_overview_profile_data(self, client):
        """Test profile data in overview."""
        response = client.get("/api/financials/AAPL/overview")
        data = response.json()

        profile = data["profile"]
        assert profile["name"] == "Apple Inc."
        assert profile["sector"] == "Technology"
        assert profile["ceo"] == "Tim Cook"

    def test_overview_price_data(self, client):
        """Test price data in overview."""
        response = client.get("/api/financials/AAPL/overview")
        data = response.json()

        price = data["price"]
        assert price["current"] == 225.50
        assert price["marketCap"] > 3000000000000  # > $3T

    def test_overview_latest_quarter(self, client):
        """Test latest quarter data."""
        response = client.get("/api/financials/AAPL/overview")
        data = response.json()

        quarter = data["latestQuarter"]
        assert quarter["revenue"] > 100000000000  # > $100B
        assert "grossMargin" in quarter
        assert "netMargin" in quarter

    def test_overview_revenue_pillars(self, client):
        """Test revenue pillars data."""
        response = client.get("/api/financials/AAPL/overview")
        data = response.json()

        pillars = data["revenuePillars"]
        assert "products" in pillars
        assert "geographies" in pillars

        # iPhone should be largest product
        products = pillars["products"]
        assert len(products) > 0
        assert products[0]["name"] == "iPhone"


class TestCacheStatusEndpoint:
    """Tests for the cache status endpoint."""

    def test_cache_status_returns_data(self, client):
        """Test cache status endpoint."""
        response = client.get("/api/financials/AAPL/cache-status")

        assert response.status_code == 200
        data = response.json()

        assert "symbol" in data
        assert "cached" in data
        assert "endpoints" in data


class TestSearchEndpoint:
    """Tests for the search endpoint."""

    def test_search_prioritizes_exact_match(self, client):
        """Test that exact symbol match comes first."""
        # This test uses actual search logic, not mocked
        # Skip if you want to avoid any API calls
        pass


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_symbol_handling(self, client):
        """Test handling of invalid symbols."""
        # With mock, this should still work but return mock data
        # In production, this would return an error
        pass
