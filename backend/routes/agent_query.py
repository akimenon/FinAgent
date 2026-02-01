from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json

from agents.orchestrator import OrchestratorAgent
from agents.chat_agent import chat_agent

router = APIRouter(prefix="/api/agent", tags=["agent"])

orchestrator = OrchestratorAgent()


class AgentQueryRequest(BaseModel):
    symbol: str
    query: str


@router.post("/query")
async def query_agent(request: AgentQueryRequest):
    """
    Send a natural language query to the agent system.
    Returns comprehensive analysis with AI-generated insights.
    """
    if not request.symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    if not request.query:
        # Default query if none provided
        request.query = "Provide a comprehensive analysis of this stock"

    try:
        result = await orchestrator.process_query(
            symbol=request.symbol.upper(),
            query=request.query,
        )

        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/stream")
async def query_agent_stream(symbol: str, query: Optional[str] = None):
    """
    Streaming version of agent query.
    Returns Server-Sent Events with progress updates.
    """
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    query = query or "Provide a comprehensive analysis of this stock"

    async def event_generator():
        try:
            async for update in orchestrator.process_query_stream(
                symbol=symbol.upper(),
                query=query,
            ):
                yield f"data: {json.dumps(update)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'phase': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/analyze")
async def analyze_stock(request: AgentQueryRequest):
    """
    Quick analysis endpoint - returns structured data without AI narrative.
    """
    from agents.data_fetcher import DataFetcherAgent
    from agents.analysis_agent import AnalysisAgent
    from agents.guidance_tracker import GuidanceTrackerAgent

    data_fetcher = DataFetcherAgent()
    analyzer = AnalysisAgent()
    tracker = GuidanceTrackerAgent()

    try:
        # Fetch data
        financial_data = await data_fetcher.fetch_all(request.symbol.upper())

        # Run analysis
        analysis = analyzer.analyze(financial_data)
        guidance = tracker.track(financial_data)

        return {
            "symbol": request.symbol.upper(),
            "company": financial_data.get("profile", {}),
            "quarterly_results": financial_data.get("income_statements", []),
            "earnings_surprises": financial_data.get("earnings_surprises", []),
            "analysis": analysis,
            "guidance": guidance,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    symbol: str
    question: str


@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """
    RAG-based chat endpoint.
    Fetches comprehensive financial data and answers any question.

    Examples:
    - "What was iPhone revenue in FY2025?"
    - "How much cash does Apple have?"
    - "What's the revenue from China?"
    - "Did they beat earnings last quarter?"
    """
    if not request.symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    if not request.question:
        raise HTTPException(status_code=400, detail="Question is required")

    try:
        result = await chat_agent.chat(
            symbol=request.symbol.upper(),
            question=request.question,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("answer"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/cache/{symbol}")
async def clear_chat_cache(symbol: str):
    """Clear cached data for a symbol to force refresh."""
    chat_agent.clear_cache(symbol)
    return {"message": f"Cache cleared for {symbol}"}
