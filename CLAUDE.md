# Claude Code Guidelines for FinAgent

## Branch Naming Convention

**All branches MUST start with `feature/`**

```bash
# Correct
feature/update-readme
feature/add-new-endpoint
feature/fix-cache-bug
feature/v1.2-new-features

# Incorrect
docs/update-readme
fix/cache-bug
update-readme
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

## Project Structure

```
backend/           # FastAPI + Python agents
├── agents/        # Multi-agent system
├── routes/        # API endpoints
├── services/      # FMP API + caching
└── tests/         # Pytest tests

frontend/          # React + Vite + TailwindCSS
├── src/pages/     # Main pages
├── src/components # Reusable components
└── src/services/  # API client
```

## API Keys

- Never commit `.env` file
- Use `.env.example` as template
- Required: `FMP_API_KEY`, `ANTHROPIC_API_KEY` (or Ollama for local LLM)
