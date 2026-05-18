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


def test_analyze_lead_endpoint(client, mock_openrouter):
    r = client.post(
        "/api/council/analyze-lead",
        json={
            "lead": {
                "name": "Jane Cooper",
                "company": "Acme Solar BV",
                "title": "CFO",
                "location": "Amsterdam",
            },
            "objective": "qualify for a discovery call",
            "locale": "en",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stage3"]["response"]


def test_generate_outreach_endpoint(client, mock_openrouter):
    r = client.post(
        "/api/council/generate-outreach",
        json={
            "lead": {"company": "Acme Solar", "title": "CFO"},
            "channel": "email",
            "locale": "en",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stage3"]["response"]


def test_review_scrape_endpoint(client, mock_openrouter):
    r = client.post(
        "/api/council/review-scrape",
        json={
            "source_name": "test-scrape",
            "criteria": "B2B solar installers in NL",
            "sample": [
                {"name": "A", "company": "Acme", "email": "a@example.com"},
                {"name": "B", "company": "Beta", "email": "b@example.com"},
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stage3"]["response"]


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
