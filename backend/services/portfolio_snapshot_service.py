"""
Portfolio Snapshot Service

Saves daily snapshots of portfolio value for performance tracking.
One snapshot per day, stored in a JSON file.

Structure:
data/portfolio/
└── snapshots.json
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path


class PortfolioSnapshotService:
    """
    Saves and retrieves daily portfolio value snapshots.

    Each snapshot contains:
    - date: YYYY-MM-DD
    - totalValue: Total portfolio value
    - totalCost: Total cost basis
    - totalGainLoss: Total gain/loss
    - byAssetType: Breakdown by stock/etf/crypto
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            base_dir = Path(__file__).parent.parent
            data_dir = base_dir / "data" / "portfolio"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_file = self.data_dir / "snapshots.json"

        if not self.snapshots_file.exists():
            self._save_snapshots({})

    def _load_snapshots(self) -> Dict[str, Any]:
        """Load snapshots from JSON file."""
        try:
            with open(self.snapshots_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_snapshots(self, snapshots: Dict[str, Any]) -> None:
        """Save snapshots to JSON file."""
        with open(self.snapshots_file, "w") as f:
            json.dump(snapshots, f, indent=2, default=str)

    def has_today_snapshot(self) -> bool:
        """Check if a snapshot already exists for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        snapshots = self._load_snapshots()
        return today in snapshots

    def save_snapshot(self, summary: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
        """
        Save a snapshot for today. Skips if already taken today unless force=True.

        Args:
            summary: Portfolio summary from the portfolio route's calculate_summary()
            force: If True, overwrite today's existing snapshot (for manual snapshots)

        Returns:
            The snapshot that was saved (or existing one if already taken today)
        """
        today = datetime.now().strftime("%Y-%m-%d")
        snapshots = self._load_snapshots()

        # Skip if already have today's snapshot (unless forced)
        if today in snapshots and not force:
            return {"date": today, "alreadyExists": True, **snapshots[today]}

        snapshot = {
            "totalValue": summary.get("totalValue", 0),
            "totalCost": summary.get("totalCost", 0),
            "totalGainLoss": summary.get("totalGainLoss", 0),
            "totalGainLossPercent": summary.get("totalGainLossPercent", 0),
            "byAssetType": {},
            "takenAt": datetime.now().isoformat(),
        }

        by_type = summary.get("byAssetType", {})
        for asset_type in ["stock", "etf", "crypto", "custom", "cash"]:
            type_data = by_type.get(asset_type, {})
            snapshot["byAssetType"][asset_type] = {
                "value": type_data.get("value", 0),
                "cost": type_data.get("cost", 0),
                "gainLoss": type_data.get("gainLoss", 0),
                "count": type_data.get("count", 0),
            }

        snapshots[today] = snapshot
        self._save_snapshots(snapshots)

        return {"date": today, "alreadyExists": False, **snapshot}

    def get_snapshots(
        self, days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get snapshots for the last N days, sorted by date ascending.

        Args:
            days: Number of days of history to return
        """
        snapshots = self._load_snapshots()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        result = []
        for date_str, data in snapshots.items():
            if date_str >= cutoff:
                result.append({"date": date_str, **data})

        result.sort(key=lambda x: x["date"])
        return result

    def get_snapshot_for_date(self, date_str: str) -> Optional[Dict[str, Any]]:
        """Get snapshot for a specific date."""
        snapshots = self._load_snapshots()
        if date_str in snapshots:
            return {"date": date_str, **snapshots[date_str]}
        return None

    def get_nearest_snapshot(self, target_date: str) -> Optional[Dict[str, Any]]:
        """
        Get the nearest snapshot to a target date (looking backwards).
        Useful for comparisons like "1 week ago" when we might not have
        an exact snapshot for that day.
        """
        snapshots = self._load_snapshots()
        if not snapshots:
            return None

        # Look backwards up to 3 days for the nearest snapshot
        target = datetime.strptime(target_date, "%Y-%m-%d")
        for i in range(4):
            check_date = (target - timedelta(days=i)).strftime("%Y-%m-%d")
            if check_date in snapshots:
                return {"date": check_date, **snapshots[check_date]}

        return None

    def get_performance(self) -> Dict[str, Any]:
        """
        Calculate performance over various periods.
        Compares current (latest) snapshot to past snapshots.

        Returns performance for: 1W, 1M, 3M, YTD
        """
        snapshots = self._load_snapshots()
        if not snapshots:
            return {"periods": {}, "history": []}

        # Get sorted dates
        sorted_dates = sorted(snapshots.keys())
        latest_date = sorted_dates[-1]
        latest = snapshots[latest_date]

        today = datetime.now()
        periods = {
            "1W": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
            "1M": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            "3M": (today - timedelta(days=90)).strftime("%Y-%m-%d"),
            "YTD": f"{today.year}-01-01",
        }

        result = {}
        for period_label, target_date in periods.items():
            past_snapshot = self.get_nearest_snapshot(target_date)
            if not past_snapshot:
                result[period_label] = None
                continue

            past_value = past_snapshot.get("totalValue", 0)
            current_value = latest.get("totalValue", 0)

            total_change = current_value - past_value
            total_change_pct = (
                (total_change / past_value * 100) if past_value > 0 else 0
            )

            # Per-asset-type breakdown
            by_type = {}
            for asset_type in ["stock", "etf", "crypto", "custom", "cash"]:
                past_type = past_snapshot.get("byAssetType", {}).get(asset_type, {})
                current_type = latest.get("byAssetType", {}).get(asset_type, {})

                past_val = past_type.get("value", 0)
                curr_val = current_type.get("value", 0)
                change = curr_val - past_val
                change_pct = (change / past_val * 100) if past_val > 0 else 0

                by_type[asset_type] = {
                    "previousValue": past_val,
                    "currentValue": curr_val,
                    "change": change,
                    "changePercent": round(change_pct, 2),
                }

            result[period_label] = {
                "fromDate": past_snapshot["date"],
                "toDate": latest_date,
                "previousValue": past_value,
                "currentValue": current_value,
                "change": round(total_change, 2),
                "changePercent": round(total_change_pct, 2),
                "byAssetType": by_type,
            }

        # Include last 90 days of history for charting
        history = self.get_snapshots(days=90)

        return {"periods": result, "history": history}


# Singleton instance
portfolio_snapshot_service = PortfolioSnapshotService()
