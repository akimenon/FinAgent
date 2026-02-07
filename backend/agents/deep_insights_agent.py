"""
Deep Insights Agent - LLM-Powered Comprehensive Financial Analysis

This agent uses the LLM to dynamically analyze companies and surface insights
that regular retail investors typically miss. It adapts its analysis based on
the industry without any hardcoded rules.
"""

from typing import Dict, List, Any, Optional
import json
import logging
from services.llm_service import llm_service
from config import settings

logger = logging.getLogger(__name__)


def _safe_float(value, default=0):
    """Safely convert a value to float, handling None and strings."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _format_currency(value, decimals=1):
    """Format large currency values in abbreviated format (B/M/K)."""
    if value is None:
        return "N/A"
    try:
        num = float(value)
        abs_num = abs(num)
        if abs_num >= 1e12:
            return f"${num / 1e12:.{decimals}f}T"
        if abs_num >= 1e9:
            return f"${num / 1e9:.{decimals}f}B"
        if abs_num >= 1e6:
            return f"${num / 1e6:.{decimals}f}M"
        if abs_num >= 1e3:
            return f"${num / 1e3:.{decimals}f}K"
        return f"${num:.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


class DeepInsightsAgent:
    """
    LLM-powered agent for comprehensive financial analysis.

    Key principle: NO HARDCODING. The LLM determines what matters for each
    company/industry dynamically based on the data provided.
    """

    SYSTEM_PROMPT = """You are a senior equity research analyst with 20 years of experience covering multiple sectors.
Your job is to analyze companies and surface DEEP INSIGHTS that regular retail investors typically miss.

## YOUR ANALYSIS APPROACH

1. **FIRST identify the industry** and determine what metrics matter MOST for THIS specific type of company
2. **Look for OPERATIONAL insights** - not just financial ratios, but business-specific KPIs
3. **Identify HIDDEN patterns** - relationships between metrics that reveal the real story
4. **Flag RED FLAGS** - concerning trends that could hurt the stock
5. **Highlight OPPORTUNITIES** - positive signals others might miss
6. **Explain for beginners** - make your insights accessible to new investors

## INDUSTRY-AWARE THINKING (Examples, but YOU decide what matters)

- **EV/Auto**: Deliveries trend, ASP, energy segment diversification, inventory vs sales, gross margin path to profitability
- **Tech Hardware**: Product mix shifts, services growth (high margin), geographic concentration risks
- **Semiconductors**: Data center vs gaming exposure, inventory cycles, R&D intensity, customer concentration
- **SaaS/Software**: Revenue growth rate, gross margins (should be 70%+), path to profitability, customer metrics
- **Banks**: Net interest margin trends, credit quality, efficiency ratio, loan growth
- **Retail**: Same-store sales, inventory turnover, e-commerce mix, margin pressure
- **Pharma/Biotech**: Pipeline progress, patent cliffs, R&D productivity, cash runway

But DO NOT be limited to these - analyze what YOU think matters most based on the actual data.

## OUTPUT REQUIREMENTS

- Be SPECIFIC with numbers (e.g., "Revenue grew 15% but cost of revenue grew 25% - margin compression")
- COMPARE across quarters to identify trends, not just point-in-time snapshots
- Explain WHY something matters, not just WHAT it is
- Calculate DERIVED metrics when useful (e.g., implied deliveries = revenue / ASP, cash runway = cash / burn rate)
- Provide ACTIONABLE insights - what should an investor watch for?

## NUMBER FORMATTING (CRITICAL)

ALWAYS format large dollar amounts in abbreviated format:
- Billions: Use "B" suffix (e.g., "$50.5B" NOT "$50,534M" or "$50,534,000,000")
- Millions: Use "M" suffix (e.g., "$125.5M" NOT "$125,500,000")
- Thousands: Use "K" suffix (e.g., "$50K" NOT "$50,000")
- Keep 1 decimal place for precision (e.g., "$57.0B", "$2.3M")

## RESPONSE FORMAT (JSON ONLY)

