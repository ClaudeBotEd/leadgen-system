"""End-to-end API smoke tests (mocked OpenRouter)."""

from __future__ import annotations


def test_conversation_lifecycle(client, mock_openrouter):
    # create
    r = client.post("/api/conversations", json={})
    assert r.status_code == 201
    conv = r.json()
    cid = conv["id"]
    assert conv["title"] == "New Conversation"

    # list
    r = client.get("/api/conversations")
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()]
    assert cid in ids

    # send message - runs full council with mocked LLMs
    r = client.post(
        f"/api/conversations/{cid}/message",
        json={"content": "What is the ICP for solar installers?"},
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["stage1"]
    assert payload["stage3"]["response"]
    assert "metadata" in payload

    # get
    r = client.get(f"/api/conversations/{cid}")
    assert r.status_code == 200
    full = r.json()
    assert len(full["messages"]) == 2  # user + assistant
    assert full["messages"][1]["role"] == "assistant"

    # delete
    r = client.delete(f"/api/conversations/{cid}")
    assert r.status_code == 204
    r = client.get(f"/api/conversations/{cid}")
    assert r.status_code == 404


def test_council_query_endpoint(client, mock_openrouter):
    r = client.post(
        "/api/council/query",
        json={"query": "Compare these three lead-gen tools.", "persist": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["conversation_id"] is None
    result = body["result"]
    assert result["stage1"]
    assert result["stage3"]["response"]


def test_review_scrape_endpoint(client, mock_openrouter):
    r = client.post(
        "/api/council/review-scrape",
        json={
            "source_name": "gathering-of-tweakers-warmtepomp",
            "criteria": "credible upstream of homeowner-intent posts",
            "sample": [
                {
                    "source_url": "https://example.test/t/1",
                    "snippet": "We willen een warmtepomp laten installeren in Utrecht.",
                    "captured_at": "2026-05-18T10:00:00Z",
                },
                {
                    "source_url": "https://example.test/t/2",
                    "snippet": "Offerte aangevraagd voor warmtepomp, advies welkom.",
                    "captured_at": "2026-05-18T10:01:00Z",
                },
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stage3"]["response"]


def test_deprecated_b2b_endpoints_return_404(client):
    """The B2B SaaS endpoints were removed in the trust-provenance refactor.
    Any caller still hitting them must see a clean 404, not a stack trace."""
    for path in (
        "/api/council/analyze-lead",
        "/api/council/generate-outreach",
        "/api/council/score-lead",
        "/api/council/generate-sequence",
    ):
        r = client.post(path, json={})
        assert r.status_code == 404, f"{path} should be removed"


def test_validation_error_shape(client):
    r = client.post("/api/council/query", json={"query": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"


def test_404_uses_central_error_envelope(client):
    r = client.get("/api/conversations/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "conversation_not_found"
