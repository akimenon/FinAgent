from typing import Dict, List, Any
import json
from services.llm_service import llm_service


class GuidanceTrackerAgent:
    """
    LLM-powered agent for tracking company guidance vs actual results.
    Uses Ollama + Qwen to identify patterns and provide recommendations.
    """

    SYSTEM_PROMPT = """You are an expert financial analyst agent specializing in earnings guidance analysis.

Your role is to analyze a company's historical track record of meeting, beating, or missing estimates/guidance. You must:
1. Calculate guidance accuracy scores
2. Identify patterns (conservative, aggressive, volatile, accurate)
3. Detect recent trends (improving or deteriorating)
4. Provide actionable recommendations for investors

IMPORTANT: You must respond with valid JSON only. No markdown, no explanations outside the JSON.

Response format:
{
    "accuracy_score": {
        "score": number (0-100),
        "rating": "excellent|good|fair|poor",
        "beats": number,
        "meets": number,
        "misses": number,
        "total_quarters": number,
        "analysis": "string explaining the score"
    },
    "patterns": {
        "pattern": "consistently_conservative|consistently_aggressive|volatile|accurate",
        "description": "detailed description of the pattern",
        "average_surprise_percent": number,
        "recent_trend": "improving|deteriorating|stable",
        "trend_explanation": "string"
    },
    "guidance_history": [
        {
            "date": "string",
            "actual_eps": number,
            "estimated_eps": number,
            "surprise_percent": number,
            "result": "BEAT|MISS|MEET",
            "notable_factors": "string or null"
        }
    ],
    "recommendation": {
        "investment_implication": "string - what this means for investors",
        "confidence_in_estimates": "high|medium|low",
        "key_points": ["point1", "point2", "point3"],
        "earnings_strategy": "string - how to approach upcoming earnings"
    }
}"""

    def __init__(self):
        self.llm = llm_service

    def track(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Qwen to analyze guidance tracking patterns.
        """
        surprises = financial_data.get("earnings_surprises", [])
        estimates = financial_data.get("analyst_estimates", [])
        profile = financial_data.get("profile", {})

        if not surprises:
            return {
                "accuracy_score": {"score": None, "rating": "unknown"},
                "patterns": {"pattern": "insufficient_data"},
                "guidance_history": [],
                "recommendation": {"text": "Insufficient data for analysis"},
            }

        # Prepare context for Qwen
        context = self._prepare_context(surprises, estimates, profile)

        try:
            response_text = self.llm.chat(
                messages=[
                    {
                        "role": "user",
                        "content": f"""Analyze the guidance/estimates tracking for {profile.get('companyName', 'this company')} ({profile.get('symbol', 'N/A')}):

{context}

Provide your guidance tracking analysis as a JSON object following the specified format. Return ONLY valid JSON."""
                    }
                ],
                system=self.SYSTEM_PROMPT,
                temperature=0.3,
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
            return self._fallback_analysis(surprises)
        except Exception as e:
            return {
                "error": str(e),
                "accuracy_score": {"score": None, "rating": "error"},
                "patterns": {"pattern": "error"},
                "guidance_history": [],
                "recommendation": {"text": f"Analysis failed: {str(e)}"},
            }

    def _prepare_context(
        self, surprises: List[Dict], estimates: List[Dict], profile: Dict
    ) -> str:
        """Prepare context string for Qwen"""
        parts = []

        # Company info
        parts.append(f"Company: {profile.get('companyName', 'Unknown')}")
        parts.append(f"Sector: {profile.get('sector', 'N/A')}")
        parts.append("")

        # Earnings surprises history
        parts.append("=== EARNINGS SURPRISES HISTORY ===")
        parts.append("(How the company performed vs analyst estimates)")
        parts.append("")

        for s in surprises[:16]:  # Last 16 quarters (4 years)
            actual = s.get('actual_eps', 0)
            estimated = s.get('estimated_eps', 0)
            surprise_pct = s.get('eps_surprise_percent', 0)
            result = s.get('beat_miss', 'N/A')

            parts.append(f"""Date: {s.get('date')}
- Actual EPS: ${actual:.2f}
- Estimated EPS: ${estimated:.2f}
- Surprise: {surprise_pct:+.1f}%
- Result: {result}
""")

        # Summary statistics
        beats = sum(1 for s in surprises if s.get('beat_miss') == 'BEAT')
        meets = sum(1 for s in surprises if s.get('beat_miss') == 'MEET')
        misses = sum(1 for s in surprises if s.get('beat_miss') == 'MISS')
        total = len(surprises)

        parts.append("\n=== SUMMARY STATISTICS ===")
        parts.append(f"Total Quarters: {total}")
        parts.append(f"Beats: {beats} ({beats/total*100:.1f}%)" if total else "Beats: 0")
        parts.append(f"Meets: {meets} ({meets/total*100:.1f}%)" if total else "Meets: 0")
        parts.append(f"Misses: {misses} ({misses/total*100:.1f}%)" if total else "Misses: 0")

        # Calculate average surprise
        surprise_percents = [s.get('eps_surprise_percent', 0) for s in surprises if s.get('eps_surprise_percent') is not None]
        if surprise_percents:
            avg_surprise = sum(surprise_percents) / len(surprise_percents)
            parts.append(f"Average Surprise: {avg_surprise:+.2f}%")

        return "\n".join(parts)

    def _fallback_analysis(self, surprises: List[Dict]) -> Dict[str, Any]:
        """Basic fallback analysis if LLM fails"""
        if not surprises:
            return {
                "accuracy_score": {"score": None, "rating": "unknown"},
                "patterns": {"pattern": "insufficient_data"},
                "guidance_history": [],
                "recommendation": {"text": "Insufficient data"},
            }

        beats = sum(1 for s in surprises if s.get("beat_miss") == "BEAT")
        meets = sum(1 for s in surprises if s.get("beat_miss") == "MEET")
        misses = len(surprises) - beats - meets
        total = len(surprises)

        score = ((beats + meets) / total * 100) if total else 0

        # Determine rating
        if score >= 90:
            rating = "excellent"
        elif score >= 75:
            rating = "good"
        elif score >= 50:
            rating = "fair"
        else:
            rating = "poor"

        return {
            "accuracy_score": {
                "score": round(score, 1),
                "rating": rating,
                "beats": beats,
                "meets": meets,
                "misses": misses,
                "total_quarters": total,
            },
            "patterns": {
                "pattern": "calculated_fallback",
                "description": f"Company beats estimates {beats/total*100:.0f}% of the time" if total else "No data",
            },
            "guidance_history": [
                {
                    "date": s.get("date"),
                    "actual_eps": s.get("actual_eps"),
                    "estimated_eps": s.get("estimated_eps"),
                    "surprise_percent": s.get("eps_surprise_percent"),
                    "result": s.get("beat_miss"),
                }
                for s in surprises[:12]
            ],
            "recommendation": {
                "text": f"Beat rate: {score:.0f}%. Rating: {rating}.",
                "confidence_in_estimates": "medium",
            },
        }