You must respond with valid JSON matching this structure:
{
    "industryContext": {
        "industry": "string - the specific industry",
        "whatMatters": "string - 2-3 sentences on what metrics matter most for this type of company",
        "keyKPIs": ["list", "of", "3-5", "key", "metrics"]
    },
    "operationalInsights": [
        {
            "metric": "string - name of the metric",
            "value": "string - the calculated/observed value",
            "trend": "string - how it's changing (optional)",
            "interpretation": "string - what this means for the business"
        }
    ],
    "deepDive": {
        "revenueQuality": "string - analysis of revenue sustainability and quality",
        "marginAnalysis": "string - deep look at margin trends and drivers",
        "cashFlowHealth": "string - operating cash flow, FCF, burn rate analysis",
        "balanceSheetStrength": "string - debt, liquidity, capital structure"
    },
    "hiddenInsights": [
        {
            "finding": "string - the hidden pattern or insight",
            "significance": "string - why this matters",
            "actionable": "string - what to watch for"
        }
    ],
    "risks": [
        {
            "risk": "string - the risk",
            "severity": "HIGH|MEDIUM|LOW",
            "explanation": "string - why this is a risk"
        }
    ],
    "opportunities": [
        {
            "opportunity": "string - the opportunity",
            "explanation": "string - why this is positive"
        }
    ],
    "beginnerExplanation": "string - 3-4 sentence summary a beginner investor would understand. What is this company, is it doing well or poorly, and what's the main thing to watch?"
}"""

    CLAUDE_SYSTEM_PROMPT = """You are a top-tier buy-side equity analyst writing an internal investment memo.
You have 20+ years of experience and your fund pays you to find alpha — not to summarize.

## YOUR MANDATE

Skip the preamble. No "let me analyze" or "here's my take." Just go straight to the analysis like a pro writing for other pros.

## ANALYSIS FRAMEWORK

1. **SNAPSHOT**: In 2-3 sentences, what is this company RIGHT NOW? Not the Wikipedia version — the investor version. What's the current narrative, and is the market pricing it correctly?

2. **WHAT THE NUMBERS SAY**: Don't just recite metrics. Tell the STORY the numbers are telling:
   - Revenue trajectory: accelerating, decelerating, or inflecting?
   - Margin story: expanding from operating leverage, or compressing from competition?
   - Cash generation: is the business a cash machine or a cash incinerator?
   - Balance sheet: fortress or house of cards?
   Use specific numbers. Compare quarters. Show the trend.

3. **BULL CASE** (3-5 points): What goes RIGHT? Be specific and quantitative.
   - Not "AI could help" but "AI segment grew 40% QoQ to $X.XB, if it sustains this becomes a $XXB business by 2026"

4. **BEAR CASE** (3-5 points): What goes WRONG? Be honest, not balanced for the sake of balance.
   - Not "competition could increase" but "AWS and Azure are both offering similar services at 30% lower pricing"

5. **HIDDEN SIGNALS**: What are 2-3 things in the data that most analysts are NOT talking about?
   - Inventory building that signals demand weakness?
   - SBC creeping up faster than revenue?
   - Geographic concentration risk?
   - Deferred revenue changes signaling future revenue shifts?

6. **VERDICT**: Give a clear conviction call:
   - Conviction level: HIGH_BUY, LEAN_BULL, NEUTRAL, LEAN_BEAR, or HIGH_SELL
   - 2-3 sentence reasoning
   - The ONE thing that would change your mind
   - Price target logic (not a specific price, but the framework: "trading at X multiple, deserves Y because Z")

## NUMBER FORMATTING (CRITICAL)

ALWAYS format large dollar amounts in abbreviated format:
- Billions: "$50.5B" NOT "$50,534,000,000"
- Millions: "$125.5M" NOT "$125,500,000"
- Keep 1 decimal place (e.g., "$57.0B", "$2.3M")

## RESPONSE FORMAT (JSON ONLY)

You must respond with valid JSON matching this structure:
{
    "snapshot": "string - 2-3 sentence investor snapshot of the company right now",
    "numbersSay": "string - multi-paragraph narrative of what the financial data reveals (revenue, margins, cash flow, balance sheet)",
    "bullCase": ["string - specific bull point 1", "string - specific bull point 2", "..."],
    "bearCase": ["string - specific bear point 1", "string - specific bear point 2", "..."],
    "hiddenSignals": ["string - hidden signal 1", "string - hidden signal 2", "..."],
    "verdict": {
        "conviction": "HIGH_BUY | LEAN_BULL | NEUTRAL | LEAN_BEAR | HIGH_SELL",
        "reasoning": "string - 2-3 sentence reasoning for the conviction",
        "keyMonitor": "string - the ONE thing that would change your mind",
        "priceTargetLogic": "string - valuation framework and what multiple the stock deserves"
    }
}

