"""
RAG Chat Agent - Answers any question using comprehensive financial data.
Fetches ALL available data and passes it to Qwen for accurate answers.
"""
import asyncio
from typing import Dict, Any, Optional
from services.fmp_service import fmp_service
from services.llm_service import llm_service


class ChatAgent:
    """
    RAG-based chat agent that can answer any question about a company's financials.

    Architecture:
    1. Fetch ALL available financial data upfront
    2. Format data clearly with labels
    3. Pass complete data + user question to Qwen
    4. Qwen answers ONLY from provided data
    """

    SYSTEM_PROMPT = """You are a financial data assistant. You answer questions ONLY using the provided financial data.

CRITICAL RULES:
1. ONLY use data explicitly provided in the context below
2. If the data to answer a question is not provided, say "This information is not available in the provided financial data"
3. Always cite the specific numbers from the data
4. For revenue/income, specify the time period (quarter, fiscal year)
5. Be concise but complete

NUMBER FORMATTING (VERY IMPORTANT):
- ALWAYS format large numbers in a human-readable way
- Billions: $45,317,000,000 → "$45.32 billion" or "$45.32B"
- Millions: $123,456,789 → "$123.46 million" or "$123.46M"
- Thousands: $45,678 → "$45.68K"
- Round to 2 decimal places for readability
- NEVER output raw numbers like "$45,317,000,000" - always convert to billions/millions

When answering:
- Convert raw numbers to readable format (billions, millions)
- Specify the time period (e.g., "In FY2025..." or "For Q1 2025...")
- If comparing periods, show both numbers in readable format
- Keep answers concise"""

    def __init__(self):
        self.fmp = fmp_service
        self.llm = llm_service
        self._data_cache: Dict[str, Dict] = {}

    async def fetch_all_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch ALL available financial data for comprehensive Q&A.
        This is the RAG "retrieval" step.
        """
        symbol = symbol.upper()

        # Check cache first
        if symbol in self._data_cache:
            return self._data_cache[symbol]

        # Fetch all data in parallel
        tasks = {
            "profile": self.fmp.get_company_profile(symbol),
            "income_quarterly": self.fmp.get_income_statement(symbol, period="quarter", limit=5),
            "income_annual": self.fmp.get_income_statement(symbol, period="annual", limit=3),
            "balance_sheet": self.fmp.get_balance_sheet(symbol, period="quarter", limit=1),
            "cash_flow": self.fmp.get_cash_flow(symbol, period="quarter", limit=1),
            "earnings": self.fmp.get_earnings_surprises(symbol, limit=5),
            "product_segments": self.fmp.get_revenue_product_segmentation(symbol),
            "geo_segments": self.fmp.get_revenue_geographic_segmentation(symbol),
            "ratios": self.fmp.get_ratios(symbol, period="quarter", limit=1),
            "key_metrics": self.fmp.get_key_metrics(symbol, period="quarter", limit=1),
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        data = {}
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                data[key] = None
            else:
                data[key] = result

        # Cache for subsequent questions
        self._data_cache[symbol] = data
        return data

    def format_data_context(self, data: Dict[str, Any], symbol: str) -> str:
        """
        Format all financial data into a clear text context for Qwen.
        This is the RAG "augmentation" step.
        """
        parts = []

        # Company Profile
        profile = data.get("profile") or {}
        parts.append(f"""
=== COMPANY PROFILE ===
Company: {profile.get('companyName', symbol)} ({symbol})
Sector: {profile.get('sector', 'N/A')}
Industry: {profile.get('industry', 'N/A')}
CEO: {profile.get('ceo', 'N/A')}
Employees: {profile.get('fullTimeEmployees', 'N/A')}
Market Cap: ${profile.get('marketCap', 0):,.0f}
Current Price: ${profile.get('price', 0):.2f}
52-Week Range: {profile.get('range', 'N/A')}
""")

        # Quarterly Income Statements
        income_q = data.get("income_quarterly") or []
        if income_q:
            parts.append("\n=== QUARTERLY INCOME STATEMENTS ===")
            for q in income_q[:5]:
                period = f"{q.get('period', 'Q?')} {q.get('fiscalYear', '')}"
                parts.append(f"""
{period} (reported {q.get('date', 'N/A')}):
  Revenue: ${q.get('revenue', 0):,.0f}
  Gross Profit: ${q.get('grossProfit', 0):,.0f}
  Operating Income: ${q.get('operatingIncome', 0):,.0f}
  Net Income: ${q.get('netIncome', 0):,.0f}
  EPS: ${q.get('eps', 0):.2f}
  Gross Margin: {(q.get('grossProfit', 0) / q.get('revenue', 1) * 100):.1f}%
  Operating Margin: {(q.get('operatingIncome', 0) / q.get('revenue', 1) * 100):.1f}%
  Net Margin: {(q.get('netIncome', 0) / q.get('revenue', 1) * 100):.1f}%
""")

        # Annual Income Statements
        income_a = data.get("income_annual") or []
        if income_a:
            parts.append("\n=== ANNUAL INCOME STATEMENTS ===")
            for y in income_a[:3]:
                parts.append(f"""
FY{y.get('fiscalYear', 'N/A')} (ended {y.get('date', 'N/A')}):
  Revenue: ${y.get('revenue', 0):,.0f}
  Gross Profit: ${y.get('grossProfit', 0):,.0f}
  Operating Income: ${y.get('operatingIncome', 0):,.0f}
  Net Income: ${y.get('netIncome', 0):,.0f}
  EPS: ${y.get('eps', 0):.2f}
""")

        # Balance Sheet
        balance = data.get("balance_sheet") or []
        if balance:
            b = balance[0]
            parts.append(f"""
