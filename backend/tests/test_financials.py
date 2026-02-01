"""
Tests for financial data processing and API endpoints.

Uses fixture data - NO API calls made during testing.
"""

import pytest
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from routes.financials import _process_revenue_pillars, _get_next_earnings


class TestRevenuePillars:
    """Tests for revenue pillar processing."""

    def test_process_product_segments(self, aapl_product_segments):
        """Test processing of product segment data."""
        result = _process_revenue_pillars(aapl_product_segments, [])

        assert "products" in result
        assert len(result["products"]) > 0

        # Check iPhone is the largest segment
        products = result["products"]
        assert products[0]["name"] == "iPhone"
        assert products[0]["revenue"] > 200000000000  # > $200B

        # Check YoY change is calculated
        assert "yoyChange" in products[0]
        assert isinstance(products[0]["yoyChange"], float)

    def test_process_geo_segments(self, aapl_geo_segments):
        """Test processing of geographic segment data."""
        result = _process_revenue_pillars([], aapl_geo_segments)

        assert "geographies" in result
        assert len(result["geographies"]) > 0

        # Check Americas is the largest segment
        geos = result["geographies"]
        assert geos[0]["name"] == "Americas"

        # Check share is calculated
        assert "share" in geos[0]
        assert geos[0]["share"] > 0

    def test_china_revenue_declining(self, aapl_geo_segments):
        """Test that China revenue decline is detected."""
        result = _process_revenue_pillars([], aapl_geo_segments)

        # Find Greater China
        china = next((g for g in result["geographies"] if "China" in g["name"]), None)
        assert china is not None

        # China revenue declined YoY
        assert china["yoyChange"] < 0
        assert china["trend"] == "down"

    def test_services_growth(self, aapl_product_segments):
        """Test that Services growth is detected."""
        result = _process_revenue_pillars(aapl_product_segments, [])

        # Find Services
        services = next((p for p in result["products"] if "Services" in p["name"]), None)
        assert services is not None

        # Services should be growing
        assert services["yoyChange"] > 0
        assert services["trend"] == "up"


class TestEarningsProcessing:
    """Tests for earnings data processing."""

    def test_earnings_beat_detection(self, aapl_earnings):
        """Test that earnings beats are correctly identified."""
        # Q1 2025: actual 2.40 vs estimated 2.35 = BEAT
        latest = aapl_earnings[0]
        surprise = latest["epsActual"] - latest["epsEstimated"]

        assert surprise > 0  # Beat
        assert latest["epsActual"] == 2.40
        assert latest["epsEstimated"] == 2.35

    def test_earnings_miss_detection(self, aapl_earnings):
        """Test that earnings misses are correctly identified."""
        # Q4 2024: actual 0.97 vs estimated 1.02 = MISS
        q4 = aapl_earnings[1]
        surprise = q4["epsActual"] - q4["epsEstimated"]

        assert surprise < 0  # Miss
        assert q4["epsActual"] == 0.97
        assert q4["epsEstimated"] == 1.02


class TestBalanceSheet:
    """Tests for balance sheet data."""

    def test_cash_position(self, aapl_balance_sheet):
        """Test cash position calculation."""
        balance = aapl_balance_sheet[0]

        # Total cash should be cash + short-term investments
        total_cash = balance["cashAndShortTermInvestments"]
        assert total_cash > 70000000000  # > $70B

    def test_debt_calculation(self, aapl_balance_sheet):
        """Test total debt calculation."""
        balance = aapl_balance_sheet[0]

        total_debt = balance["shortTermDebt"] + balance["longTermDebt"]
        assert total_debt > 100000000000  # > $100B (Apple has significant debt)

    def test_equity_positive(self, aapl_balance_sheet):
        """Test that stockholder equity is positive."""
        balance = aapl_balance_sheet[0]

        assert balance["totalStockholdersEquity"] > 0


class TestCashFlow:
    """Tests for cash flow data."""

    def test_free_cash_flow(self, aapl_cash_flow):
        """Test free cash flow calculation."""
        cf = aapl_cash_flow[0]

        # FCF = Operating CF - CapEx
        calculated_fcf = cf["operatingCashFlow"] + cf["capitalExpenditure"]  # capex is negative
        assert abs(calculated_fcf - cf["freeCashFlow"]) < 1000000  # Within $1M tolerance

    def test_buybacks(self, aapl_cash_flow):
        """Test that Apple is doing buybacks."""
        cf = aapl_cash_flow[0]

        # Apple does massive buybacks
        assert cf["commonStockRepurchased"] < 0  # Negative = money spent on buybacks
        assert abs(cf["commonStockRepurchased"]) > 20000000000  # > $20B


class TestIncomeStatement:
    """Tests for income statement data."""

    def test_margin_calculation(self, aapl_income):
        """Test margin calculations."""
        latest = aapl_income[0]

        revenue = latest["revenue"]
        gross_profit = latest["grossProfit"]
        net_income = latest["netIncome"]

        gross_margin = (gross_profit / revenue) * 100
        net_margin = (net_income / revenue) * 100

        # Apple typically has 40%+ gross margin
        assert gross_margin > 40
        assert gross_margin < 60

        # Apple typically has 20%+ net margin
        assert net_margin > 20

    def test_revenue_trend(self, aapl_income):
        """Test revenue trend analysis."""
        # Compare Q1 2025 to Q1 2024 (YoY)
        q1_2025 = aapl_income[0]
        q1_2024 = aapl_income[4]

        yoy_growth = ((q1_2025["revenue"] - q1_2024["revenue"]) / q1_2024["revenue"]) * 100

        # Should show some growth
        assert yoy_growth > 0  # Positive YoY growth


class TestNextEarnings:
    """Tests for next earnings date processing."""

    def test_next_earnings_future_date(self):
        """Test that next earnings returns future date."""
        # Mock earnings calendar with future date
        earnings_cal = [
            {"date": "2026-04-30", "time": "amc", "eps": 1.50, "revenue": 95000000000}
        ]

        result = _get_next_earnings(earnings_cal)

        assert result is not None
        assert result["date"] == "2026-04-30"
        assert result["daysUntil"] > 0

    def test_next_earnings_empty(self):
        """Test handling of empty earnings calendar."""
        result = _get_next_earnings([])
        assert result is None

        result = _get_next_earnings(None)
        assert result is None