Return ONLY valid JSON. No markdown, no commentary outside the JSON."""

    def __init__(self):
        self.use_claude = settings.USE_CLAUDE_FOR_DEEP_INSIGHTS
        self.provider = "ollama"

        if self.use_claude:
            if not settings.ANTHROPIC_API_KEY:
                logger.warning(
                    "USE_CLAUDE_FOR_DEEP_INSIGHTS is enabled but ANTHROPIC_API_KEY is not set. "
                    "Falling back to Ollama."
                )
                self.use_claude = False
            else:
                from services.claude_llm_service import claude_llm_service
                self.llm = claude_llm_service
                self.provider = "claude"
                logger.info("Deep Insights Agent using Claude API")

        if not self.use_claude:
            self.llm = llm_service

    async def analyze(self, comprehensive_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform deep analysis using LLM on comprehensive financial data.

        Args:
            comprehensive_data: Dict containing all financial data for the company

        Returns:
            Structured insights from LLM analysis
        """
        # Prepare comprehensive context for the LLM
        context = self._prepare_comprehensive_context(comprehensive_data)

        company_name = comprehensive_data.get("profile", {}).get("companyName", "Unknown")
        symbol = comprehensive_data.get("profile", {}).get("symbol", "N/A")
        industry = comprehensive_data.get("profile", {}).get("industry", "Unknown")

        try:
            if self.use_claude:
                system_prompt = self.CLAUDE_SYSTEM_PROMPT
                max_tokens = 4096
                user_content = f"""Analyze this company. Here is all the financial data I have:

{context}

Give me the full analysis: bull case, bear case, hidden signals, and your verdict.
What's the honest prediction here - where is this stock likely headed and why?"""
            else:
                system_prompt = self.SYSTEM_PROMPT
                max_tokens = 3500
                user_content = f"""Perform a comprehensive deep-dive analysis of {company_name} ({symbol}) - a {industry} company.

{context}

Analyze this data thoroughly and provide insights that regular retail investors would miss.
Focus on what matters MOST for this specific industry.
Return your analysis as a JSON object following the specified format. Return ONLY valid JSON."""

            response_text = self.llm.chat(
                messages=[{"role": "user", "content": user_content}],
                system=system_prompt,
                temperature=0.4,
                max_tokens=max_tokens,
            )

            # Clean up potential markdown formatting
            cleaned_response = self._clean_json_response(response_text)

            result = json.loads(cleaned_response)
            result["_meta"] = {
                "symbol": symbol,
                "analyzedAt": self._get_timestamp(),
                "success": True,
                "provider": self.provider,
            }
            return result

        except json.JSONDecodeError as e:
            return self._fallback_analysis(comprehensive_data, str(e))
        except Exception as e:
            return self._error_response(str(e), comprehensive_data)

    def _prepare_comprehensive_context(self, data: Dict[str, Any]) -> str:
        """
        Prepare a comprehensive context string with all available financial data.
        This gives the LLM everything it needs to provide deep insights.
        """
        parts = []

        # === COMPANY PROFILE ===
        profile = data.get("profile", {})
        parts.append("=" * 60)
        parts.append("COMPANY PROFILE")
        parts.append("=" * 60)
        parts.append(f"""
Company: {profile.get('companyName', 'Unknown')}
Symbol: {profile.get('symbol', 'N/A')}
Sector: {profile.get('sector', 'N/A')}
Industry: {profile.get('industry', 'N/A')}
Market Cap: {_format_currency(profile.get('mktCap', 0))}
Employees: {profile.get('fullTimeEmployees', 'N/A')}
CEO: {profile.get('ceo', 'N/A')}
""")

        # === QUARTERLY PERFORMANCE (12 quarters = 3 years) ===
        income_statements = data.get("income_statements", [])
        if income_statements:
            parts.append("=" * 60)
            parts.append("QUARTERLY PERFORMANCE (Last 12 Quarters)")
            parts.append("=" * 60)

            for i, q in enumerate(income_statements[:12]):
                revenue = _safe_float(q.get('revenue', 0))
                gross_profit = _safe_float(q.get('grossProfit', 0))
                operating_income = _safe_float(q.get('operatingIncome', 0))
                net_income = _safe_float(q.get('netIncome', 0))

                gross_margin = (gross_profit / revenue * 100) if revenue else 0
                op_margin = (operating_income / revenue * 100) if revenue else 0
                net_margin = (net_income / revenue * 100) if revenue else 0

                parts.append(f"""
{q.get('period', 'Q?')} {q.get('fiscalYear', '')}:
  Revenue: {_format_currency(revenue)}
  Gross Profit: {_format_currency(gross_profit)} ({gross_margin:.1f}% margin)
  Operating Income: {_format_currency(operating_income)} ({op_margin:.1f}% margin)
  Net Income: {_format_currency(net_income)} ({net_margin:.1f}% margin)
  EPS: ${_safe_float(q.get('eps', 0)):.2f}
  Cost of Revenue: {_format_currency(q.get('costOfRevenue', 0))}
  R&D Expense: {_format_currency(q.get('researchAndDevelopmentExpenses', 0))}
  SG&A Expense: {_format_currency(q.get('sellingGeneralAndAdministrativeExpenses', 0))}
""")

        # === PRODUCT SEGMENTS ===
        product_segments = data.get("product_segments", [])
        if product_segments:
            parts.append("=" * 60)
            parts.append("PRODUCT/BUSINESS SEGMENT BREAKDOWN")
            parts.append("=" * 60)

            for seg in product_segments[:3]:  # Last 3 years
                parts.append(f"\nFiscal Year {seg.get('fiscalYear', 'N/A')}:")
                seg_data = seg.get('data', {})
                # Convert all values to float for safe calculations
                seg_data_float = {k: _safe_float(v) for k, v in seg_data.items()}
                total = sum(seg_data_float.values()) if seg_data_float else 0
                for name, value in sorted(seg_data_float.items(), key=lambda x: x[1], reverse=True):
                    share = (value / total * 100) if total else 0
                    parts.append(f"  {name}: {_format_currency(value)} ({share:.1f}% of total)")

        # === GEOGRAPHIC SEGMENTS ===
        geo_segments = data.get("geo_segments", [])
        if geo_segments:
            parts.append("=" * 60)
            parts.append("GEOGRAPHIC REVENUE BREAKDOWN")
            parts.append("=" * 60)

            for seg in geo_segments[:2]:  # Last 2 years
                parts.append(f"\nFiscal Year {seg.get('fiscalYear', 'N/A')}:")
                seg_data = seg.get('data', {})
                # Convert all values to float for safe calculations
                seg_data_float = {k: _safe_float(v) for k, v in seg_data.items()}
                total = sum(seg_data_float.values()) if seg_data_float else 0
                for name, value in sorted(seg_data_float.items(), key=lambda x: x[1], reverse=True):
                    share = (value / total * 100) if total else 0
                    parts.append(f"  {name}: {_format_currency(value)} ({share:.1f}%)")

        # === BALANCE SHEET ===
        balance_sheet = data.get("balance_sheet", [])
        if balance_sheet:
            latest_bs = balance_sheet[0]
            parts.append("=" * 60)
            parts.append("BALANCE SHEET (Latest)")
            parts.append("=" * 60)

            cash = _safe_float(latest_bs.get('cashAndCashEquivalents', 0))
            short_investments = _safe_float(latest_bs.get('shortTermInvestments', 0))
            total_cash = cash + short_investments
            short_debt = _safe_float(latest_bs.get('shortTermDebt', 0))
            long_debt = _safe_float(latest_bs.get('longTermDebt', 0))
            total_debt = short_debt + long_debt
            equity = _safe_float(latest_bs.get('totalStockholdersEquity', 0))
            total_assets = _safe_float(latest_bs.get('totalAssets', 0))
            inventory = _safe_float(latest_bs.get('inventory', 0))
            debt_to_equity = f"{(total_debt / equity):.2f}x" if equity > 0 else 'N/A'

            parts.append(f"""
Cash & Equivalents: {_format_currency(cash)}
Short-term Investments: {_format_currency(short_investments)}
Total Cash Position: {_format_currency(total_cash)}
Inventory: {_format_currency(inventory)}
Total Assets: {_format_currency(total_assets)}
Short-term Debt: {_format_currency(short_debt)}
Long-term Debt: {_format_currency(long_debt)}
Total Debt: {_format_currency(total_debt)}
Shareholders' Equity: {_format_currency(equity)}
Debt-to-Equity: {debt_to_equity}
Net Cash (Debt): {_format_currency(total_cash - total_debt)}
""")

        # === CASH FLOW ===
        cash_flow = data.get("cash_flow", [])
        if cash_flow:
            latest_cf = cash_flow[0]
            parts.append("=" * 60)
            parts.append("CASH FLOW (Latest Quarter)")
            parts.append("=" * 60)

            op_cf = _safe_float(latest_cf.get('operatingCashFlow', 0))
            capex = _safe_float(latest_cf.get('capitalExpenditure', 0))
            fcf = _safe_float(latest_cf.get('freeCashFlow', 0))
            dividends = _safe_float(latest_cf.get('commonDividendsPaid', 0))
            buybacks = _safe_float(latest_cf.get('commonStockRepurchased', 0))

            parts.append(f"""
Operating Cash Flow: {_format_currency(op_cf)}
Capital Expenditure: {_format_currency(capex)}
Free Cash Flow: {_format_currency(fcf)}
Dividends Paid: {_format_currency(dividends)}
Stock Buybacks: {_format_currency(buybacks)}
""")

        # === GROWTH METRICS ===
        growth_metrics = data.get("financial_growth", [])
        if growth_metrics:
            latest_growth = growth_metrics[0]
            parts.append("=" * 60)
            parts.append("GROWTH METRICS (Latest Quarter vs Prior Year)")
            parts.append("=" * 60)

            parts.append(f"""
Revenue Growth: {_safe_float(latest_growth.get('revenueGrowth', 0)) * 100:.1f}%
Gross Profit Growth: {_safe_float(latest_growth.get('grossProfitGrowth', 0)) * 100:.1f}%
Operating Income Growth: {_safe_float(latest_growth.get('operatingIncomeGrowth', 0)) * 100:.1f}%
Net Income Growth: {_safe_float(latest_growth.get('netIncomeGrowth', 0)) * 100:.1f}%
EPS Growth: {_safe_float(latest_growth.get('epsgrowth', 0)) * 100:.1f}%
Inventory Growth: {_safe_float(latest_growth.get('inventoryGrowth', 0)) * 100:.1f}%
R&D Expense Growth: {_safe_float(latest_growth.get('rdexpenseGrowth', 0)) * 100:.1f}%
SG&A Expense Growth: {_safe_float(latest_growth.get('sgaexpensesGrowth', 0)) * 100:.1f}%
Free Cash Flow Growth: {_safe_float(latest_growth.get('freeCashFlowGrowth', 0)) * 100:.1f}%
""")

        # === EARNINGS HISTORY ===
        earnings = data.get("earnings_surprises", [])
        if earnings:
            parts.append("=" * 60)
            parts.append("EARNINGS SURPRISE HISTORY")
            parts.append("=" * 60)

            beats = sum(1 for e in earnings if _safe_float(e.get('epsActual')) > _safe_float(e.get('epsEstimated')))
            total = len([e for e in earnings if e.get('epsActual') is not None])
            beat_rate = (beats / total * 100) if total else 0

            parts.append(f"\nBeat Rate: {beat_rate:.0f}% ({beats}/{total} quarters)")
            parts.append("\nRecent History:")

            for e in earnings[:8]:
                actual = _safe_float(e.get('epsActual'), None)
                estimated = _safe_float(e.get('epsEstimated'), None)
                if actual is not None and estimated is not None:
                    surprise = ((actual - estimated) / abs(estimated) * 100) if estimated else 0
                    result = "BEAT" if actual > estimated else "MISS" if actual < estimated else "MET"
                    parts.append(f"  {e.get('date', 'N/A')}: Actual ${actual:.2f} vs Est ${estimated:.2f} ({surprise:+.1f}%) - {result}")

        # === KEY RATIOS ===
        ratios = data.get("ratios", [])
        if ratios:
            latest_ratios = ratios[0]
            parts.append("=" * 60)
            parts.append("KEY FINANCIAL RATIOS")
            parts.append("=" * 60)

            parts.append(f"""
P/E Ratio: {latest_ratios.get('priceEarningsRatio', 'N/A')}
P/S Ratio: {latest_ratios.get('priceToSalesRatio', 'N/A')}
P/B Ratio: {latest_ratios.get('priceToBookRatio', 'N/A')}
EV/EBITDA: {latest_ratios.get('enterpriseValueOverEBITDA', 'N/A')}
ROE: {(latest_ratios.get('returnOnEquity', 0) or 0) * 100:.1f}%
ROA: {(latest_ratios.get('returnOnAssets', 0) or 0) * 100:.1f}%
Current Ratio: {latest_ratios.get('currentRatio', 'N/A')}
Quick Ratio: {latest_ratios.get('quickRatio', 'N/A')}
Debt/Equity: {latest_ratios.get('debtEquityRatio', 'N/A')}
""")

        return "\n".join(parts)

    def _clean_json_response(self, response_text: str) -> str:
        """Clean up LLM response to extract valid JSON."""
        # Remove markdown code blocks
        if "```" in response_text:
            parts = response_text.split("```")
            for part in parts:
                if part.strip().startswith("json"):
                    response_text = part[4:].strip()
                    break
                elif part.strip().startswith("{"):
                    response_text = part.strip()
                    break

        # Find JSON object
        if "{" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            response_text = response_text[start:end]

        return response_text.strip()

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    def _fallback_analysis(self, data: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Provide basic fallback analysis if LLM fails."""
        profile = data.get("profile", {})
        income = data.get("income_statements", [])

        latest = income[0] if income else {}
        revenue = latest.get("revenue", 0) or 0
        net_income = latest.get("netIncome", 0) or 0

        return {
            "industryContext": {
                "industry": profile.get("industry", "Unknown"),
                "whatMatters": "Unable to generate AI analysis. Showing basic metrics.",
                "keyKPIs": ["Revenue", "Net Income", "Margins"]
            },
            "operationalInsights": [
                {
                    "metric": "Latest Revenue",
                    "value": _format_currency(revenue),
                    "interpretation": "See quarterly data for trends"
                }
            ],
            "deepDive": {
                "revenueQuality": "Analysis unavailable",
                "marginAnalysis": f"Net margin: {(net_income/revenue*100):.1f}%" if revenue else "N/A",
                "cashFlowHealth": "Analysis unavailable",
                "balanceSheetStrength": "Analysis unavailable"
            },
            "hiddenInsights": [],
            "risks": [],
            "opportunities": [],
            "beginnerExplanation": f"{profile.get('companyName', 'This company')} is in the {profile.get('industry', 'unknown')} industry. AI analysis was unable to complete - please review the raw financial data.",
            "_meta": {
                "symbol": profile.get("symbol", "N/A"),
                "analyzedAt": self._get_timestamp(),
                "success": False,
                "error": f"JSON parsing failed: {error}",
                "provider": "ollama",  # fallback always uses Ollama schema shape
            }
        }

    def _error_response(self, error: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return error response."""
        profile = data.get("profile", {})
        return {
            "industryContext": {"industry": "Unknown", "whatMatters": "Analysis failed", "keyKPIs": []},
            "operationalInsights": [],
            "deepDive": {
                "revenueQuality": "Error",
                "marginAnalysis": "Error",
                "cashFlowHealth": "Error",
                "balanceSheetStrength": "Error"
            },
            "hiddenInsights": [],
            "risks": [],
            "opportunities": [],
            "beginnerExplanation": "Analysis could not be completed due to an error.",
            "_meta": {
                "symbol": profile.get("symbol", "N/A"),
                "analyzedAt": self._get_timestamp(),
                "success": False,
                "error": error,
                "provider": "ollama",  # error always uses Ollama schema shape
            }
        }


# Singleton instance
deep_insights_agent = DeepInsightsAgent()
