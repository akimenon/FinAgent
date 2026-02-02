"""
Static company assets loader.

Loads company profiles (name, logo, sector, industry) from a pre-generated JSON file.
This avoids API calls for common company metadata.
"""

import json
from pathlib import Path
from typing import Dict, Optional

# Load company profiles once at module import
_ASSETS_PATH = Path(__file__).parent.parent / "assets" / "company_profiles.json"
_COMPANY_PROFILES: Dict[str, dict] = {}


def _load_profiles():
    """Load company profiles from the static JSON file."""
    global _COMPANY_PROFILES
    if _ASSETS_PATH.exists():
        with open(_ASSETS_PATH, "r") as f:
            _COMPANY_PROFILES = json.load(f)
        print(f"[ASSETS] Loaded {len(_COMPANY_PROFILES)} company profiles")
    else:
        print(f"[ASSETS] Warning: {_ASSETS_PATH} not found")


# Load on import
_load_profiles()


def get_company_info(symbol: str) -> Optional[dict]:
    """
    Get company info for a symbol.

    Returns:
        dict with name, logo, sector, industry or None if not found
    """
    return _COMPANY_PROFILES.get(symbol.upper())


def get_company_name(symbol: str) -> Optional[str]:
    """Get company name for a symbol."""
    info = _COMPANY_PROFILES.get(symbol.upper())
    return info.get("name") if info else None


def get_company_logo(symbol: str) -> Optional[str]:
    """Get company logo URL for a symbol."""
    info = _COMPANY_PROFILES.get(symbol.upper())
    return info.get("logo") if info else None


def enrich_with_company_info(items: list, symbol_key: str = "symbol") -> list:
    """
    Enrich a list of items with company info.

    Args:
        items: List of dicts containing symbol
        symbol_key: Key name for the symbol field

    Returns:
        Same list with companyName, logo, sector, industry added where available
    """
    for item in items:
        symbol = item.get(symbol_key)
        if symbol:
            info = _COMPANY_PROFILES.get(symbol.upper())
            if info:
                item["companyName"] = info.get("name")
                item["logo"] = info.get("logo")
                item["sector"] = info.get("sector")
                item["industry"] = info.get("industry")
    return items


def get_all_symbols() -> list:
    """Get list of all symbols with cached profiles."""
    return list(_COMPANY_PROFILES.keys())


def reload_profiles():
    """Reload profiles from disk (useful for updates)."""
    _load_profiles()
