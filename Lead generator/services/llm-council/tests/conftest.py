"""Pytest fixtures: in-memory DB + mocked OpenRouter."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_COUNCIL_ENV", "test")
os.environ.setdefault("LLM_COUNCIL_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("LLM_COUNCIL_RATE_LIMIT_PER_MINUTE", "1000")

# Import AFTER the env is in place so pydantic-settings picks them up.
from backend.config import get_settings  # noqa: E402
from backend.main import create_app  # noqa: E402

get_settings.cache_clear()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_openrouter(monkeypatch):
    """Stub query_model + query_models_parallel so tests never hit the network."""

    async def fake_query_model(model, messages, **kwargs):  # noqa: ARG001
        last_user = messages[-1]["content"] if messages else ""
        if "Title:" in last_user:
            return {"content": "Test Title", "reasoning_details": None}
        if "FINAL RANKING" in last_user.upper() or "rank" in last_user.lower():
            return {
                "content": (
                    "Response A is great. Response B is OK.\n\n"
                    "FINAL RANKING:\n1. Response A\n2. Response B\n"
                ),
                "reasoning_details": None,
            }
        return {
            "content": f"[mock {model}] {last_user[:80]}",
            "reasoning_details": None,
        }

    async def fake_query_models_parallel(models, messages, **kwargs):
        return {m: await fake_query_model(m, messages, **kwargs) for m in models}

    monkeypatch.setattr(
        "backend.services.openrouter.query_model", fake_query_model
    )
    monkeypatch.setattr(
        "backend.services.openrouter.query_models_parallel", fake_query_models_parallel
    )
    monkeypatch.setattr(
        "backend.services.council.query_model", fake_query_model
    )
    monkeypatch.setattr(
        "backend.services.council.query_models_parallel", fake_query_models_parallel
    )
    return fake_query_model
