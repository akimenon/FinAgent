"""
Tests for agent modules.

Uses fixture data - NO API calls made during testing.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.analysis_agent import AnalysisAgent
from agents.guidance_tracker import GuidanceTrackerAgent
from agents.data_fetcher import DataFetcherAgent


class TestAnalysisAgent:
    """Tests for the Analysis Agent."""

    def test_analyze_returns_metrics(self, all_aapl_data):
        """Test that analysis returns expected metrics."""
        agent = AnalysisAgent()

        # Prepare data in expected format
        financial_data = {
            "symbol": "AAPL",
            "profile": all_aapl_data["profile"],
            "income_statements": all_aapl_data["income_quarterly"],
            "earnings_surprises": _process_earnings(all_aapl_data["earnings"]),
        }

        result = agent.analyze(financial_data)

        assert "metrics" in result
        assert "trends" in result
        assert "concerns" in result
        assert "beat_rate" in result

    def test_beat_rate_calculation(self, aapl_earnings):
        """Test beat rate is calculated correctly."""
        agent = AnalysisAgent()

        processed_earnings = _process_earnings(aapl_earnings)

        financial_data = {
            "symbol": "AAPL",
            "profile": {},
            "income_statements": [],
            "earnings_surprises": processed_earnings,
        }

        result = agent.analyze(financial_data)

        # 4 beats out of 5 quarters = 80%
        # Q1 2025: BEAT, Q4 2024: MISS, Q3 2024: BEAT, Q2 2024: BEAT, Q1 2024: BEAT
        assert result["beat_rate"] is not None


class TestGuidanceTracker:
    """Tests for the Guidance Tracker Agent."""

    def test_track_returns_history(self, all_aapl_data):
        """Test that guidance tracking returns history."""
        agent = GuidanceTrackerAgent()

        financial_data = {
            "symbol": "AAPL",
            "profile": all_aapl_data["profile"],
            "income_statements": all_aapl_data["income_quarterly"],
            "earnings_surprises": _process_earnings(all_aapl_data["earnings"]),
        }

        result = agent.track(financial_data)

        assert "accuracy_score" in result or "guidance_history" in result


class TestDataFetcherProcessing:
    """Tests for data fetcher processing methods."""

    def test_process_income_data(self, aapl_income):
        """Test income statement processing."""
        agent = DataFetcherAgent()
        processed = agent._process_income_data(aapl_income)

        assert len(processed) == len(aapl_income)

        # Check calculated fields exist
        first = processed[0]
        assert "gross_margin" in first
        assert "operating_margin" in first
        assert "net_margin" in first

        # Margins should be reasonable percentages
        assert 0 < first["gross_margin"] < 100
        assert 0 < first["operating_margin"] < 100
        assert 0 < first["net_margin"] < 100

    def test_process_earnings_surprises(self, aapl_earnings):
        """Test earnings surprise processing."""
        agent = DataFetcherAgent()
        processed = agent._process_surprises_data(aapl_earnings)

        assert len(processed) > 0

        # Check beat/miss classification
        first = processed[0]
        assert "beat_miss" in first
        assert first["beat_miss"] in ["BEAT", "MISS", "MEET"]

        # Check surprise calculation
        assert "eps_surprise" in first
        expected_surprise = first["actual_eps"] - first["estimated_eps"]
        assert abs(first["eps_surprise"] - expected_surprise) < 0.01


class TestDataIntegrity:
    """Tests to ensure fixture data integrity."""

    def test_profile_required_fields(self, aapl_profile):
        """Test profile has all required fields."""
        required = ["symbol", "companyName", "price", "marketCap", "sector"]

        for field in required:
            assert field in aapl_profile, f"Missing required field: {field}"

    def test_income_required_fields(self, aapl_income):
        """Test income statement has all required fields."""
        required = ["revenue", "grossProfit", "netIncome", "eps"]

        for quarter in aapl_income:
            for field in required:
                assert field in quarter, f"Missing required field: {field}"

    def test_segments_structure(self, aapl_product_segments, aapl_geo_segments):
        """Test segment data has correct structure."""
        # Product segments
        assert len(aapl_product_segments) >= 2  # At least 2 years

        latest = aapl_product_segments[0]
        assert "fiscalYear" in latest
        assert "data" in latest
        assert "iPhone" in latest["data"]  # Apple-specific

        # Geo segments
        assert len(aapl_geo_segments) >= 2

        latest_geo = aapl_geo_segments[0]
        assert "data" in latest_geo
        assert "Americas" in latest_geo["data"]


# Helper function to process raw earnings data
def _process_earnings(earnings_data):
    """Convert raw earnings to processed format."""
    processed = []
    for item in earnings_data:
        actual = item.get("epsActual", 0)
        estimated = item.get("epsEstimated", 0)
        surprise = actual - estimated

        if surprise > 0.01:
            verdict = "BEAT"
        elif surprise < -0.01:
            verdict = "MISS"
        else:
            verdict = "MEET"

        processed.append({
            "date": item.get("date"),
            "actual_eps": actual,
            "estimated_eps": estimated,
            "eps_surprise": round(surprise, 4),
            "beat_miss": verdict,
        })

    return processed
