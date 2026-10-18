# AI Learning Copilot - Development Notes

## Commands

- Backend tests: `make test` (or `cd backend && python -m pytest tests/ -v`)
- Backend dev server: `make backend` (or `cd backend && uvicorn app.main:app --reload --port 8000`)
- Frontend dev server: `make frontend` (or `cd frontend && npm run dev`)
- DB init: `make db-init`
- Install deps: `make setup`

## Architecture Decisions

- **SQLite** default, easy switch to PostgreSQL via `DATABASE_URL` env var
- **Ollama** as default LLM, model configurable via env
- **Playwright** for browser automation, non-headless for manual login
- **Modular services** pattern: browser.py -> course_navigator.py -> services use llm_client.py
- **API routes** are thin, logic lives in services

## Key Patterns

- All external calls (LLM, browser) are async
- Services have fallback implementations when LLM is unavailable
- Database session management via FastAPI dependency injection
- Frontend uses Next.js App Router with client components
