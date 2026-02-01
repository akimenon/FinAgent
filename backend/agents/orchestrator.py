import asyncio
from typing import Dict, Any, AsyncGenerator
from datetime import datetime
import json

from config import settings
from services.llm_service import llm_service
from .data_fetcher import DataFetcherAgent
from .analysis_agent import AnalysisAgent
from .guidance_tracker import GuidanceTrackerAgent


class OrchestratorAgent:
    """
    Master orchestrator that coordinates all specialized LLM agents.
    Uses Ollama + Qwen as the "brain" to synthesize insights from all agents.
    """

    SYSTEM_PROMPT = """You are the lead financial analyst. Your job is to synthesize financial data into clear insights.

CRITICAL RULES:
1. ONLY use the EXACT numbers provided in the "ACTUAL QUARTERLY DATA" section
2. The FIRST quarter listed is the LATEST/MOST RECENT quarter - refer to it as "Latest Quarter"
3. NEVER make up or estimate numbers - only report what is explicitly provided
4. If data is missing, say "data not available" rather than guessing

Format your response with clear sections using markdown:
## Key Findings
(3-4 bullet points with specific numbers from the data)

## Financial Performance
(Use exact revenue, EPS, margin figures from ACTUAL QUARTERLY DATA)

## Beat/Miss Analysis
(Use data from ACTUAL EARNINGS SURPRISES)

## Concerns & Risks
(Based on trends and analyst insights)

## Investment Implications
(Actionable recommendations)"""

    def __init__(self):
        self.data_fetcher = DataFetcherAgent()
        self.analyzer = AnalysisAgent()
        self.guidance_tracker = GuidanceTrackerAgent()
        self.llm = llm_service

    async def process_query(self, symbol: str, query: str) -> Dict[str, Any]:
        """
        Process a user query by coordinating all agents.
        Each agent uses Qwen for its specialized analysis.
        """
        try:
            # Phase 1: Fetch all data (Data Fetcher Agent)
            financial_data = await self.data_fetcher.fetch_all(symbol)

            # Check for errors
            income_statements = financial_data.get("income_statements", [])
            if not income_statements or (income_statements and "error" in str(income_statements[0])):
                return {
                    "status": "error",
                    "message": f"Failed to fetch financial data for {symbol}. Please verify the symbol.",
                    "symbol": symbol,
                }

            # Phase 2: Run specialized agents in parallel (both use Qwen)
            analysis_task = asyncio.create_task(
                asyncio.to_thread(lambda: self.analyzer.analyze(financial_data))
            )
            guidance_task = asyncio.create_task(
                asyncio.to_thread(lambda: self.guidance_tracker.track(financial_data))
            )

            # Wait for both agents
            analysis_result = await analysis_task
            guidance_result = await guidance_task

            # Phase 3: Orchestrator synthesizes all agent outputs using Qwen
            synthesis = await self._synthesize_insights(
                symbol=symbol,
                query=query,
                financial_data=financial_data,
                analysis=analysis_result,
                guidance=guidance_result,
            )

            return {
                "status": "success",
                "symbol": symbol,
                "company": financial_data.get("profile", {}),
                "query": query,
                "synthesis": synthesis,
                "agent_outputs": {
                    "analysis_agent": analysis_result,
                    "guidance_agent": guidance_result,
                },
                "raw_data": {
                    "quarterly_results": financial_data.get("income_statements", []),
                    "earnings_surprises": financial_data.get("earnings_surprises", []),
                },
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol,
            }

    async def process_query_stream(
        self, symbol: str, query: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming version that shows agent progress in real-time.
        """
        yield {
            "phase": "starting",
            "agent": "orchestrator",
            "message": f"Initiating multi-agent analysis for {symbol}...",
        }

        # Check if Ollama is available
        if not self.llm.is_available():
            yield {
                "phase": "error",
                "agent": "orchestrator",
                "message": "Ollama is not running or model not found. Run: ollama serve && ollama pull qwen2.5:14b",
            }
            return

        # Phase 1: Data Fetcher Agent
        yield {
            "phase": "data_fetching",
            "agent": "data_fetcher",
            "message": "Data Fetcher Agent: Retrieving financial data from FMP...",
        }

        financial_data = await self.data_fetcher.fetch_all(symbol)

        income_statements = financial_data.get("income_statements", [])
        if not income_statements or "error" in str(income_statements[0] if income_statements else ""):
            error_msg = str(income_statements[0]) if income_statements else ""
            if "Premium" in error_msg or "subscription" in error_msg:
                yield {
                    "phase": "error",
                    "agent": "data_fetcher",
                    "message": f"{symbol} requires FMP premium subscription. Free tier only covers major stocks (AAPL, MSFT, GOOGL, etc.)",
                }
            else:
                yield {
                    "phase": "error",
                    "agent": "data_fetcher",
                    "message": f"Failed to fetch data for {symbol}. Symbol may not exist or API error occurred.",
                }
            return

        yield {
            "phase": "data_fetching",
            "agent": "data_fetcher",
            "message": f"Data Fetcher Agent: Retrieved {len(income_statements)} quarters of data",
            "preview": {
                "quarters_fetched": len(income_statements),
                "company": financial_data.get("profile", {}).get("companyName", symbol),
            },
        }

        # Phase 2: Analysis Agent (uses Qwen)
        yield {
            "phase": "analyzing",
            "agent": "analysis_agent",
            "message": "Analysis Agent: Running Qwen-powered financial analysis...",
        }

        analysis_result = await asyncio.to_thread(lambda: self.analyzer.analyze(financial_data))

        yield {
            "phase": "analyzing",
            "agent": "analysis_agent",
            "message": "Analysis Agent: Completed trend and metrics analysis",
            "preview": {
                "trends": analysis_result.get("trends", {}),
                "concerns_count": len(analysis_result.get("concerns", [])),
            },
        }

        # Phase 3: Guidance Tracker Agent (uses Qwen)
        yield {
            "phase": "tracking",
            "agent": "guidance_tracker",
            "message": "Guidance Tracker Agent: Analyzing beat/miss patterns with Qwen...",
        }

        guidance_result = await asyncio.to_thread(lambda: self.guidance_tracker.track(financial_data))

        yield {
            "phase": "tracking",
            "agent": "guidance_tracker",
            "message": "Guidance Tracker Agent: Completed guidance accuracy analysis",
            "preview": {
                "accuracy_score": guidance_result.get("accuracy_score", {}).get("score"),
                "pattern": guidance_result.get("patterns", {}).get("pattern"),
            },
        }

        # Phase 4: Orchestrator Synthesis (uses Qwen)
        yield {
            "phase": "synthesizing",
            "agent": "orchestrator",
            "message": "Orchestrator: Synthesizing all agent outputs with Qwen...",
        }

        synthesis = await self._synthesize_insights(
            symbol=symbol,
            query=query,
            financial_data=financial_data,
            analysis=analysis_result,
            guidance=guidance_result,
        )

        # Final result
        yield {
            "phase": "complete",
            "agent": "orchestrator",
            "message": "Multi-agent analysis complete",
            "result": {
                "status": "success",
                "symbol": symbol,
                "company": financial_data.get("profile", {}),
                "synthesis": synthesis,
                "agent_outputs": {
                    "analysis_agent": analysis_result,
                    "guidance_agent": guidance_result,
                },
                "raw_data": {
                    "quarterly_results": financial_data.get("income_statements", []),
                    "earnings_surprises": financial_data.get("earnings_surprises", []),
                },
            },
        }

    async def _synthesize_insights(
        self,
        symbol: str,
        query: str,
        financial_data: Dict,
        analysis: Dict,
        guidance: Dict,
    ) -> str:
        """
        Use Qwen to synthesize all agent outputs into a coherent response.
        """
        profile = financial_data.get("profile", {})

        # Get actual raw data to include
        income_statements = financial_data.get('income_statements', [])
        earnings_surprises = financial_data.get('earnings_surprises', [])

        # Format raw quarterly data
        raw_quarters = ""
        for i, q in enumerate(income_statements[:5]):
            marker = " (LATEST)" if i == 0 else ""
            raw_quarters += f"""
{q.get('fiscal_quarter', 'Q?')} {q.get('fiscal_year', '')}{marker}:
  - Revenue: ${q.get('revenue', 0):,.0f}
  - Net Income: ${q.get('net_income', 0):,.0f}
  - EPS: ${q.get('eps', 0):.2f}
  - Gross Margin: {q.get('gross_margin', 0):.1f}%
  - Operating Margin: {q.get('operating_margin', 0):.1f}%
  - Net Margin: {q.get('net_margin', 0):.1f}%
"""

        # Format earnings surprises
        raw_surprises = ""
        for s in earnings_surprises[:5]:
            raw_surprises += f"""
{s.get('date', 'N/A')}: Actual ${s.get('actual_eps', 0):.2f} vs Est ${s.get('estimated_eps', 0):.2f} = {s.get('beat_miss', 'N/A')}
"""

        # Prepare comprehensive context from all agents
        context = f"""
=== USER QUESTION ===
{query}

=== COMPANY INFO ===
Company: {profile.get('companyName', symbol)} ({symbol})
Sector: {profile.get('sector', 'N/A')}
Industry: {profile.get('industry', 'N/A')}
Market Cap: ${profile.get('mktCap', 0):,.0f}

=== ACTUAL QUARTERLY DATA (USE THESE EXACT NUMBERS) ===
{raw_quarters}

=== ACTUAL EARNINGS SURPRISES ===
{raw_surprises}

=== ANALYSIS AGENT INSIGHTS ===
Trends: {json.dumps(analysis.get('trends', {}), default=str)}
Concerns: {json.dumps(analysis.get('concerns', []), default=str)}
Beat Rate: {analysis.get('beat_rate', {}).get('beat_rate', 'N/A')}%

=== GUIDANCE TRACKER INSIGHTS ===
Accuracy Score: {guidance.get('accuracy_score', {}).get('score', 'N/A')}
Pattern: {guidance.get('patterns', {}).get('pattern', 'N/A')}
"""

        try:
            response = await asyncio.to_thread(
                lambda: self.llm.chat(
                    messages=[
                        {
                            "role": "user",
                            "content": f"""Based on the analysis from our specialized agents, provide a comprehensive response to the user's question about {symbol}.

{context}

Synthesize all the information and provide actionable insights."""
                        }
                    ],
                    system=self.SYSTEM_PROMPT,
                    temperature=0.7,
                    max_tokens=2000,
                )
            )
            return response

        except Exception as e:
            return f"Error synthesizing insights: {str(e)}\n\nFallback summary: {analysis.get('summary', 'No summary available')}"
