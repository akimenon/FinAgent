"""
Industry-Specific KPI Configuration

This module defines the KPIs that matter for each industry.
KPIs are config-driven to allow easy extension without code changes.

Structure:
- INDUSTRY_MAPPING: Maps FMP sectors/industries to our analysis categories
- INDUSTRY_KPIS: Defines KPIs, thresholds, and context for each category
"""

# Map FMP sector/industry names to our analysis categories
INDUSTRY_MAPPING = {
    # Sector-level mappings (fallback)
    "sectors": {
        "Technology": "tech",
        "Consumer Cyclical": "consumer",
        "Communication Services": "communication",
        "Healthcare": "healthcare",
        "Financial Services": "financial",
        "Energy": "energy",
        "Industrials": "industrial",
        "Basic Materials": "materials",
        "Consumer Defensive": "consumer_defensive",
        "Real Estate": "real_estate",
        "Utilities": "utilities",
    },
    # Industry-level mappings (more specific, takes precedence)
    "industries": {
        # Tech Hardware
        "Consumer Electronics": "tech_hardware",
        "Computer Hardware": "tech_hardware",
        # Semiconductors
        "Semiconductors": "semiconductors",
        "Semiconductor Equipment & Materials": "semiconductors",
        # Software
        "Software - Infrastructure": "software",
        "Software - Application": "software",
        # EV / Auto
        "Auto Manufacturers": "ev_auto",
        "Auto - Electric": "ev_auto",
        # Internet / Cloud
        "Internet Content & Information": "internet",
        "Internet Retail": "ecommerce",
        # Banks
        "Banks - Diversified": "banking",
        "Banks - Regional": "banking",
        # Streaming / Media
        "Entertainment": "media",
        # Pharma / Biotech
        "Biotechnology": "biotech",
        "Drug Manufacturers": "pharma",
    }
}

