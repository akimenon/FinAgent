"""
Shared utility functions for the backend.

Contains common helpers for type conversion and financial data processing.
"""

from datetime import datetime
from typing import Any, Optional


def safe_float(value: Any, default: float = 0) -> float:
    """Safely convert a value to float, handling None and strings."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, handling None and strings."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def find_price_near_date(
    prices: list,
    target_date,
    tolerance_days: int = 7
) -> Optional[float]:
    """
    Find closing price for trading day closest to target_date.

    Args:
        prices: List of price records with 'date' and 'close'/'adjClose' fields
        target_date: Target date (datetime or date object)
        tolerance_days: Maximum days from target to accept a match

    Returns:
        Closing price if found within tolerance, None otherwise
    """
    target_dt = target_date.date() if hasattr(target_date, 'date') else target_date
    best_match = None
    best_diff = float('inf')

    for record in prices:
        date_str = record.get("date", "")
        if not date_str:
            continue
        try:
            record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            diff = abs((record_date - target_dt).days)
            if diff <= tolerance_days and diff < best_diff:
                best_diff = diff
                best_match = record.get("close") or record.get("adjClose")
                if diff == 0:
                    break
        except ValueError:
            continue

    return best_match


def calc_pct_change(current: Any, previous: Any) -> Optional[float]:
    """
    Calculate percentage change between two values.

    Returns None if either value is None/0.
    """
    current = safe_float(current, None)
    previous = safe_float(previous, None)
    if current is None or previous is None or previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 2)
