.PHONY: help setup backend frontend test lint run clean

help:
	@echo "AI Learning Copilot - Makefile"
	@echo ""
	@echo "setup       Install all dependencies"
	@echo "backend     Run the FastAPI backend"
	@echo "frontend    Run the Next.js frontend"
	@echo "test        Run backend tests"
	@echo "db-init     Initialize the database"
	@echo "clean       Clean temporary files"

setup:
	cd backend && pip install -r requirements.txt && playwright install chromium
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && python -m pytest tests/ -v

db-init:
	cd backend && python -c "from app.database import engine, Base; from app.db.base import *; Base.metadata.create_all(bind=engine); print('Database initialized')"

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	rm -f backend/*.db
