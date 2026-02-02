"""
Tests for DeepInsightsAgent - focusing on helper functions and fallback logic.
"""

import pytest
from agents.deep_insights_agent import (
    _safe_float,
    _format_currency,
    DeepInsightsAgent,
)


class TestSafeFloat:
    """Tests for _safe_float helper function."""

    def test_safe_float_with_valid_number(self):
        assert _safe_float(123.45) == 123.45

    def test_safe_float_with_integer(self):
        assert _safe_float(100) == 100.0

    def test_safe_float_with_string_number(self):
        assert _safe_float("123.45") == 123.45

    def test_safe_float_with_none(self):
        assert _safe_float(None) == 0

    def test_safe_float_with_none_custom_default(self):
        assert _safe_float(None, default=99) == 99

    def test_safe_float_with_invalid_string(self):
        assert _safe_float("not a number") == 0

    def test_safe_float_with_empty_string(self):
        assert _safe_float("") == 0

    def test_safe_float_with_negative(self):
        assert _safe_float(-500.5) == -500.5


class TestFormatCurrency:
    """Tests for _format_currency helper function."""

    def test_format_billions(self):
        assert _format_currency(57_000_000_000) == "$57.0B"

    def test_format_billions_with_decimals(self):
        assert _format_currency(57_500_000_000) == "$57.5B"

    def test_format_millions(self):
        assert _format_currency(125_500_000) == "$125.5M"

    def test_format_thousands(self):
        assert _format_currency(50_000) == "$50.0K"

    def test_format_small_number(self):
        assert _format_currency(999) == "$999.0"

    def test_format_none(self):
        assert _format_currency(None) == "N/A"

    def test_format_invalid_string(self):
        assert _format_currency("invalid") == "N/A"

    def test_format_negative_billions(self):
        assert _format_currency(-5_000_000_000) == "$-5.0B"

    def test_format_trillions(self):
        assert _format_currency(1_500_000_000_000) == "$1.5T"

    def test_format_with_custom_decimals(self):
        assert _format_currency(57_123_000_000, decimals=2) == "$57.12B"

    def test_format_zero(self):
        assert _format_currency(0) == "$0.0"


