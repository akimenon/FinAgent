"""
Watchlist Service

File-based JSON storage for user watchlist.
Stores watchlist items with metadata for future features like alarms.

Structure:
data/watchlist/
└── watchlist.json
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class WatchlistService:
    """
    File-based watchlist storage.

    Each watchlist item contains:
    - symbol: Stock ticker
    - addedAt: When the stock was added
    - notes: Optional user notes
    - alarms: Future feature - price/earnings alarms
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            base_dir = Path(__file__).parent.parent
            data_dir = base_dir / "data" / "watchlist"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.watchlist_file = self.data_dir / "watchlist.json"

        # Initialize empty watchlist if file doesn't exist
        if not self.watchlist_file.exists():
            self._save_watchlist({})

    def _load_watchlist(self) -> Dict[str, Any]:
        """Load watchlist from JSON file."""
        try:
            with open(self.watchlist_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_watchlist(self, watchlist: Dict[str, Any]) -> None:
        """Save watchlist to JSON file."""
        with open(self.watchlist_file, 'w') as f:
            json.dump(watchlist, f, indent=2, default=str)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all watchlist items sorted by addedAt descending."""
        watchlist = self._load_watchlist()
        items = [{"symbol": symbol, **data} for symbol, data in watchlist.items()]
        items.sort(key=lambda x: x.get("addedAt", ""), reverse=True)
        return items

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get a specific watchlist item."""
        symbol = symbol.upper()
        watchlist = self._load_watchlist()
        if symbol in watchlist:
            return {"symbol": symbol, **watchlist[symbol]}
        return None

    def add(self, symbol: str, notes: str = None) -> Dict[str, Any]:
        """Add a stock to the watchlist."""
        symbol = symbol.upper()
        watchlist = self._load_watchlist()

        # If already exists, just update the notes if provided
        if symbol in watchlist:
            if notes is not None:
                watchlist[symbol]["notes"] = notes
                watchlist[symbol]["updatedAt"] = datetime.now().isoformat()
                self._save_watchlist(watchlist)
            return {"symbol": symbol, **watchlist[symbol], "alreadyExists": True}

        # Add new item
        item = {
            "addedAt": datetime.now().isoformat(),
            "notes": notes,
            "alarms": [],  # Future feature: price/earnings alarms
        }
        watchlist[symbol] = item
        self._save_watchlist(watchlist)

        return {"symbol": symbol, **item, "alreadyExists": False}

    def remove(self, symbol: str) -> bool:
        """Remove a stock from the watchlist."""
        symbol = symbol.upper()
        watchlist = self._load_watchlist()

        if symbol in watchlist:
            del watchlist[symbol]
            self._save_watchlist(watchlist)
            return True
        return False

    def is_in_watchlist(self, symbol: str) -> bool:
        """Check if a stock is in the watchlist."""
        symbol = symbol.upper()
        watchlist = self._load_watchlist()
        return symbol in watchlist

    def update_notes(self, symbol: str, notes: str) -> Optional[Dict[str, Any]]:
        """Update notes for a watchlist item."""
        symbol = symbol.upper()
        watchlist = self._load_watchlist()

        if symbol not in watchlist:
            return None

        watchlist[symbol]["notes"] = notes
        watchlist[symbol]["updatedAt"] = datetime.now().isoformat()
        self._save_watchlist(watchlist)

        return {"symbol": symbol, **watchlist[symbol]}

    def get_symbols(self) -> List[str]:
        """Get just the list of symbols in the watchlist."""
        watchlist = self._load_watchlist()
        return list(watchlist.keys())


# Singleton instance
watchlist_service = WatchlistService()