# KPI definitions for each industry category
INDUSTRY_KPIS = {
    "ev_auto": {
        "name": "Electric Vehicles & Auto",
        "description": "For EV/Auto companies, focus on vehicle deliveries, production efficiency, and energy business growth.",
        "context": """
Key things to evaluate for EV companies:
• Automotive Revenue Growth: Are vehicle sales growing?
• Gross Margin: Can they make money on each car? (TSLA ~18%, LCID negative)
• Energy Segment: Diversification beyond cars (batteries, solar)
• Inventory Growth: High inventory = weak demand or production issues
• R&D Spending: Investment in future tech (FSD, batteries)
• Cash Burn: How long can they survive at current burn rate?
""",
        "kpis": [
            {
                "id": "auto_revenue",
                "name": "Automotive Revenue",
                "source": "segments",
                "segment_key": ["Automotive", "Automotive sales", "Vehicle sales"],
                "format": "currency",
                "show_yoy": True,
            },
            {
                "id": "energy_revenue",
                "name": "Energy Segment",
                "source": "segments",
                "segment_key": ["Energy Generation And Storage Segment", "Energy generation and storage", "Energy"],
                "format": "currency",
                "show_yoy": True,
                "optional": True,  # Not all auto companies have this
            },
            {
                "id": "inventory_growth",
                "name": "Inventory Growth",
                "source": "growth",
                "key": "inventoryGrowth",
                "format": "percent",
                "warning_above": 30,
                "warning_message": "High inventory growth may indicate weak demand",
                "positive_below": -10,
                "positive_message": "Inventory declining - strong demand",
            },
            {
                "id": "gross_margin_trend",
                "name": "Gross Profit Growth",
                "source": "growth",
                "key": "grossProfitGrowth",
                "format": "percent",
                "warning_below": -20,
                "warning_message": "Gross profit declining - margin pressure",
            },
            {
                "id": "rd_growth",
                "name": "R&D Investment Growth",
                "source": "growth",
                "key": "rdexpenseGrowth",
                "format": "percent",
                "context": "R&D investment for future tech (batteries, autonomy)",
            },
        ],
        "red_flags": [
            {"condition": "gross_margin < 0", "message": "Negative gross margin - losing money on each vehicle sold"},
            {"condition": "revenue_growth < -10 and inventory_growth > 20", "message": "Revenue declining while inventory builds - serious demand concern"},
        ]
    },

    "tech_hardware": {
        "name": "Technology Hardware",
        "description": "For hardware companies like Apple, focus on product mix shifts and services growth.",
        "context": """
Key things to evaluate for tech hardware:
• Product Revenue Mix: Which products are growing/shrinking?
• Services Revenue: High-margin recurring revenue (subscriptions, cloud)
• Geographic Diversification: Exposure to China, emerging markets
• Gross Margin: Hardware margins vs services margins
• R&D Investment: Innovation pipeline
""",
        "kpis": [
            {
                "id": "services_revenue",
                "name": "Services Revenue",
                "source": "segments",
                "segment_key": ["Services", "Service"],
                "format": "currency",
                "show_yoy": True,
                "positive_growth_above": 10,
                "positive_message": "Services growing - high margin recurring revenue",
            },
            {
                "id": "product_mix",
                "name": "Product Segments",
                "source": "segments",
                "segment_key": "all",  # Show all segments
                "format": "breakdown",
            },
            {
                "id": "geo_concentration",
                "name": "Geographic Revenue",
                "source": "geo_segments",
                "segment_key": "all",
                "format": "breakdown",
                "highlight_key": ["Greater China", "China"],
                "context": "China exposure can be a risk factor",
            },
        ]
    },

    "semiconductors": {
        "name": "Semiconductors",
        "description": "For chip companies, focus on end-market exposure and inventory cycles.",
        "context": """
Key things to evaluate for semiconductor companies:
• Data Center Revenue: AI/cloud demand driver (NVDA's key segment)
• Gaming Revenue: Consumer discretionary, more cyclical
• Inventory Levels: Chip inventory cycles drive boom/bust
• R&D Intensity: Staying ahead in process technology
• Gross Margin: Indicator of pricing power and mix
""",
        "kpis": [
            {
                "id": "datacenter_revenue",
                "name": "Data Center Revenue",
                "source": "segments",
                "segment_key": ["Data Center", "Datacenter", "Compute & Networking"],
                "format": "currency",
                "show_yoy": True,
            },
            {
                "id": "gaming_revenue",
                "name": "Gaming Revenue",
                "source": "segments",
                "segment_key": ["Gaming", "Graphics"],
                "format": "currency",
                "show_yoy": True,
                "optional": True,
            },
            {
                "id": "inventory_growth",
                "name": "Inventory Growth",
                "source": "growth",
                "key": "inventoryGrowth",
                "format": "percent",
                "warning_above": 40,
                "warning_message": "High inventory - potential oversupply",
            },
            {
                "id": "rd_intensity",
                "name": "R&D Growth",
                "source": "growth",
                "key": "rdexpenseGrowth",
                "format": "percent",
            },
        ]
    },

    "software": {
        "name": "Software & SaaS",
        "description": "For software companies, focus on recurring revenue and growth efficiency.",
        "context": """
Key things to evaluate for software/SaaS:
• Revenue Growth: High growth expected for SaaS
• Gross Margin: Should be 70%+ for pure software
• Operating Margin: Path to profitability
• R&D Investment: Product development
""",
        "kpis": [
            {
                "id": "revenue_growth",
                "name": "Revenue Growth",
                "source": "growth",
                "key": "revenueGrowth",
                "format": "percent",
                "warning_below": 10,
                "warning_message": "Slowing growth for a software company",
                "positive_above": 25,
                "positive_message": "Strong growth trajectory",
            },
            {
                "id": "gross_margin",
                "name": "Gross Margin Trend",
                "source": "growth",
                "key": "grossProfitGrowth",
                "format": "percent",
            },
        ]
    },

    "banking": {
        "name": "Banking & Financial Services",
        "description": "For banks, focus on net interest income and credit quality.",
        "context": """
Key things to evaluate for banks:
• Net Interest Income: Core earnings from lending
• Provision for Credit Losses: Indicator of loan quality expectations
• Efficiency Ratio: Operating expenses / Revenue (lower is better)
• Book Value Growth: Tangible equity per share
""",
        "kpis": [
            {
                "id": "revenue_growth",
                "name": "Revenue Growth",
                "source": "growth",
                "key": "revenueGrowth",
                "format": "percent",
            },
            {
                "id": "book_value_growth",
                "name": "Book Value Growth",
                "source": "growth",
                "key": "bookValueperShareGrowth",
                "format": "percent",
                "positive_above": 5,
                "positive_message": "Growing book value",
            },
        ]
    },

    # Default fallback for industries we don't have specific config for
    "default": {
        "name": "General Analysis",
        "description": "Standard financial analysis for all companies.",
        "context": """
Key things to evaluate for any company:
• Revenue Growth: Is the business growing?
• Profit Margins: Is growth profitable?
• Cash Flow: Is the company generating cash?
• Debt Levels: Can they service their debt?
• R&D/CapEx: Are they investing in the future?
""",
        "kpis": [
            {
                "id": "revenue_growth",
                "name": "Revenue Growth",
                "source": "growth",
                "key": "revenueGrowth",
                "format": "percent",
                "warning_below": -5,
                "warning_message": "Revenue declining",
                "positive_above": 15,
                "positive_message": "Strong revenue growth",
            },
            {
                "id": "profit_growth",
                "name": "Net Income Growth",
                "source": "growth",
                "key": "netIncomeGrowth",
                "format": "percent",
            },
            {
                "id": "fcf_growth",
                "name": "Free Cash Flow Growth",
                "source": "growth",
                "key": "freeCashFlowGrowth",
                "format": "percent",
            },
        ]
    }
}


def get_industry_category(sector: str, industry: str) -> str:
    """
    Map a company's sector/industry to our analysis category.
    Industry mapping takes precedence over sector mapping.
    """
    # Try industry first (more specific)
    if industry and industry in INDUSTRY_MAPPING["industries"]:
        return INDUSTRY_MAPPING["industries"][industry]

    # Fall back to sector
    if sector and sector in INDUSTRY_MAPPING["sectors"]:
        return INDUSTRY_MAPPING["sectors"][sector]

    return "default"


def get_kpi_config(category: str) -> dict:
    """Get the KPI configuration for an industry category."""
    return INDUSTRY_KPIS.get(category, INDUSTRY_KPIS["default"])