class TestDeepInsightsAgent:
    """Tests for DeepInsightsAgent methods."""

    @pytest.fixture
    def agent(self):
        return DeepInsightsAgent()

    @pytest.fixture
    def sample_data(self):
        return {
            "profile": {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "industry": "Consumer Electronics",
                "sector": "Technology",
                "mktCap": 3000000000000,
            },
            "income_statements": [
                {
                    "period": "Q1",
                    "fiscalYear": "2024",
                    "revenue": 100000000000,
                    "grossProfit": 45000000000,
                    "operatingIncome": 30000000000,
                    "netIncome": 25000000000,
                    "eps": 1.50,
                    "costOfRevenue": 55000000000,
                    "researchAndDevelopmentExpenses": 8000000000,
                }
            ],
            "balance_sheet": [
                {
                    "cashAndCashEquivalents": 30000000000,
                    "shortTermInvestments": 20000000000,
                    "shortTermDebt": 5000000000,
                    "longTermDebt": 100000000000,
                    "totalStockholdersEquity": 60000000000,
                    "totalAssets": 350000000000,
                    "inventory": 7000000000,
                }
            ],
            "cash_flow": [
                {
                    "operatingCashFlow": 30000000000,
                    "capitalExpenditure": -3000000000,
                    "freeCashFlow": 27000000000,
                    "commonDividendsPaid": -4000000000,
                    "commonStockRepurchased": -20000000000,
                }
            ],
        }

    def test_clean_json_response_with_markdown(self, agent):
        response = '```json\n{"key": "value"}\n```'
        result = agent._clean_json_response(response)
        assert result == '{"key": "value"}'

    def test_clean_json_response_plain_json(self, agent):
        response = '{"key": "value"}'
        result = agent._clean_json_response(response)
        assert result == '{"key": "value"}'

    def test_clean_json_response_with_text_before(self, agent):
        response = 'Here is the result: {"key": "value"}'
        result = agent._clean_json_response(response)
        assert result == '{"key": "value"}'

    def test_clean_json_response_with_text_after(self, agent):
        response = '{"key": "value"} some extra text'
        result = agent._clean_json_response(response)
        assert result == '{"key": "value"}'

    def test_fallback_analysis_structure(self, agent, sample_data):
        result = agent._fallback_analysis(sample_data, "test error")

        assert "industryContext" in result
        assert "operationalInsights" in result
        assert "deepDive" in result
        assert "hiddenInsights" in result
        assert "risks" in result
        assert "opportunities" in result
        assert "beginnerExplanation" in result
        assert "_meta" in result

    def test_fallback_analysis_meta(self, agent, sample_data):
        result = agent._fallback_analysis(sample_data, "test error")

        assert result["_meta"]["symbol"] == "AAPL"
        assert result["_meta"]["success"] is False
        assert "test error" in result["_meta"]["error"]

    def test_fallback_analysis_industry(self, agent, sample_data):
        result = agent._fallback_analysis(sample_data, "test error")

        assert result["industryContext"]["industry"] == "Consumer Electronics"

    def test_error_response_structure(self, agent, sample_data):
        result = agent._error_response("Something went wrong", sample_data)

        assert result["_meta"]["success"] is False
        assert result["_meta"]["error"] == "Something went wrong"
        assert result["industryContext"]["industry"] == "Unknown"

    def test_error_response_empty_lists(self, agent, sample_data):
        result = agent._error_response("error", sample_data)

        assert result["hiddenInsights"] == []
        assert result["risks"] == []
        assert result["opportunities"] == []
        assert result["operationalInsights"] == []

    def test_prepare_context_includes_profile(self, agent, sample_data):
        context = agent._prepare_comprehensive_context(sample_data)

        assert "COMPANY PROFILE" in context
        assert "Apple Inc." in context
        assert "AAPL" in context
        assert "Consumer Electronics" in context

    def test_prepare_context_includes_quarterly(self, agent, sample_data):
        context = agent._prepare_comprehensive_context(sample_data)

        assert "QUARTERLY PERFORMANCE" in context
        assert "Q1 2024" in context

    def test_prepare_context_includes_balance_sheet(self, agent, sample_data):
        context = agent._prepare_comprehensive_context(sample_data)

        assert "BALANCE SHEET" in context
        assert "Total Cash Position" in context
        assert "Debt-to-Equity" in context

    def test_prepare_context_includes_cash_flow(self, agent, sample_data):
        context = agent._prepare_comprehensive_context(sample_data)

        assert "CASH FLOW" in context
        assert "Free Cash Flow" in context
        assert "Stock Buybacks" in context

    def test_prepare_context_with_empty_data(self, agent):
        context = agent._prepare_comprehensive_context({})

        assert "COMPANY PROFILE" in context
        assert "Unknown" in context

    def test_prepare_context_with_segments(self, agent, sample_data):
        sample_data["product_segments"] = [
            {
                "fiscalYear": "2024",
                "data": {"iPhone": 200000000000, "Services": 80000000000}
            }
        ]
        context = agent._prepare_comprehensive_context(sample_data)

        assert "PRODUCT/BUSINESS SEGMENT" in context
        assert "iPhone" in context

    def test_prepare_context_with_geo_segments(self, agent, sample_data):
        sample_data["geo_segments"] = [
            {
                "fiscalYear": "2024",
                "data": {"Americas": 150000000000, "Europe": 100000000000}
            }
        ]
        context = agent._prepare_comprehensive_context(sample_data)

        assert "GEOGRAPHIC REVENUE" in context
        assert "Americas" in context

    def test_prepare_context_with_earnings(self, agent, sample_data):
        sample_data["earnings_surprises"] = [
            {"date": "2024-01-15", "epsActual": 2.18, "epsEstimated": 2.10},
            {"date": "2023-10-15", "epsActual": 1.46, "epsEstimated": 1.50},
        ]
        context = agent._prepare_comprehensive_context(sample_data)

        assert "EARNINGS SURPRISE HISTORY" in context
        assert "Beat Rate" in context
        assert "BEAT" in context
        assert "MISS" in context

    def test_prepare_context_with_ratios(self, agent, sample_data):
        sample_data["ratios"] = [
            {
                "priceEarningsRatio": 28.5,
                "priceToSalesRatio": 7.2,
                "returnOnEquity": 0.45,
                "currentRatio": 1.2,
            }
        ]
        context = agent._prepare_comprehensive_context(sample_data)

        assert "KEY FINANCIAL RATIOS" in context
        assert "P/E Ratio" in context
        assert "ROE" in context

    def test_prepare_context_with_growth_metrics(self, agent, sample_data):
        sample_data["financial_growth"] = [
            {
                "revenueGrowth": 0.08,
                "netIncomeGrowth": 0.12,
                "epsgrowth": 0.15,
            }
        ]
        context = agent._prepare_comprehensive_context(sample_data)

        assert "GROWTH METRICS" in context
        assert "Revenue Growth" in context


class TestDeepInsightsEdgeCases:
    """Edge case tests for DeepInsightsAgent."""

    @pytest.fixture
    def agent(self):
        return DeepInsightsAgent()

    def test_fallback_with_empty_income(self, agent):
        data = {"profile": {"symbol": "TEST"}, "income_statements": []}
        result = agent._fallback_analysis(data, "error")

        assert result["_meta"]["symbol"] == "TEST"

    def test_fallback_with_zero_revenue(self, agent):
        data = {
            "profile": {"symbol": "TEST"},
            "income_statements": [{"revenue": 0, "netIncome": 0}]
        }
        result = agent._fallback_analysis(data, "error")

        # Should not raise division by zero
        assert "marginAnalysis" in result["deepDive"]

    def test_error_response_with_empty_profile(self, agent):
        result = agent._error_response("error", {})

        assert result["_meta"]["symbol"] == "N/A"

    def test_context_handles_none_values(self, agent):
        data = {
            "profile": {"companyName": None, "symbol": None},
            "income_statements": [{"revenue": None, "netIncome": None}],
        }
        # Should not raise exceptions
        context = agent._prepare_comprehensive_context(data)
        assert "COMPANY PROFILE" in context
