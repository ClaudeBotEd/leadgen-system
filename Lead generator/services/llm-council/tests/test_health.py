"""Health endpoint contracts."""

from __future__ import annotations


def test_health_returns_ok_when_configured(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "llm-council"
    assert body["status"] in {"ok", "degraded"}
    assert body["chairman_model"]
    assert isinstance(body["council_models"], list)


def test_liveness_always_alive(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_readiness_reports_configured(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] is True
    assert body["status"] == "ready"
