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
from routes.portfolio import calculate_summary


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
        summary = self.service.get_summary()
        assert summary["totalHoldings"] == 5
        assert len(summary["byAssetType"]["stock"]) == 1
        assert len(summary["byAssetType"]["etf"]) == 1
        assert len(summary["byAssetType"]["crypto"]) == 1
        assert len(summary["byAssetType"]["custom"]) == 1
        assert len(summary["byAssetType"]["cash"]) == 1
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

    def test_all_asset_types_present(self):
        summary = calculate_summary([])
        for t in ["stock", "etf", "crypto", "custom", "cash"]:
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
        ]
        summary = calculate_summary(holdings)
        assert summary["byAssetType"]["stock"]["count"] == 1
        assert summary["byAssetType"]["etf"]["count"] == 1
        assert summary["byAssetType"]["crypto"]["count"] == 1
        assert summary["byAssetType"]["custom"]["count"] == 1
        assert summary["byAssetType"]["cash"]["count"] == 1
        expected_gain = 200 + (-100) + 10000 + 0 + 0
        assert summary["totalGainLoss"] == expected_gain
        # totalCost excludes cash
        expected_cost = 1000 + 1000 + 60000 + 17000
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
                      custom_val=5000, cash_val=5000):
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
        summary = self._make_summary()
        result = self.service.save_snapshot(summary)
        by_type = result["byAssetType"]
        assert "stock" in by_type
        assert "etf" in by_type
        assert "crypto" in by_type
        assert "custom" in by_type
        assert "cash" in by_type
        assert by_type["custom"]["value"] == 5000
        assert by_type["cash"]["value"] == 5000

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
