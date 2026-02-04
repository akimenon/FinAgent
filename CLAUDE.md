# Claude Code Guidelines for FinAgent

## Quick Reference

### What is FinAgent?
AI-powered financial analysis platform combining:
- Real financial data from Financial Modeling Prep (FMP) API
- Multi-agent AI system powered by Ollama + Qwen 2.5 (14B local LLM)
- Intelligent caching to minimize API calls
- Interactive React frontend

### Key Files by Purpose

**Backend Agents** (`backend/agents/`)
| File | Purpose |
|------|---------|
| `orchestrator.py` | Master coordinator - synthesizes all agent outputs |
| `data_fetcher.py` | Fetches financial data from FMP API in parallel |
| `analysis_agent.py` | LLM analysis of quarterly results, trends, concerns |
| `guidance_tracker.py` | Beat/miss pattern analysis, accuracy scoring |
| `deep_insights_agent.py` | Industry-aware comprehensive analysis |
| `chat_agent.py` | RAG-based Q&A about company financials |

**Backend Routes** (`backend/routes/`)
| File | Key Endpoints |
|------|---------------|
| `financials.py` | `/api/financials/{symbol}/overview`, `/quarterly`, `/deep-insights`, `/analyst-ratings`, `/price-history` |
| `agent_query.py` | `/api/agent/query`, `/api/agent/chat`, `/api/agent/query/stream` |
| `companies.py` | `/api/companies/market-movers`, `/api/companies/sectors/{sector}` |
| `watchlist.py` | `/api/watchlist`, `/api/watchlist/{symbol}`, `/api/watchlist/{symbol}/status` |

**Backend Services** (`backend/services/`)
| File | Purpose |
|------|---------|
| `fmp_service.py` | Async FMP API client (~40 methods) |
| `fmp_cache.py` | File-based JSON caching with TTL |
| `llm_service.py` | Ollama/Qwen client |
| `insights_cache.py` | Caches LLM-generated insights |
| `watchlist_service.py` | File-based JSON watchlist storage |

**Frontend Pages** (`frontend/src/pages/`)
| File | Purpose |
|------|---------|
| `Dashboard.jsx` | Home page with search, market movers, sector lists |
| `CompanyAnalysis.jsx` | Main analysis page with charts, tables, AI insights |
| `Watchlist.jsx` | User watchlist with industry grouping, price tracking |

**Frontend Components** (`frontend/src/components/`)
| Path | Purpose |
|------|---------|
| `charts/PriceChart.jsx` | Area chart with time period selector |
| `charts/EarningsTrendChart.jsx` | Revenue/EPS trends |
| `charts/BeatMissChart.jsx` | Beat/miss visualization |
| `StockSearch.jsx` | Type-ahead stock search |
| `AgentQueryPanel.jsx` | Streaming AI analysis interface |

**Frontend Services** (`frontend/src/services/api.js`)
- `companiesApi` - Company search and profiles
- `financialsApi` - Financial data endpoints
- `agentApi` - AI query endpoints (including SSE streaming)
- `watchlistApi` - Watchlist management (add, remove, list)

---

## Multi-Agent Data Flow

```
User Request → API Route
    ↓
1. DataFetcherAgent
   - Parallel fetch from FMP API (with caching)
   - Calculate margins, YoY growth, fiscal quarters
    ↓
2. Parallel Agent Execution
   ├── AnalysisAgent (trends, metrics, concerns)
   ├── GuidanceTrackerAgent (beat/miss patterns)
   └── DeepInsightsAgent (industry-aware analysis)
    ↓
3. OrchestratorAgent
   - Synthesizes all outputs via Qwen
   - Returns markdown-formatted analysis
    ↓
Frontend Display
```

---

## Caching Strategy (TTL)

| Data Type | TTL | Examples |
|-----------|-----|----------|
| Daily | 1 day | Profiles, prices, earnings calendar, analyst grades |
| Quarterly | 90 days | Income statements, cash flow, ratios |
| Annual | 365 days | Product/geographic segments |
| Estimates | 30 days | Analyst estimates |
| News | 6 hours | Company news |

Cache location: `backend/data/fmp_cache/`

---

## Branch Naming Convention

**All branches MUST start with `feature/`**

