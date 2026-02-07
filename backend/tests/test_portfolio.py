"""
Tests for portfolio service, snapshot service, crypto caching, and calculate_summary.
Uses temp directories for file isolation — no real data is touched.
"""

import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from services.portfolio_service import PortfolioService, categorize_ticker
from services.portfolio_snapshot_service import PortfolioSnapshotService
from routes.portfolio import calculate_summary, _extract_next_earnings_date


# ── Ticker Categorization ──────────────────────────────────────────────────


class TestCategorizeTicker:
    def test_stock(self):
        assert categorize_ticker("AAPL") == "stock"
        assert categorize_ticker("TSLA") == "stock"
        assert categorize_ticker("AMZN") == "stock"

    def test_etf(self):
        assert categorize_ticker("VOO") == "etf"
        assert categorize_ticker("VGT") == "etf"
        assert categorize_ticker("SCHD") == "etf"
        assert categorize_ticker("GLD") == "etf"
        assert categorize_ticker("SPY") == "etf"

    def test_crypto(self):
        assert categorize_ticker("BTC") == "crypto"
        assert categorize_ticker("ETH") == "crypto"
        assert categorize_ticker("XRP") == "crypto"
        assert categorize_ticker("SHIB") == "crypto"

    def test_case_insensitive(self):
        assert categorize_ticker("btc") == "crypto"
        assert categorize_ticker("voo") == "etf"
        assert categorize_ticker("aapl") == "stock"

    def test_unknown_defaults_to_stock(self):
        assert categorize_ticker("XYZABC") == "stock"


# ── Portfolio Service ───────────────────────────────────────────────────────


