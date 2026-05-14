"""Tests voor Reddit author-enrichment."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from consumer.sources.reddit_author import (
    AuthorProfile,
    RENOVATION_SUBS,
    _parse_user_payload,
    enrich_author,
)


def _synthetic_payload(*children: dict) -> dict:
    return {"data": {"children": list(children)}}


def _child(*, kind: str = "t3", subreddit: str = "thenetherlands",
           score: int = 1, created_ago_s: float = 86400) -> dict:
    return {
        "kind": kind,
        "data": {
            "subreddit": subreddit,
            "score": score,
            "created_utc": time.time() - created_ago_s,
        },
    }


def test_unavailable_for_missing_author() -> None:
    p = enrich_author(None)
    assert p.available is False
    assert p.error == "missing_or_deleted"


def test_unavailable_for_deleted_author() -> None:
    p = enrich_author("[deleted]")
    assert p.available is False


def test_parse_counts_submissions_and_comments() -> None:
    payload = _synthetic_payload(
        _child(kind="t3", subreddit="thenetherlands"),
        _child(kind="t3", subreddit="bouwen"),
        _child(kind="t1", subreddit="warmtepompen", score=5),
        _child(kind="t1", subreddit="random", score=2),
    )
    p = _parse_user_payload("alice", payload)
    assert p.submission_count == 2
    assert p.comment_count == 2
    assert p.total_score == 9


def test_parse_identifies_renovation_subs() -> None:
    payload = _synthetic_payload(
        _child(subreddit="warmtepompen"),
        _child(subreddit="bouwen"),
        _child(subreddit="random"),
    )
    p = _parse_user_payload("alice", payload)
    assert "warmtepompen" in p.renovation_subs_hit
    assert "bouwen" in p.renovation_subs_hit
    assert "random" not in p.renovation_subs_hit


def test_recurring_asker_flagged() -> None:
    payload = _synthetic_payload(
        *[_child(subreddit="warmtepompen") for _ in range(6)],
    )
    p = _parse_user_payload("alice", payload)
    assert p.is_recurring_asker is True
    assert p.signal_penalty == -20


def test_not_recurring_when_low_activity() -> None:
    payload = _synthetic_payload(
        _child(subreddit="warmtepompen"),
        _child(subreddit="random"),
    )
    p = _parse_user_payload("alice", payload)
    assert p.is_recurring_asker is False
    assert p.signal_penalty == 0


def test_not_recurring_when_no_renovation_subs() -> None:
    payload = _synthetic_payload(
        *[_child(subreddit="random") for _ in range(6)],
    )
    p = _parse_user_payload("alice", payload)
    assert p.is_recurring_asker is False


def test_account_age_estimated_from_earliest_child() -> None:
    """Fallback-pad: geen about.json data, gebruik oudste zichtbare post."""
    payload = _synthetic_payload(
        _child(created_ago_s=86400 * 30),
        _child(created_ago_s=86400 * 60),
    )
    p = _parse_user_payload("alice", payload)
    assert p.account_age_days is not None
    assert 58 <= p.account_age_days <= 62


def test_account_age_uses_about_created_utc_when_present() -> None:
    """Met about.json data: echte account-leeftijd, niet schatting uit posts.

    Bug 723: oude code schatte account_age uit earliest visible post — een
    5-jaar oud account dat 1 maand actief is werd 30 dagen oud genoemd,
    wat user-classificatie scheef trok."""
    payload = _synthetic_payload(
        _child(created_ago_s=86400 * 10),  # laatste activiteit 10 dagen oud
    )
    payload["_about_created_utc"] = time.time() - (86400 * 365 * 5)
    p = _parse_user_payload("alice", payload)
    assert p.account_age_days is not None
    assert 1820 <= p.account_age_days <= 1830  # ~5 jaar = 1825d


def test_account_age_invalid_about_falls_back_to_earliest_child() -> None:
    """Ongeldige _about_created_utc → defensieve fallback naar earliest child."""
    payload = _synthetic_payload(_child(created_ago_s=86400 * 30))
    payload["_about_created_utc"] = "not-a-number"
    p = _parse_user_payload("alice", payload)
    assert p.account_age_days is not None
    assert 28 <= p.account_age_days <= 32


def test_enrich_with_fetch_fn(tmp_path: Path) -> None:
    payload = _synthetic_payload(
        *[_child(subreddit="warmtepompen") for _ in range(5)],
    )
    captured: dict = {}

    def fake_fetch(author: str, timeout_s: int) -> dict:
        captured["author"] = author
        return payload

    p = enrich_author("alice", cache_dir=tmp_path, fetch_fn=fake_fetch)
    assert p.available is True
    assert p.is_recurring_asker is True
    assert captured["author"] == "alice"


def test_enrich_uses_cache_on_second_call(tmp_path: Path) -> None:
    payload = _synthetic_payload(_child(subreddit="bouwen"))
    call_count = {"n": 0}

    def fake_fetch(author: str, timeout_s: int) -> dict:
        call_count["n"] += 1
        return payload

    p1 = enrich_author("bob", cache_dir=tmp_path, fetch_fn=fake_fetch)
    p2 = enrich_author("bob", cache_dir=tmp_path, fetch_fn=fake_fetch)
    assert p1.author == p2.author
    assert call_count["n"] == 1


def test_enrich_fetch_returns_none_handled(tmp_path: Path) -> None:
    p = enrich_author("alice", cache_dir=tmp_path, fetch_fn=lambda a, t: None)
    assert p.available is False
    assert p.error == "fetch_failed_or_404"


def test_renovation_subs_lowercase() -> None:
    for sub in RENOVATION_SUBS:
        assert sub == sub.lower()


def test_profile_signal_penalty_only_when_recurring() -> None:
    p = AuthorProfile(author="x", available=True, is_recurring_asker=False)
    assert p.signal_penalty == 0
    p.is_recurring_asker = True
    assert p.signal_penalty == -20


def test_fetch_url_encodes_author_with_special_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Author-namen moeten URL-safe geëncodeerd worden, anders kan een
    malicious naam als 'alice/../admin' of een naam met query-chars de URL-
    structuur breken (SSRF / path-injection)."""
    from consumer.sources import reddit_author as ra

    captured: list[str] = []

    class FakeResp:
        status_code = 404
        def json(self):  # noqa: D401, ANN201
            return {}

    def fake_get(url, **kwargs):  # noqa: ANN001, ANN201
        captured.append(url)
        return FakeResp()

    monkeypatch.setattr(ra.requests, "get", fake_get)
    result = ra._fetch_reddit_user("alice/../admin", timeout_s=5)
    assert result is None  # 404 path
    assert captured, "expected at least one GET request"
    # /'s in author moeten als %2F geëncodeerd zijn — anders zou Reddit
    # de '..' segmenten als path-traversal kunnen interpreteren.
    assert "alice%2F..%2Fadmin" in captured[0], (
        f"author not URL-encoded; got {captured[0]!r}"
    )
    assert "/user/alice/../admin/" not in captured[0]