```bash
# Correct
feature/update-readme
feature/add-new-endpoint
feature/fix-cache-bug

# Incorrect
docs/update-readme
fix/cache-bug
```

## Git Workflow

1. Always create branches from `main`
2. Branch name: `feature/<description>`
3. Push and create PR
4. CI must pass (backend tests + frontend build)
5. Requires 1 approval before merge
6. Admin (owner) can bypass if needed

## Testing

- Run tests before committing: `make test`
- Tests use fixture data from `backend/tests/fixtures/` (no API calls)
- Pre-commit hook runs tests automatically
- Coverage: `make test-cov` → `backend/htmlcov/`

## Common Commands

```bash
make start      # Start all services in background
make stop       # Stop services
make test       # Run backend tests
make test-cov   # Run tests with coverage
make backend    # Start backend only
make frontend   # Start frontend only
make setup-hooks # Install pre-commit hook
make clean      # Clean cache and artifacts
```

---

## Project Structure

```
backend/
├── agents/           # Multi-agent system (orchestrator, analysis, chat, etc.)
├── routes/           # API endpoints (financials, companies, agent_query)
├── services/         # FMP API client, caching, LLM service
├── models/           # SQLAlchemy ORM (Company, QuarterlyResult, EarningsSurprise)
├── schemas/          # Pydantic request/response schemas
├── tests/            # Pytest tests with fixtures
├── main.py           # FastAPI app entry
├── config.py         # Pydantic settings
└── database.py       # Async SQLAlchemy setup

frontend/
├── src/
│   ├── pages/        # Dashboard, CompanyAnalysis
│   ├── components/   # Charts, search, tables, agent panel
│   └── services/     # API client (api.js)
├── index.html
└── vite.config.js
```

---

## API Keys

- Never commit `.env` file
- Use `.env.example` as template
- Required: `FMP_API_KEY`, `ANTHROPIC_API_KEY` (or Ollama for local LLM)

## Number Formatting

**Always display large numbers in abbreviated format:**

- Billions: Use `B` suffix (e.g., `$57.0B` instead of `$57,006,000,000`)
- Millions: Use `M` suffix (e.g., `$125.5M` instead of `$125,500,000`)
- Thousands: Use `K` suffix for values >= 10K (e.g., `$50K` instead of `$50,000`)

Keep 1 decimal place for precision when needed (e.g., `$57.0B`, `$2.3M`).

**Implemented in:**
- Frontend: `formatNumber()` in `CompanyAnalysis.jsx`
- Backend: `_format_currency()` in `deep_insights_agent.py`
- LLM prompts enforce this formatting

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 18, Vite, TailwindCSS, Recharts |
| Backend | FastAPI, Python 3.9+, SQLAlchemy |
| LLM | Ollama + Qwen 2.5 (14B) |
| Financial Data | Financial Modeling Prep API |
| Database | SQLite + aiosqlite |
| HTTP Client | httpx (async), axios |
| Testing | Pytest |

---

## Common Tasks

### Add a new API endpoint
1. Create/edit route in `backend/routes/`
2. Add service method in `backend/services/fmp_service.py` if needed
3. Update cache TTL in `backend/services/fmp_cache.py` if needed
4. Add tests in `backend/tests/`

### Add a new agent
1. Create agent file in `backend/agents/`
2. Integrate with orchestrator if needed
3. Add route to expose functionality

### Add a new chart
1. Create component in `frontend/src/components/charts/`
2. Use Recharts library
3. Import and use in page component

### Add a new frontend page
1. Create page in `frontend/src/pages/`
2. Add route in `frontend/src/App.jsx`
3. Add API calls in `frontend/src/services/api.js`

---

## Database Models

**Company** - Main company record
- Fields: symbol, name, sector, industry, market_cap, exchange

**QuarterlyResult** - Financial metrics per quarter
- Revenue, gross_profit, operating_income, net_income, eps
- Calculated margins and YoY growth rates

**EarningsSurprise** - Beat/miss tracking
- Actual vs estimated EPS and revenue
- Verdict: BEAT, MISS, MEET

---

## LLM Integration Notes

- Local Ollama server at `http://localhost:11434`
- Model: `qwen2.5:14b`
- 5-minute timeout for complex synthesis
- Agents have fallback logic if LLM fails
- JSON structured output for parseable responses
- SSE support for streaming progress