class TestPortfolioService:
    def setup_method(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = PortfolioService(data_dir=self.tmp.name)

    def teardown_method(self):
        self.tmp.cleanup()

    def test_empty_portfolio(self):
        assert self.service.get_all() == []

    def test_add_stock(self):
        holding = self.service.add("AAPL", 10, 150.0, "Fidelity")
        assert holding["ticker"] == "AAPL"
        assert holding["quantity"] == 10
        assert holding["costBasis"] == 150.0
        assert holding["accountName"] == "Fidelity"
        assert holding["assetType"] == "stock"
        assert holding["id"].startswith("h_")

    def test_add_etf_auto_categorized(self):
        holding = self.service.add("VOO", 5, 500.0, "Vanguard")
        assert holding["assetType"] == "etf"

    def test_add_crypto_auto_categorized(self):
        holding = self.service.add("BTC", 0.5, 60000.0, "Coinbase")
        assert holding["assetType"] == "crypto"

    def test_add_custom_asset_type(self):
        holding = self.service.add("LEDGER", 1, 17000.0, "Ledger", asset_type="custom")
        assert holding["assetType"] == "custom"

    def test_add_cash_asset_type(self):
        holding = self.service.add("CASH", 1, 50000.0, "Fidelity", asset_type="cash")
        assert holding["assetType"] == "cash"
        assert holding["costBasis"] == 50000.0

    def test_add_option_holding(self):
        holding = self.service.add(
            "AAPL 200C", 5, 3.50, "Fidelity",
            asset_type="option",
            option_type="call",
            strike_price=200.0,
            expiration_date="2025-06-20",
            underlying_ticker="AAPL",
            option_price=4.20,
        )
        assert holding["assetType"] == "option"
        assert holding["optionType"] == "call"
        assert holding["strikePrice"] == 200.0
        assert holding["expirationDate"] == "2025-06-20"
        assert holding["underlyingTicker"] == "AAPL"
        assert holding["quantity"] == 5
        assert holding["costBasis"] == 3.50
        assert holding["optionPrice"] == 4.20

    def test_update_option_fields(self):
        holding = self.service.add(
            "AAPL 200C", 5, 3.50, "Fidelity",
            asset_type="option",
            option_type="call",
            strike_price=200.0,
            expiration_date="2025-06-20",
            underlying_ticker="AAPL",
            option_price=4.20,
        )
        updated = self.service.update(
            holding["id"],
            quantity=10,
            cost_basis=4.00,
            strike_price=210.0,
            expiration_date="2025-09-19",
            option_price=5.50,
        )
        assert updated["quantity"] == 10
        assert updated["costBasis"] == 4.00
        assert updated["strikePrice"] == 210.0
        assert updated["expirationDate"] == "2025-09-19"
        assert updated["optionPrice"] == 5.50
        # Unchanged fields preserved
        assert updated["optionType"] == "call"
        assert updated["underlyingTicker"] == "AAPL"

    def test_add_multiple_holdings(self):
        self.service.add("AAPL", 10, 150.0, "Fidelity")
        time.sleep(0.002)
        self.service.add("TSLA", 5, 300.0, "Robinhood")
        time.sleep(0.002)
        self.service.add("BTC", 1, 60000.0, "Coinbase")
        assert len(self.service.get_all()) == 3

    def test_get_holding_by_id(self):
        holding = self.service.add("AAPL", 10, 150.0, "Fidelity")
        fetched = self.service.get(holding["id"])
        assert fetched["ticker"] == "AAPL"

    def test_get_nonexistent_holding(self):
        assert self.service.get("h_nonexistent") is None

    def test_update_quantity(self):
        holding = self.service.add("AAPL", 10, 150.0, "Fidelity")
        updated = self.service.update(holding["id"], quantity=20)
        assert updated["quantity"] == 20
        assert updated["costBasis"] == 150.0  # unchanged

    def test_update_cost_basis(self):
        holding = self.service.add("AAPL", 10, 150.0, "Fidelity")
        updated = self.service.update(holding["id"], cost_basis=200.0)
        assert updated["costBasis"] == 200.0
        assert updated["quantity"] == 10  # unchanged

    def test_update_account_name(self):
        holding = self.service.add("AAPL", 10, 150.0, "Fidelity")
        updated = self.service.update(holding["id"], account_name="Schwab")
        assert updated["accountName"] == "Schwab"

    def test_update_nonexistent_returns_none(self):
        assert self.service.update("h_fake", quantity=5) is None

    def test_remove_holding(self):
        holding = self.service.add("AAPL", 10, 150.0, "Fidelity")
        assert self.service.remove(holding["id"]) is True
        assert len(self.service.get_all()) == 0

    def test_remove_nonexistent_returns_false(self):
        assert self.service.remove("h_fake") is False

    def test_get_by_ticker(self):
        self.service.add("AAPL", 10, 150.0, "Fidelity")
        time.sleep(0.002)
        self.service.add("AAPL", 5, 160.0, "Robinhood")
        time.sleep(0.002)
        self.service.add("TSLA", 3, 300.0, "Fidelity")
        results = self.service.get_by_ticker("AAPL")
        assert len(results) == 2
        assert all(h["ticker"] == "AAPL" for h in results)

    def test_get_by_ticker_case_insensitive(self):
        self.service.add("AAPL", 10, 150.0, "Fidelity")
        results = self.service.get_by_ticker("aapl")
        assert len(results) == 1

    def test_ticker_stored_uppercase(self):
        holding = self.service.add("aapl", 10, 150.0, "Fidelity")
        assert holding["ticker"] == "AAPL"

    def test_get_summary_with_all_types(self):
        self.service.add("AAPL", 10, 150.0, "Fidelity")
        time.sleep(0.002)
        self.service.add("VOO", 5, 500.0, "Vanguard")
        time.sleep(0.002)
        self.service.add("BTC", 1, 60000.0, "Coinbase")
        time.sleep(0.002)
        self.service.add("LEDGER", 1, 17000.0, "Ledger", asset_type="custom")
        time.sleep(0.002)
        self.service.add("CASH", 1, 25000.0, "Fidelity", asset_type="cash")
        time.sleep(0.002)
        self.service.add(
            "AAPL 200C", 5, 3.50, "Fidelity",
            asset_type="option", option_type="call",
            strike_price=200.0, expiration_date="2025-06-20",
            underlying_ticker="AAPL",
        )
        summary = self.service.get_summary()
        assert summary["totalHoldings"] == 6
        assert len(summary["byAssetType"]["stock"]) == 1
        assert len(summary["byAssetType"]["etf"]) == 1
        assert len(summary["byAssetType"]["crypto"]) == 1
        assert len(summary["byAssetType"]["custom"]) == 1
        assert len(summary["byAssetType"]["cash"]) == 1
        assert len(summary["byAssetType"]["option"]) == 1
        assert "Fidelity" in summary["accounts"]
        assert "Coinbase" in summary["accounts"]

    def test_persistence_across_instances(self):
        self.service.add("AAPL", 10, 150.0, "Fidelity")
        new_service = PortfolioService(data_dir=self.tmp.name)
        assert len(new_service.get_all()) == 1


# ── calculate_summary ───────────────────────────────────────────────────────


class TestCalculateSummary:
    def _make_holding(self, asset_type, cost_basis, price, quantity=10):
        total_cost = quantity * cost_basis
        current_value = quantity * price if price else None
        gain_loss = current_value - total_cost if current_value is not None else None
        return {
            "assetType": asset_type,
            "totalCost": total_cost,
            "currentValue": current_value,
            "gainLoss": gain_loss,
        }

    def test_basic_summary(self):
        holdings = [
            self._make_holding("stock", 100, 120),
            self._make_holding("etf", 50, 55),
        ]
        summary = calculate_summary(holdings)
        assert summary["totalValue"] == (120 * 10) + (55 * 10)
        assert summary["totalCost"] == (100 * 10) + (50 * 10)
        assert summary["totalGainLoss"] == (200) + (50)

    def test_cash_excluded_from_total_cost(self):
        holdings = [
            self._make_holding("stock", 100, 120),  # cost=1000, val=1200
            self._make_holding("cash", 5000, 5000, quantity=1),  # cost=5000, val=5000
        ]
        summary = calculate_summary(holdings)
        # totalCost should NOT include cash
        assert summary["totalCost"] == 1000
        # totalValue SHOULD include cash
        assert summary["totalValue"] == 1200 + 5000
        # cash appears in byAssetType
        assert summary["byAssetType"]["cash"]["count"] == 1
        assert summary["byAssetType"]["cash"]["value"] == 5000

    def test_return_percent_excludes_cash(self):
        holdings = [
            self._make_holding("stock", 100, 150),  # cost=1000, val=1500, gain=500
            self._make_holding("cash", 10000, 10000, quantity=1),
        ]
        summary = calculate_summary(holdings)
        # Return should be 500/1000 = 50%, not 500/11000
        assert summary["totalGainLossPercent"] == pytest.approx(50.0)

    def test_custom_in_summary(self):
        holdings = [self._make_holding("custom", 17000, 17000, quantity=1)]
        summary = calculate_summary(holdings)
        assert summary["byAssetType"]["custom"]["count"] == 1
        assert summary["byAssetType"]["custom"]["value"] == 17000

    def test_option_in_summary(self):
        # Simulate enriched option holding (100x multiplier applied during enrichment)
        # 5 contracts × $3.50 premium × 100 shares/contract = $1,750
        holdings = [self._make_holding("option", 350, 350, quantity=5)]
        summary = calculate_summary(holdings)
        assert summary["byAssetType"]["option"]["count"] == 1
        assert summary["byAssetType"]["option"]["value"] == 1750
        # Options are included in totalCost (invested capital)
        assert summary["totalCost"] == 1750

    def test_all_asset_types_present(self):
        summary = calculate_summary([])
        for t in ["stock", "etf", "crypto", "custom", "cash", "option"]:
            assert t in summary["byAssetType"]
            assert summary["byAssetType"][t]["count"] == 0

    def test_gain_loss_with_none_price(self):
        holdings = [self._make_holding("stock", 100, None)]
        summary = calculate_summary(holdings)
        assert summary["totalCost"] == 1000
        assert summary["totalValue"] == 0  # None prices don't add to value
        assert summary["totalGainLoss"] == 0

    def test_mixed_portfolio(self):
        holdings = [
            self._make_holding("stock", 100, 120, 10),   # +200
            self._make_holding("etf", 50, 45, 20),       # -100
            self._make_holding("crypto", 60000, 70000, 1),  # +10000
            self._make_holding("custom", 17000, 17000, 1),  # 0
            self._make_holding("cash", 25000, 25000, 1),    # 0
            self._make_holding("option", 350, 350, 5),      # 5 contracts, enriched with 100x
        ]
        summary = calculate_summary(holdings)
        assert summary["byAssetType"]["stock"]["count"] == 1
        assert summary["byAssetType"]["etf"]["count"] == 1
        assert summary["byAssetType"]["crypto"]["count"] == 1
        assert summary["byAssetType"]["custom"]["count"] == 1
        assert summary["byAssetType"]["cash"]["count"] == 1
        assert summary["byAssetType"]["option"]["count"] == 1
        expected_gain = 200 + (-100) + 10000 + 0 + 0 + 0
        assert summary["totalGainLoss"] == expected_gain
        # totalCost excludes cash but includes options (5 × $3.50 × 100 = $1,750)
        expected_cost = 1000 + 1000 + 60000 + 17000 + 1750
        assert summary["totalCost"] == expected_cost


# ── Snapshot Service ────────────────────────────────────────────────────────


class TestSnapshotService:
    def setup_method(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = PortfolioSnapshotService(data_dir=self.tmp.name)

    def teardown_method(self):
        self.tmp.cleanup()

    def _make_summary(self, total_value=100000, total_cost=80000, gain=20000,
                      stocks_val=60000, etfs_val=20000, crypto_val=10000,
                      custom_val=5000, cash_val=5000, option_val=0):
        return {
            "totalValue": total_value,
            "totalCost": total_cost,
            "totalGainLoss": gain,
            "totalGainLossPercent": (gain / total_cost * 100) if total_cost else 0,
            "byAssetType": {
                "stock": {"count": 2, "value": stocks_val, "cost": 50000, "gainLoss": 10000},
                "etf": {"count": 1, "value": etfs_val, "cost": 15000, "gainLoss": 5000},
                "crypto": {"count": 1, "value": crypto_val, "cost": 8000, "gainLoss": 2000},
                "custom": {"count": 1, "value": custom_val, "cost": 5000, "gainLoss": 0},
                "cash": {"count": 1, "value": cash_val, "cost": 5000, "gainLoss": 0},
                "option": {"count": 1 if option_val else 0, "value": option_val, "cost": option_val, "gainLoss": 0},
            },
        }

    def test_no_snapshots_initially(self):
        assert self.service.has_today_snapshot() is False

    def test_save_snapshot(self):
        summary = self._make_summary()
        result = self.service.save_snapshot(summary)
        assert result["alreadyExists"] is False
        assert result["totalValue"] == 100000
        assert self.service.has_today_snapshot() is True

    def test_skip_duplicate_snapshot(self):
        summary = self._make_summary()
        self.service.save_snapshot(summary)
        result = self.service.save_snapshot(summary)
        assert result["alreadyExists"] is True

    def test_force_overwrite_snapshot(self):
        summary1 = self._make_summary(total_value=100000)
        self.service.save_snapshot(summary1)
        summary2 = self._make_summary(total_value=120000)
        result = self.service.save_snapshot(summary2, force=True)
        assert result["alreadyExists"] is False
        assert result["totalValue"] == 120000

    def test_snapshot_includes_all_asset_types(self):
        summary = self._make_summary(option_val=175)
        result = self.service.save_snapshot(summary)
        by_type = result["byAssetType"]
        assert "stock" in by_type
        assert "etf" in by_type
        assert "crypto" in by_type
        assert "custom" in by_type
        assert "cash" in by_type
        assert "option" in by_type
        assert by_type["custom"]["value"] == 5000
        assert by_type["cash"]["value"] == 5000
        assert by_type["option"]["value"] == 175

    def test_get_snapshot_for_date(self):
        summary = self._make_summary()
        self.service.save_snapshot(summary)
        today = datetime.now().strftime("%Y-%m-%d")
        snap = self.service.get_snapshot_for_date(today)
        assert snap is not None
        assert snap["date"] == today
        assert snap["totalValue"] == 100000

    def test_get_snapshot_for_missing_date(self):
        assert self.service.get_snapshot_for_date("2020-01-01") is None

    def test_get_nearest_snapshot(self):
        # Manually insert a snapshot for 3 days ago
        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        snapshots = {
            three_days_ago: {
                "totalValue": 90000,
                "totalCost": 80000,
                "totalGainLoss": 10000,
                "totalGainLossPercent": 12.5,
                "byAssetType": {},
                "takenAt": datetime.now().isoformat(),
            }
        }
        self.service._save_snapshots(snapshots)

        # Look for today — should find the one 3 days ago (within 4-day lookback)
        today = datetime.now().strftime("%Y-%m-%d")
        result = self.service.get_nearest_snapshot(today)
        assert result is not None
        assert result["date"] == three_days_ago

    def test_get_nearest_snapshot_too_old(self):
        ten_days_ago = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        snapshots = {
            ten_days_ago: {
                "totalValue": 90000,
                "totalCost": 80000,
                "totalGainLoss": 10000,
                "totalGainLossPercent": 12.5,
                "byAssetType": {},
                "takenAt": datetime.now().isoformat(),
            }
        }
        self.service._save_snapshots(snapshots)
        today = datetime.now().strftime("%Y-%m-%d")
        result = self.service.get_nearest_snapshot(today)
        assert result is None

    def test_get_snapshots_within_range(self):
        now = datetime.now()
        snapshots = {}
        for i in range(5):
            date = (now - timedelta(days=i * 10)).strftime("%Y-%m-%d")
            snapshots[date] = {
                "totalValue": 100000 - (i * 5000),
                "totalCost": 80000,
                "totalGainLoss": 20000 - (i * 5000),
                "totalGainLossPercent": 0,
                "byAssetType": {},
                "takenAt": now.isoformat(),
            }
        self.service._save_snapshots(snapshots)

        result = self.service.get_snapshots(days=30)
        # Should include snapshots from 0, 10, 20, 30 days ago (within 30 days)
        assert len(result) >= 3
        # Should be sorted ascending
        dates = [s["date"] for s in result]
        assert dates == sorted(dates)

    def test_get_performance_empty(self):
        result = self.service.get_performance()
        assert result["periods"] == {}
        assert result["history"] == []

    def test_get_performance_with_data(self):
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        snapshots = {
            week_ago: {
                "totalValue": 90000,
                "totalCost": 80000,
                "totalGainLoss": 10000,
                "totalGainLossPercent": 12.5,
                "byAssetType": {
                    "stock": {"value": 50000, "cost": 40000, "gainLoss": 10000, "count": 2},
                    "etf": {"value": 20000, "cost": 15000, "gainLoss": 5000, "count": 1},
                    "crypto": {"value": 10000, "cost": 8000, "gainLoss": 2000, "count": 1},
                    "custom": {"value": 5000, "cost": 5000, "gainLoss": 0, "count": 1},
                    "cash": {"value": 5000, "cost": 5000, "gainLoss": 0, "count": 1},
                    "option": {"value": 0, "cost": 0, "gainLoss": 0, "count": 0},
                },
                "takenAt": now.isoformat(),
            },
            today: {
                "totalValue": 100000,
                "totalCost": 80000,
                "totalGainLoss": 20000,
                "totalGainLossPercent": 25.0,
                "byAssetType": {
                    "stock": {"value": 60000, "cost": 40000, "gainLoss": 20000, "count": 2},
                    "etf": {"value": 20000, "cost": 15000, "gainLoss": 5000, "count": 1},
                    "crypto": {"value": 10000, "cost": 8000, "gainLoss": 2000, "count": 1},
                    "custom": {"value": 5000, "cost": 5000, "gainLoss": 0, "count": 1},
                    "cash": {"value": 5000, "cost": 5000, "gainLoss": 0, "count": 1},
                    "option": {"value": 0, "cost": 0, "gainLoss": 0, "count": 0},
                },
                "takenAt": now.isoformat(),
            },
        }
        self.service._save_snapshots(snapshots)

        perf = self.service.get_performance()
        assert "1W" in perf["periods"]
        week_perf = perf["periods"]["1W"]
        assert week_perf["previousValue"] == 90000
        assert week_perf["currentValue"] == 100000
        assert week_perf["change"] == 10000
        # Per-asset breakdown
        assert "stock" in week_perf["byAssetType"]
        assert week_perf["byAssetType"]["stock"]["change"] == 10000

    def test_snapshot_persists_to_file(self):
        summary = self._make_summary()
        self.service.save_snapshot(summary)
        # Create new instance pointing to same dir
        new_service = PortfolioSnapshotService(data_dir=self.tmp.name)
        assert new_service.has_today_snapshot() is True


# ── Crypto Cache ────────────────────────────────────────────────────────────


class TestCryptoCache:
    def setup_method(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmp.name)
        self.cache_file = self.cache_dir / "prices.json"

    def teardown_method(self):
        self.tmp.cleanup()

    def _write_cache(self, prices, hours_ago=0):
        fetched_at = datetime.now() - timedelta(hours=hours_ago)
        self.cache_file.write_text(json.dumps({
            "fetchedAt": fetched_at.isoformat(),
            "prices": prices,
        }))

    def test_read_empty_cache(self):
        from services.crypto_service import CryptoService
        svc = CryptoService()
        svc._cache_dir = self.cache_dir
        svc._cache_file = self.cache_file
        assert svc._read_cache() == {}

    def test_read_fresh_cache(self):
        from services.crypto_service import CryptoService
        svc = CryptoService()
        svc._cache_dir = self.cache_dir
        svc._cache_file = self.cache_file

        prices = {"BTC": {"ticker": "BTC", "price": 70000}}
        self._write_cache(prices, hours_ago=1)
        result = svc._read_cache()
        assert "BTC" in result
        assert result["BTC"]["price"] == 70000

    def test_read_stale_cache(self):
        from services.crypto_service import CryptoService
        svc = CryptoService()
        svc._cache_dir = self.cache_dir
        svc._cache_file = self.cache_file

        prices = {"BTC": {"ticker": "BTC", "price": 70000}}
        self._write_cache(prices, hours_ago=13)  # > 12h TTL
        result = svc._read_cache()
        assert result == {}

    def test_write_cache(self):
        from services.crypto_service import CryptoService
        svc = CryptoService()
        svc._cache_dir = self.cache_dir
        svc._cache_file = self.cache_file

        prices = {"ETH": {"ticker": "ETH", "price": 2000}}
        svc._write_cache(prices)
        assert self.cache_file.exists()
        data = json.loads(self.cache_file.read_text())
        assert "ETH" in data["prices"]
        assert "fetchedAt" in data

    def test_write_cache_merges(self):
        from services.crypto_service import CryptoService
        svc = CryptoService()
        svc._cache_dir = self.cache_dir
        svc._cache_file = self.cache_file

        # Write BTC first
        self._write_cache({"BTC": {"ticker": "BTC", "price": 70000}}, hours_ago=1)
        # Now write ETH — should merge with BTC
        svc._write_cache({"ETH": {"ticker": "ETH", "price": 2000}})
        data = json.loads(self.cache_file.read_text())
        assert "BTC" in data["prices"]
        assert "ETH" in data["prices"]

    def test_corrupt_cache_returns_empty(self):
        from services.crypto_service import CryptoService
        svc = CryptoService()
        svc._cache_dir = self.cache_dir
        svc._cache_file = self.cache_file

        self.cache_file.write_text("not valid json{{{")
        assert svc._read_cache() == {}


# ── Options Service ──────────────────────────────────────────────────────


class TestOptionsService:
    def setup_method(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmp.name)

    def teardown_method(self):
        self.tmp.cleanup()

    def _make_service(self, api_key="test_key"):
        from services.options_service import OptionsService
        svc = OptionsService()
        svc.api_key = api_key
        svc._cache_dir = self.cache_dir
        return svc

    def test_is_configured_with_key(self):
        svc = self._make_service(api_key="my_key")
        assert svc.is_configured is True

    def test_is_not_configured_without_key(self):
        svc = self._make_service(api_key="")
        assert svc.is_configured is False

    def test_cache_write_and_read(self):
        svc = self._make_service()
        chain = [
            {"symbol": "AAPL210416C00200000", "strike": 200.0, "option_type": "call", "last": 5.50},
            {"symbol": "AAPL210416P00200000", "strike": 200.0, "option_type": "put", "last": 3.20},
        ]
        svc._write_cache("AAPL_2025-06-20", chain)
        result = svc._read_cache("AAPL_2025-06-20")
        assert result is not None
        assert len(result) == 2
        assert result[0]["last"] == 5.50

    def test_cache_miss_returns_none(self):
        svc = self._make_service()
        assert svc._read_cache("AAPL_2025-06-20") is None

    def test_stale_cache_returns_none(self):
        svc = self._make_service()
        # Write cache with old timestamp
        cache_file = self.cache_dir / "AAPL_2025-06-20.json"
        cache_file.write_text(json.dumps({
            "fetchedAt": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "chain": [{"strike": 200.0, "option_type": "call", "last": 5.50}],
        }))
        assert svc._read_cache("AAPL_2025-06-20") is None

    def test_corrupt_cache_returns_none(self):
        svc = self._make_service()
        cache_file = self.cache_dir / "AAPL_2025-06-20.json"
        cache_file.write_text("not valid json{{{")
        assert svc._read_cache("AAPL_2025-06-20") is None

    @pytest.mark.asyncio
    async def test_get_option_price_no_api_key(self):
        svc = self._make_service(api_key="")
        result = await svc.get_option_price("AAPL", 200.0, "2025-06-20", "call")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_option_price_from_cache(self):
        svc = self._make_service()
        # Pre-populate cache
        chain = [
            {"strike": 200.0, "option_type": "call", "last": 5.50, "bid": 5.40, "ask": 5.60},
            {"strike": 200.0, "option_type": "put", "last": 3.20, "bid": 3.10, "ask": 3.30},
            {"strike": 210.0, "option_type": "call", "last": 2.10, "bid": 2.00, "ask": 2.20},
        ]
        svc._write_cache("AAPL_2025-06-20", chain)

        price = await svc.get_option_price("AAPL", 200.0, "2025-06-20", "call")
        assert price == 5.50

        price = await svc.get_option_price("AAPL", 200.0, "2025-06-20", "put")
        assert price == 3.20

        price = await svc.get_option_price("AAPL", 210.0, "2025-06-20", "call")
        assert price == 2.10

    @pytest.mark.asyncio
    async def test_get_option_price_fallback_to_midpoint(self):
        svc = self._make_service()
        chain = [
            {"strike": 200.0, "option_type": "call", "last": 0, "bid": 5.40, "ask": 5.60},
        ]
        svc._write_cache("AAPL_2025-06-20", chain)
        price = await svc.get_option_price("AAPL", 200.0, "2025-06-20", "call")
        assert price == 5.50  # midpoint of 5.40 and 5.60

    @pytest.mark.asyncio
    async def test_get_option_price_no_match(self):
        svc = self._make_service()
        chain = [
            {"strike": 200.0, "option_type": "call", "last": 5.50},
        ]
        svc._write_cache("AAPL_2025-06-20", chain)
        # Wrong strike
        price = await svc.get_option_price("AAPL", 999.0, "2025-06-20", "call")
        assert price is None

    @pytest.mark.asyncio
    async def test_get_option_prices_batch_no_api_key(self):
        svc = self._make_service(api_key="")
        result = await svc.get_option_prices_batch([
            {"id": "h_1", "underlyingTicker": "AAPL", "strikePrice": 200.0,
             "expirationDate": "2025-06-20", "optionType": "call"},
        ])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_option_prices_batch_from_cache(self):
        svc = self._make_service()
        chain = [
            {"strike": 200.0, "option_type": "call", "last": 5.50},
            {"strike": 200.0, "option_type": "put", "last": 3.20},
        ]
        svc._write_cache("AAPL_2025-06-20", chain)

        holdings = [
            {"id": "h_1", "underlyingTicker": "AAPL", "strikePrice": 200.0,
             "expirationDate": "2025-06-20", "optionType": "call"},
            {"id": "h_2", "underlyingTicker": "AAPL", "strikePrice": 200.0,
             "expirationDate": "2025-06-20", "optionType": "put"},
        ]
        result = await svc.get_option_prices_batch(holdings)
        assert result["h_1"] == 5.50
        assert result["h_2"] == 3.20

    @pytest.mark.asyncio
    async def test_get_option_prices_batch_missing_fields(self):
        svc = self._make_service()
        # Holdings with missing underlyingTicker/expirationDate
        holdings = [
            {"id": "h_1", "underlyingTicker": "", "strikePrice": 200.0,
             "expirationDate": "2025-06-20", "optionType": "call"},
            {"id": "h_2", "underlyingTicker": "AAPL", "strikePrice": 200.0,
             "expirationDate": "", "optionType": "call"},
        ]
        result = await svc.get_option_prices_batch(holdings)
        assert result["h_1"] is None
        assert result["h_2"] is None


# ── Next Earnings Date Extraction ─────────────────────────────────────────────


class TestExtractNextEarningsDate:
    """Tests for _extract_next_earnings_date() used in portfolio stock enrichment."""

    def _future_date(self, days_ahead=10):
        return (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    def _past_date(self, days_ago=10):
        return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    def test_returns_nearest_future_date(self):
        near = self._future_date(5)
        far = self._future_date(30)
        result = _extract_next_earnings_date([{"date": far}, {"date": near}])
        assert result == near

    def test_returns_none_for_empty_list(self):
        assert _extract_next_earnings_date([]) is None

    def test_returns_none_for_none_input(self):
        assert _extract_next_earnings_date(None) is None

    def test_skips_past_dates(self):
        past = self._past_date(5)
        future = self._future_date(10)
        result = _extract_next_earnings_date([{"date": past}, {"date": future}])
        assert result == future

    def test_returns_none_when_all_dates_in_past(self):
        result = _extract_next_earnings_date([
            {"date": self._past_date(5)},
            {"date": self._past_date(30)},
        ])
        assert result is None

    def test_includes_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        result = _extract_next_earnings_date([{"date": today}])
        assert result == today

    def test_skips_entries_without_date(self):
        future = self._future_date(10)
        result = _extract_next_earnings_date([
            {"date": None},
            {},
            {"date": future},
        ])
        assert result == future

    def test_skips_malformed_dates(self):
        future = self._future_date(10)
        result = _extract_next_earnings_date([
            {"date": "not-a-date"},
            {"date": "2026-13-45"},
            {"date": future},
        ])
        assert result == future

    def test_returns_none_when_all_entries_malformed(self):
        result = _extract_next_earnings_date([
            {"date": "invalid"},
            {"date": ""},
            {},
        ])
        assert result is None

    def test_single_future_date(self):
        future = self._future_date(15)
        result = _extract_next_earnings_date([{"date": future}])
        assert result == future

    def test_multiple_future_dates_sorted(self):
        """Ensures the nearest date is returned regardless of input order."""
        d1 = self._future_date(5)
        d2 = self._future_date(15)
        d3 = self._future_date(50)
        # Input in reverse order
        result = _extract_next_earnings_date([{"date": d3}, {"date": d2}, {"date": d1}])
        assert result == d1

    def test_extra_fields_ignored(self):
        future = self._future_date(7)
        result = _extract_next_earnings_date([
            {"date": future, "eps": 1.5, "revenue": 95000000000, "symbol": "AAPL"},
        ])
        assert result == future

    # ── Fallback to earnings history ──

    def test_falls_back_to_history_when_calendar_empty(self):
        future = self._future_date(20)
        history = [{"date": future, "epsActual": None, "epsEstimated": 1.5}]
        result = _extract_next_earnings_date([], history)
        assert result == future

    def test_falls_back_to_history_when_calendar_none(self):
        future = self._future_date(20)
        history = [{"date": future, "epsActual": None}]
        result = _extract_next_earnings_date(None, history)
        assert result == future

    def test_history_skips_entries_with_actual_eps(self):
        """Entries with epsActual set are past earnings, not upcoming."""
        past_reported = self._future_date(5)
        future_upcoming = self._future_date(30)
        history = [
            {"date": past_reported, "epsActual": 2.50},
            {"date": future_upcoming, "epsActual": None},
        ]
        result = _extract_next_earnings_date([], history)
        assert result == future_upcoming

    def test_calendar_takes_precedence_over_history(self):
        cal_date = self._future_date(10)
        hist_date = self._future_date(20)
        result = _extract_next_earnings_date(
            [{"date": cal_date}],
            [{"date": hist_date, "epsActual": None}],
        )
        assert result == cal_date

    def test_returns_none_when_both_sources_empty(self):
        assert _extract_next_earnings_date([], []) is None

    def test_returns_none_when_history_all_reported(self):
        """All history entries have actual EPS — no upcoming earnings."""
        result = _extract_next_earnings_date([], [
            {"date": self._future_date(5), "epsActual": 2.0},
            {"date": self._future_date(10), "epsActual": 1.5},
        ])
        assert result is None
