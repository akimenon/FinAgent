"""
Portfolio Service

File-based JSON storage for user portfolio holdings.
Supports stocks, ETFs, and crypto with cost basis tracking.

Structure:
data/portfolio/
└── portfolio.json
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


# Known crypto tickers for auto-categorization
KNOWN_CRYPTOS = {
    "BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "DOT", "AVAX", "MATIC", "LINK",
    "SHIB", "LTC", "UNI", "ATOM", "XLM", "ALGO", "VET", "FIL", "HBAR", "ICP",
    "APT", "ARB", "OP", "NEAR", "INJ", "TIA", "SUI", "SEI", "JUP", "RENDER",
    "PEPE", "WIF", "BONK", "FLOKI", "MEME", "ONDO", "ENA", "JASMY", "FET",
}

# Known ETF tickers for auto-categorization
KNOWN_ETFS = {
    "SPY", "QQQ", "VOO", "VTI", "IWM", "ARKK", "SCHD", "VIG", "VYM", "JEPI",
    "VGT", "XLK", "XLF", "XLE", "XLV", "XLI", "XLC", "XLY", "XLP", "XLU",
    "IVV", "DIA", "VEA", "VWO", "EFA", "EEM", "AGG", "BND", "LQD", "HYG",
    "GLD", "SLV", "USO", "TLT", "IEF", "SHY", "IEMG", "VNQ", "SCHF", "SCHA",
    "SPLG", "SPTM", "VB", "VO", "VTV", "VUG", "VXUS", "ITOT", "IJH", "IJR",
    "QQQM", "QQQE", "SOXX", "SMH", "XBI", "IBB", "KWEB", "FXI", "MCHI",
}


def categorize_ticker(ticker: str) -> str:
    """Auto-categorize a ticker as stock, etf, or crypto."""
    ticker_upper = ticker.upper()
    if ticker_upper in KNOWN_CRYPTOS:
        return "crypto"
    if ticker_upper in KNOWN_ETFS:
        return "etf"
    return "stock"


class PortfolioService:
    """
    File-based portfolio storage.

    Each holding contains:
    - id: Unique holding ID
    - ticker: Stock/ETF/crypto ticker
    - quantity: Number of shares/units
    - costBasis: Cost per share/unit
    - accountName: Brokerage/exchange name
    - assetType: stock, etf, or crypto
    - addedAt: When the holding was added
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            base_dir = Path(__file__).parent.parent
            data_dir = base_dir / "data" / "portfolio"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.portfolio_file = self.data_dir / "portfolio.json"

        # Initialize empty portfolio if file doesn't exist
        if not self.portfolio_file.exists():
            self._save_portfolio({"holdings": {}})

    def _load_portfolio(self) -> Dict[str, Any]:
        """Load portfolio from JSON file."""
        try:
            with open(self.portfolio_file, 'r') as f:
                data = json.load(f)
                # Ensure structure
                if "holdings" not in data:
                    data = {"holdings": data if isinstance(data, dict) else {}}
                return data
        except (json.JSONDecodeError, IOError):
            return {"holdings": {}}

    def _save_portfolio(self, portfolio: Dict[str, Any]) -> None:
        """Save portfolio to JSON file."""
        with open(self.portfolio_file, 'w') as f:
            json.dump(portfolio, f, indent=2, default=str)

    def _generate_id(self) -> str:
        """Generate a unique holding ID."""
        return f"h_{int(time.time() * 1000)}"

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all holdings sorted by addedAt descending."""
        portfolio = self._load_portfolio()
        holdings = list(portfolio["holdings"].values())
        holdings.sort(key=lambda x: x.get("addedAt", ""), reverse=True)
        return holdings

    def get(self, holding_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific holding by ID."""
        portfolio = self._load_portfolio()
        return portfolio["holdings"].get(holding_id)

    def add(
        self,
        ticker: str,
        quantity: float,
        cost_basis: float,
        account_name: str,
        asset_type: str = None,
    ) -> Dict[str, Any]:
        """Add a new holding to the portfolio."""
        ticker = ticker.upper()
        portfolio = self._load_portfolio()

        # Auto-categorize if not specified
        if asset_type is None:
            asset_type = categorize_ticker(ticker)

        holding_id = self._generate_id()
        holding = {
            "id": holding_id,
            "ticker": ticker,
            "quantity": quantity,
            "costBasis": cost_basis,
            "accountName": account_name,
            "assetType": asset_type,
            "addedAt": datetime.now().isoformat(),
        }

        portfolio["holdings"][holding_id] = holding
        self._save_portfolio(portfolio)

        return holding

    def update(
        self,
        holding_id: str,
        quantity: float = None,
        cost_basis: float = None,
        account_name: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing holding."""
        portfolio = self._load_portfolio()

        if holding_id not in portfolio["holdings"]:
            return None

        holding = portfolio["holdings"][holding_id]

        if quantity is not None:
            holding["quantity"] = quantity
        if cost_basis is not None:
            holding["costBasis"] = cost_basis
        if account_name is not None:
            holding["accountName"] = account_name

        holding["updatedAt"] = datetime.now().isoformat()

        portfolio["holdings"][holding_id] = holding
        self._save_portfolio(portfolio)

        return holding

    def remove(self, holding_id: str) -> bool:
        """Remove a holding from the portfolio."""
        portfolio = self._load_portfolio()

        if holding_id in portfolio["holdings"]:
            del portfolio["holdings"][holding_id]
            self._save_portfolio(portfolio)
            return True
        return False

    def get_by_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        """Get all holdings for a specific ticker."""
        ticker = ticker.upper()
        portfolio = self._load_portfolio()
        return [
            h for h in portfolio["holdings"].values()
            if h["ticker"] == ticker
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get portfolio summary statistics."""
        holdings = self.get_all()

        summary = {
            "totalHoldings": len(holdings),
            "byAssetType": {
                "stock": [],
                "etf": [],
                "crypto": [],
                "custom": [],
                "cash": [],
            },
            "accounts": set(),
        }

        for holding in holdings:
            asset_type = holding.get("assetType", "stock")
            if asset_type in summary["byAssetType"]:
                summary["byAssetType"][asset_type].append(holding)
            summary["accounts"].add(holding.get("accountName", "Unknown"))

        summary["accounts"] = list(summary["accounts"])
        return summary


# Singleton instance
portfolio_service = PortfolioService()