=== BALANCE SHEET (Latest: {b.get('date', 'N/A')}) ===
Cash & Cash Equivalents: ${b.get('cashAndCashEquivalents', 0):,.0f}
Short-term Investments: ${b.get('shortTermInvestments', 0):,.0f}
Total Cash & Investments: ${b.get('cashAndShortTermInvestments', 0):,.0f}
Accounts Receivable: ${b.get('netReceivables', 0):,.0f}
Inventory: ${b.get('inventory', 0):,.0f}
Total Current Assets: ${b.get('totalCurrentAssets', 0):,.0f}
Total Assets: ${b.get('totalAssets', 0):,.0f}
Accounts Payable: ${b.get('accountPayables', 0):,.0f}
Short-term Debt: ${b.get('shortTermDebt', 0):,.0f}
Long-term Debt: ${b.get('longTermDebt', 0):,.0f}
Total Debt: ${(b.get('shortTermDebt', 0) or 0) + (b.get('longTermDebt', 0) or 0):,.0f}
Total Liabilities: ${b.get('totalLiabilities', 0):,.0f}
Total Stockholders Equity: ${b.get('totalStockholdersEquity', 0):,.0f}
""")

        # Cash Flow
        cashflow = data.get("cash_flow") or []
        if cashflow:
            cf = cashflow[0]
            parts.append(f"""
=== CASH FLOW STATEMENT (Latest: {cf.get('date', 'N/A')}) ===
Operating Cash Flow: ${cf.get('operatingCashFlow', 0):,.0f}
Capital Expenditure: ${cf.get('capitalExpenditure', 0):,.0f}
Free Cash Flow: ${cf.get('freeCashFlow', 0):,.0f}
Dividends Paid: ${cf.get('commonDividendsPaid', 0):,.0f}
Stock Repurchased: ${cf.get('commonStockRepurchased', 0):,.0f}
Net Debt Issuance: ${cf.get('netDebtIssuance', 0):,.0f}
""")

        # Product Segments (iPhone, Mac, Services, etc.)
        product_seg = data.get("product_segments") or []
        if product_seg:
            parts.append("\n=== REVENUE BY PRODUCT SEGMENT ===")
            for seg in product_seg[:3]:  # Last 3 years
                parts.append(f"\nFY{seg.get('fiscalYear', 'N/A')}:")
                seg_data = seg.get('data', {})
                for product, revenue in seg_data.items():
                    parts.append(f"  {product}: ${revenue:,.0f}")

        # Geographic Segments
        geo_seg = data.get("geo_segments") or []
        if geo_seg:
            parts.append("\n=== REVENUE BY GEOGRAPHY ===")
            for seg in geo_seg[:3]:  # Last 3 years
                parts.append(f"\nFY{seg.get('fiscalYear', 'N/A')}:")
                seg_data = seg.get('data', {})
                for region, revenue in seg_data.items():
                    parts.append(f"  {region}: ${revenue:,.0f}")

        # Earnings Surprises
        earnings = data.get("earnings") or []
        if earnings:
            parts.append("\n=== EARNINGS HISTORY (Actual vs Estimated) ===")
            for e in earnings[:5]:
                if e.get('epsActual') is not None:
                    actual = e.get('epsActual', 0)
                    estimated = e.get('epsEstimated', 0)
                    surprise = actual - estimated
                    result = "BEAT" if surprise > 0.01 else "MISS" if surprise < -0.01 else "MET"
                    parts.append(f"""
{e.get('date', 'N/A')}:
  Actual EPS: ${actual:.2f}
  Estimated EPS: ${estimated:.2f}
  Surprise: ${surprise:.2f} ({result})
""")

        # Key Ratios
        ratios = data.get("ratios") or []
        if ratios:
            r = ratios[0]
            parts.append(f"""
=== KEY FINANCIAL RATIOS ===
P/E Ratio: {r.get('priceEarningsRatio', 'N/A')}
P/B Ratio: {r.get('priceToBookRatio', 'N/A')}
P/S Ratio: {r.get('priceToSalesRatio', 'N/A')}
EV/EBITDA: {r.get('enterpriseValueMultiple', 'N/A')}
Debt/Equity: {r.get('debtEquityRatio', 'N/A')}
Current Ratio: {r.get('currentRatio', 'N/A')}
ROE: {r.get('returnOnEquity', 'N/A')}
ROA: {r.get('returnOnAssets', 'N/A')}
""")

        return "\n".join(parts)

    async def chat(self, symbol: str, question: str) -> Dict[str, Any]:
        """
        Answer a question about a company using RAG.

        1. Fetch all data (or use cache)
        2. Format as context
        3. Pass to Qwen with question
        4. Return answer
        """
        # Fetch all data
        data = await self.fetch_all_data(symbol)

        # Check if we got usable data
        if not data.get("profile"):
            return {
                "success": False,
                "answer": f"Could not fetch data for {symbol}. Please check the symbol.",
                "symbol": symbol,
            }

        # Format context
        context = self.format_data_context(data, symbol)

        # Build prompt
        prompt = f"""Based on the following financial data for {symbol}, answer this question:

QUESTION: {question}

{context}

Answer the question using ONLY the data provided above. If the information needed is not in the data, say so clearly."""

        try:
            # Call Qwen
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system=self.SYSTEM_PROMPT,
                temperature=0.1,  # Low temperature for factual accuracy
                max_tokens=1500,
            )

            return {
                "success": True,
                "answer": response,
                "symbol": symbol,
                "question": question,
            }

        except Exception as e:
            return {
                "success": False,
                "answer": f"Error generating response: {str(e)}",
                "symbol": symbol,
            }

    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cached data for a symbol or all symbols."""
        if symbol:
            self._data_cache.pop(symbol.upper(), None)
        else:
            self._data_cache.clear()


# Singleton instance
chat_agent = ChatAgent()
