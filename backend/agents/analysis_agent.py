from typing import Dict, List, Any
import json
from services.llm_service import llm_service


class AnalysisAgent:
    """
    LLM-powered agent for financial analysis.
    Uses Ollama + Qwen to analyze quarterly results, identify trends, and flag concerns.
    """

    SYSTEM_PROMPT = """You are an expert financial analyst agent specializing in quarterly earnings analysis.

Your role is to analyze financial data and provide structured insights. You must:
1. Calculate and interpret key metrics (margins, growth rates)
2. Identify trends across quarters (improving, declining, stable)
3. Flag concerning metrics that investors should watch
4. Compare performance to historical averages
5. Provide actionable insights

IMPORTANT: You must respond with valid JSON only. No markdown, no explanations outside the JSON.

Response format:
{
    "metrics": {
        "latest_quarter": {
            "revenue": number,
            "eps": number,
            "gross_margin": number,
            "operating_margin": number,
            "net_margin": number,
            "revenue_growth_yoy": number or null,
            "eps_growth_yoy": number or null
        },
        "averages": {
            "avg_revenue": number,
            "avg_eps": number,
            "avg_gross_margin": number,
            "avg_net_margin": number
        }
    },
    "trends": {
        "revenue": {"direction": "increasing|decreasing|stable", "strength": "strong|moderate|weak", "analysis": "string"},
        "eps": {"direction": "increasing|decreasing|stable", "strength": "strong|moderate|weak", "analysis": "string"},
        "margins": {"direction": "expanding|contracting|stable", "analysis": "string"}
    },
    "concerns": [
        {"type": "string", "severity": "high|medium|low", "message": "string", "recommendation": "string"}
    ],
    "beat_rate": {
        "beat_rate": number,
        "beats": number,
        "misses": number,
        "total_quarters": number,
        "analysis": "string"
    },
    "summary": "2-3 sentence executive summary"
}"""

    def __init__(self):
        self.llm = llm_service

    def analyze(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Qwen to analyze financial data and return structured insights.
        """
        income_data = financial_data.get("income_statements", [])
        surprises_data = financial_data.get("earnings_surprises", [])
        profile = financial_data.get("profile", {})

        # Prepare the context for Qwen
        context = self._prepare_context(income_data, surprises_data, profile)

        try:
            response_text = self.llm.chat(
                messages=[
                    {
                        "role": "user",
                        "content": f"""Analyze the following financial data for {profile.get('companyName', 'this company')} ({profile.get('symbol', 'N/A')}):

{context}

Provide your analysis as a JSON object following the specified format. Return ONLY valid JSON."""
                    }
                ],
                system=self.SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for more consistent JSON
                max_tokens=2000,
            )

            # Clean up potential markdown formatting
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            # Try to find JSON in the response
            if "{" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                response_text = response_text[start:end]

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            # Fallback to basic analysis if JSON parsing fails
            return self._fallback_analysis(income_data, surprises_data)
        except Exception as e:
            return {
                "error": str(e),
                "metrics": {},
                "trends": {},
                "concerns": [],
                "beat_rate": {},
                "summary": "Analysis failed due to an error."
            }

    def _prepare_context(
        self, income_data: List[Dict], surprises_data: List[Dict], profile: Dict
    ) -> str:
        """Prepare context string for Qwen"""
        parts = []

        # Company info
        parts.append(f"Company: {profile.get('companyName', 'Unknown')}")
        parts.append(f"Sector: {profile.get('sector', 'N/A')}")
        parts.append(f"Industry: {profile.get('industry', 'N/A')}")
        parts.append("")

        # Quarterly results
        parts.append("=== QUARTERLY INCOME STATEMENTS ===")
        for q in income_data[:8]:
            parts.append(f"""
Quarter: {q.get('fiscal_year')} {q.get('fiscal_quarter')}
- Revenue: ${q.get('revenue', 0):,.0f}
- Gross Profit: ${q.get('gross_profit', 0):,.0f}
- Operating Income: ${q.get('operating_income', 0):,.0f}
- Net Income: ${q.get('net_income', 0):,.0f}
- EPS: ${q.get('eps', 0):.2f}
- Gross Margin: {q.get('gross_margin', 0):.1f}%
- Operating Margin: {q.get('operating_margin', 0):.1f}%
- Net Margin: {q.get('net_margin', 0):.1f}%
- Revenue Growth YoY: {q.get('revenue_growth_yoy', 'N/A')}%
- EPS Growth YoY: {q.get('eps_growth_yoy', 'N/A')}%
""")

        # Earnings surprises
        if surprises_data:
            parts.append("\n=== EARNINGS SURPRISES (BEAT/MISS HISTORY) ===")
            for s in surprises_data[:12]:
                parts.append(f"""
Date: {s.get('date')}
- Actual EPS: ${s.get('actual_eps', 0):.2f}
- Estimated EPS: ${s.get('estimated_eps', 0):.2f}
- Surprise: {s.get('eps_surprise_percent', 0):.1f}%
- Result: {s.get('beat_miss', 'N/A')}
""")

        return "\n".join(parts)

    def _fallback_analysis(
        self, income_data: List[Dict], surprises_data: List[Dict]
    ) -> Dict[str, Any]:
        """Basic fallback analysis if LLM fails"""
        import statistics

        if not income_data:
            return {"error": "No data available", "summary": "Insufficient data for analysis"}

        latest = income_data[0]

        # Calculate beat rate
        if surprises_data:
            beats = sum(1 for s in surprises_data if s.get("beat_miss") == "BEAT")
            total = len(surprises_data)
            beat_rate = (beats / total * 100) if total else 0
        else:
            beats, total, beat_rate = 0, 0, 0

        return {
            "metrics": {
                "latest_quarter": {
                    "revenue": latest.get("revenue"),
                    "eps": latest.get("eps"),
                    "gross_margin": latest.get("gross_margin"),
                    "operating_margin": latest.get("operating_margin"),
                    "net_margin": latest.get("net_margin"),
                    "revenue_growth_yoy": latest.get("revenue_growth_yoy"),
                    "eps_growth_yoy": latest.get("eps_growth_yoy"),
                }
            },
            "trends": {"revenue": {"direction": "unknown"}, "eps": {"direction": "unknown"}},
            "concerns": [],
            "beat_rate": {"beat_rate": beat_rate, "beats": beats, "total_quarters": total},
            "summary": f"Latest quarter: Revenue ${latest.get('revenue', 0):,.0f}, EPS ${latest.get('eps', 0):.2f}. Beat rate: {beat_rate:.0f}%.",
        }
