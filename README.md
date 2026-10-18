# AI Learning Copilot

A local-first AI assistant that helps students learn from online course platforms without completing graded work on the student's behalf.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────┐
│  Next.js UI │────▶│  FastAPI API │────▶│  Ollama   │
│  (TS/React) │     │  (Python)    │     │  (LLM)    │
└─────────────┘     └──────┬───────┘     └───────────┘
                           │
                    ┌──────┴───────┐
                    │  Playwright  │
                    │  (Browser)   │
                    └──────────────┘
                           │
                    ┌──────┴───────┐
                    │   SQLite/DB  │
                    └──────────────┘
```

## Features

- **Browser Automation**: Navigate courses, detect lesson completion, extract content
- **Lecture Intelligence**: Generate summaries, notes, key concepts, flashcards, revision questions
- **Coding Assistant**: Explain problems, generate hints, review solutions, analyze complexity
- **MCQ Explainer**: Extract questions, explain options, provide reasoning
- **Knowledge Base**: Local SQLite storage for all learning data
- **Dashboard**: Track progress, study time, weak areas, revision schedule
- **Local AI**: Ollama integration (supports Qwen, Gemma, DeepSeek)

## Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- Ollama (running locally)

### Quick Start

```bash
# 1. Install dependencies
make setup

# 2. Initialize the database
make db-init

# 3. Start the backend (terminal 1)
make backend

# 4. Start the frontend (terminal 2)
make frontend

# 5. Open http://localhost:3000
```

### Environment Variables

Copy and edit the example files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Key settings in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./alc.db` | Database connection string |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Default LLM model |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Docker

```bash
make docker-build
make docker-up
```

## API Documentation

When the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/automation/start` | Start browser |
| POST | `/api/automation/navigate` | Navigate to URL |
| GET | `/api/automation/content` | Extract lesson content |
| GET | `/api/automation/detect-completion` | Check lesson completion |
| POST | `/api/automation/next-lesson` | Open next lesson |
| GET/POST | `/api/courses/` | Course CRUD |
| GET/POST | `/api/lessons/` | Lesson CRUD |
| POST | `/api/notes/generate` | Generate notes from lesson |
| GET | `/api/flashcards/` | List flashcards |
| POST | `/api/flashcards/{id}/review` | Review flashcard |
| POST | `/api/coding/explain` | Explain coding problem |
| POST | `/api/coding/problems/{id}/review` | Review solution |
| POST | `/api/mcq/extract` | Extract MCQ from page text |
| POST | `/api/mcq/explain` | Explain MCQ options |
| GET | `/api/analytics/dashboard` | Dashboard statistics |

## Folder Structure

```
alc/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # API endpoints
│   │   ├── core/              # Logging, exceptions
│   │   ├── db/                # Database session
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/          # Business logic
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js pages
│   │   ├── components/        # React components
│   │   ├── lib/               # API client, types
│   │   └── styles/
│   └── package.json
├── docker-compose.yml
├── Makefile
└── README.md
```

## Testing

```bash
make test
```

## License

MIT
