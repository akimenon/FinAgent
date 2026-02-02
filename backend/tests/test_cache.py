"""
Tests for FMPCache - file-based caching system.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from services.fmp_cache import FMPCache


class TestFMPCacheInit:
    """Tests for FMPCache initialization."""

    def test_default_cache_dir_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = FMPCache(cache_dir=tmpdir)
            assert cache.cache_dir.exists()

    def test_custom_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom_cache"
            cache = FMPCache(cache_dir=str(custom_path))
            assert cache.cache_dir == custom_path
            assert custom_path.exists()


class TestFMPCacheTTL:
    """Tests for TTL (Time To Live) logic."""

    @pytest.fixture
    def cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield FMPCache(cache_dir=tmpdir)

    def test_get_ttl_days_profile(self, cache):
        assert cache._get_ttl_days("profile") == 1

    def test_get_ttl_days_quarterly(self, cache):
        assert cache._get_ttl_days("income_quarterly") == 90

    def test_get_ttl_days_annual(self, cache):
        assert cache._get_ttl_days("product_segments") == 365

    def test_get_ttl_days_estimates(self, cache):
        assert cache._get_ttl_days("analyst_estimates") == 30

    def test_get_ttl_days_dynamic_price_history(self, cache):
        # Dynamic endpoints like price_history_30d should use base TTL
        assert cache._get_ttl_days("price_history_30d") == 1
        assert cache._get_ttl_days("price_history_365d") == 1

    def test_get_ttl_days_dynamic_earnings_calendar(self, cache):
        assert cache._get_ttl_days("market_earnings_calendar_7d") == 0.25

    def test_get_ttl_days_unknown_defaults_to_1(self, cache):
        assert cache._get_ttl_days("unknown_endpoint") == 1


class TestFMPCacheFileOperations:
    """Tests for file read/write operations."""

    @pytest.fixture
    def cache(self):
        tmpdir = tempfile.mkdtemp()
        cache = FMPCache(cache_dir=tmpdir)
        yield cache
        shutil.rmtree(tmpdir)

    def test_get_file_path(self, cache):
        path = cache._get_file_path("AAPL", "profile")
        assert path.name == "profile.json"
        assert "AAPL" in str(path)

    def test_get_file_path_uppercase_symbol(self, cache):
        path = cache._get_file_path("aapl", "profile")
        assert "AAPL" in str(path)

    def test_get_market_file_path(self, cache):
        path = cache._get_market_file_path("market_earnings_calendar")
        assert "_market" in str(path)
        assert path.name == "market_earnings_calendar.json"

    def test_write_and_read_cache(self, cache):
        test_data = {"key": "value", "number": 123}
        cache._write_cache("AAPL", "test_endpoint", test_data)

        cached = cache._read_cache("AAPL", "test_endpoint")
        assert cached is not None
        assert cached["data"] == test_data
        assert cached["symbol"] == "AAPL"
        assert cached["endpoint"] == "test_endpoint"
        assert "fetched_at" in cached

    def test_read_nonexistent_cache(self, cache):
        result = cache._read_cache("NONEXISTENT", "profile")
        assert result is None

    def test_write_market_cache(self, cache):
        test_data = [{"symbol": "AAPL", "date": "2024-01-15"}]
        cache._write_market_cache("market_earnings_calendar", test_data)

        cached = cache._read_market_cache("market_earnings_calendar")
        assert cached is not None
        assert cached["data"] == test_data

    def test_read_nonexistent_market_cache(self, cache):
        result = cache._read_market_cache("nonexistent")
        assert result is None


class TestFMPCacheFreshness:
    """Tests for cache freshness checking."""

    @pytest.fixture
    def cache(self):
        tmpdir = tempfile.mkdtemp()
        cache = FMPCache(cache_dir=tmpdir)
        yield cache
        shutil.rmtree(tmpdir)

    def test_is_fresh_with_recent_data(self, cache):
        cached_data = {
            "fetched_at": datetime.now().isoformat(),
            "data": {}
        }
        assert cache._is_fresh(cached_data, "profile") is True

    def test_is_fresh_with_stale_data(self, cache):
        old_time = datetime.now() - timedelta(days=10)
        cached_data = {
            "fetched_at": old_time.isoformat(),
            "data": {}
        }
        # Profile has TTL of 1 day, so 10 days old is stale
        assert cache._is_fresh(cached_data, "profile") is False

    def test_is_fresh_with_quarterly_data(self, cache):
        # 30 days old should still be fresh for quarterly data (90 day TTL)
        old_time = datetime.now() - timedelta(days=30)
        cached_data = {
            "fetched_at": old_time.isoformat(),
            "data": {}
        }
        assert cache._is_fresh(cached_data, "income_quarterly") is True

    def test_is_fresh_with_quarterly_data_stale(self, cache):
        # 100 days old should be stale for quarterly data
        old_time = datetime.now() - timedelta(days=100)
        cached_data = {
            "fetched_at": old_time.isoformat(),
            "data": {}
        }
        assert cache._is_fresh(cached_data, "income_quarterly") is False

    def test_is_fresh_with_none(self, cache):
        assert cache._is_fresh(None, "profile") is False

    def test_is_fresh_with_missing_fetched_at(self, cache):
        cached_data = {"data": {}}
        assert cache._is_fresh(cached_data, "profile") is False

    def test_is_fresh_with_annual_data(self, cache):
        # 200 days old should still be fresh for annual data (365 day TTL)
        old_time = datetime.now() - timedelta(days=200)
        cached_data = {
            "fetched_at": old_time.isoformat(),
            "data": {}
        }
        assert cache._is_fresh(cached_data, "product_segments") is True


class TestFMPCacheStatus:
    """Tests for cache status retrieval."""

    @pytest.fixture
    def cache(self):
        tmpdir = tempfile.mkdtemp()
        cache = FMPCache(cache_dir=tmpdir)
        yield cache
        shutil.rmtree(tmpdir)

    def test_cache_status_no_data(self, cache):
        status = cache.get_cache_status("UNKNOWN")
        assert status["symbol"] == "UNKNOWN"
        assert status["cached"] is False
        assert status["endpoints"] == {}

    def test_cache_status_with_data(self, cache):
        cache._write_cache("AAPL", "profile", {"test": "data"})
        cache._write_cache("AAPL", "income_quarterly", {"test": "data2"})

        status = cache.get_cache_status("AAPL")
        assert status["symbol"] == "AAPL"
        assert status["cached"] is True
        assert "profile" in status["endpoints"]
        assert "income_quarterly" in status["endpoints"]
        assert status["endpoints"]["profile"]["is_fresh"] is True


class TestFMPCacheClear:
    """Tests for cache clearing."""

    @pytest.fixture
    def cache(self):
        tmpdir = tempfile.mkdtemp()
        cache = FMPCache(cache_dir=tmpdir)
        yield cache
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_clear_specific_endpoint(self, cache):
        cache._write_cache("AAPL", "profile", {"test": "data"})
        cache._write_cache("AAPL", "income_quarterly", {"test": "data2"})

        cache.clear_cache("AAPL", "profile")

        assert cache._read_cache("AAPL", "profile") is None
        assert cache._read_cache("AAPL", "income_quarterly") is not None

    def test_clear_symbol_cache(self, cache):
        cache._write_cache("AAPL", "profile", {"test": "data"})
        cache._write_cache("AAPL", "income_quarterly", {"test": "data2"})
        cache._write_cache("MSFT", "profile", {"test": "data3"})

        cache.clear_cache("AAPL")

        assert cache._read_cache("AAPL", "profile") is None
        assert cache._read_cache("AAPL", "income_quarterly") is None
        assert cache._read_cache("MSFT", "profile") is not None

    def test_clear_all_cache(self, cache):
        cache._write_cache("AAPL", "profile", {"test": "data"})
        cache._write_cache("MSFT", "profile", {"test": "data2"})

        cache.clear_cache()

        assert cache._read_cache("AAPL", "profile") is None
        assert cache._read_cache("MSFT", "profile") is None
        # Cache directory should still exist but be empty
        assert cache.cache_dir.exists()

    def test_clear_nonexistent_symbol(self, cache):
        # Should not raise error
        cache.clear_cache("NONEXISTENT", "profile")

    def test_refresh_daily_data(self, cache):
        cache._write_cache("AAPL", "profile", {"test": "data"})
        cache._write_cache("AAPL", "price_history", {"test": "data2"})
        cache._write_cache("AAPL", "income_quarterly", {"test": "data3"})

        cache.refresh_daily_data("AAPL")

        assert cache._read_cache("AAPL", "profile") is None
        assert cache._read_cache("AAPL", "price_history") is None
        # Non-daily data should remain
        assert cache._read_cache("AAPL", "income_quarterly") is not None


class TestFMPCacheCorruptData:
    """Tests for handling corrupt cache data."""

    @pytest.fixture
    def cache(self):
        tmpdir = tempfile.mkdtemp()
        cache = FMPCache(cache_dir=tmpdir)
        yield cache
        shutil.rmtree(tmpdir)

    def test_read_corrupt_json(self, cache):
        # Write corrupt JSON
        file_path = cache._get_file_path("AAPL", "profile")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write("not valid json {{{")

        result = cache._read_cache("AAPL", "profile")
        assert result is None

    def test_read_corrupt_market_json(self, cache):
        # Write corrupt JSON
        file_path = cache._get_market_file_path("test_endpoint")
        with open(file_path, 'w') as f:
            f.write("not valid json")

        result = cache._read_market_cache("test_endpoint")
        assert result is None
