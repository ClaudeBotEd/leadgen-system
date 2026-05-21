SHELL := /bin/bash

.PHONY: help install install-backend install-frontend dev backend frontend lint fmt test smoke clean docker-build docker-up docker-down

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: install-backend install-frontend ## Install all dependencies.

install-backend: ## uv sync + dev extras.
	uv sync --extra dev

install-frontend: ## npm install in frontend/.
	cd frontend && npm install

dev: ## Start backend (8001) + frontend (5173) together.
	@./scripts/dev.sh

backend: ## Start only the backend (with auto-reload).
	uv run uvicorn backend.main:app --host 0.0.0.0 --port $${LLM_COUNCIL_PORT:-8001} --reload

frontend: ## Start only the frontend.
	cd frontend && npm run dev

lint: ## Ruff lint check.
	uv run ruff check backend tests

fmt: ## Ruff format.
	uv run ruff format backend tests

test: ## Run pytest with the in-memory SQLite test config.
	LLM_COUNCIL_ENV=test LLM_COUNCIL_DATABASE_URL=sqlite+aiosqlite:///:memory: uv run pytest -q

smoke: ## Hit /health on the running backend.
	@curl -fsS http://127.0.0.1:$${LLM_COUNCIL_PORT:-8001}/health | python3 -m json.tool

clean: ## Remove caches and the local SQLite db.
	rm -rf .ruff_cache .pytest_cache data/llm_council.db
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

docker-build: ## Build all docker images.
	docker compose build

docker-up: ## Start the full stack with docker compose.
	docker compose up -d

docker-down: ## Stop the docker stack.
	docker compose down
