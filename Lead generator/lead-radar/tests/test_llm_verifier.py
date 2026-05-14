"""Regression-tests voor llm_verifier — pure-function delen + skipped paths."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from consumer.processor.llm_verifier import (
    DEFAULT_MAX_SCORE,
    DEFAULT_MIN_SCORE,
    LlmVerdict,
    _build_user_prompt,
    _parse_response,
    _post_hash,
    combine_score,
    should_verify,
    verify_post,
)


@pytest.mark.parametrize("score,expected", [
    (0, False), (39, False),
    (40, True), (50, True), (75, True),
    (76, False), (100, False),
])
def test_should_verify_brackets(score: int, expected: bool) -> None:
    assert should_verify(score) is expected


def test_should_verify_custom_range() -> None:
    assert should_verify(50, min_score=30, max_score=60) is True
    assert should_verify(70, min_score=30, max_score=60) is False


def test_post_hash_stable() -> None:
    h1 = _post_hash("hello world", "claude-haiku-4-5")
    h2 = _post_hash("hello world", "claude-haiku-4-5")
    h3 = _post_hash("hello world", "claude-sonnet-4-6")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 24


def test_parse_response_clean_json() -> None:
    out = _parse_response('{"kind": "lead", "confidence": 0.9, "refined_score": 85}')
    assert out is not None
    assert out["kind"] == "lead"
    assert out["confidence"] == 0.9


def test_parse_response_json_in_text() -> None:
    raw = 'Hier mijn antwoord:\n{"kind": "promo", "confidence": 0.8}\n— einde'
    out = _parse_response(raw)
    assert out is not None
    assert out["kind"] == "promo"


def test_parse_response_invalid() -> None:
    assert _parse_response("") is None
    assert _parse_response("geen json hier") is None
    assert _parse_response("{not valid json") is None


def test_verify_post_no_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    verdict = verify_post(
        title="t", text="x", city=None, niche="cv",
        regex_score=50, regex_breakdown={},
        cache_dir=tmp_path,
    )
    assert verdict.available is False
    assert verdict.skipped_reason == "no_api_key"


def test_verify_post_uses_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-cache-test")
    cached = {
        "available": True, "kind": "lead", "confidence": 0.9,
        "refined_score": 80, "is_real_lead": True,
        "reason": "uit cache", "model": "claude-haiku-4-5-20251001",
        "skipped_reason": None,
    }
    prompt = _build_user_prompt(
        title="t", text="x", city=None, niche="cv",
        regex_score=50, regex_breakdown={},
    )
    key = _post_hash(prompt, "claude-haiku-4-5-20251001")
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{key}.json").write_text(json.dumps(cached), encoding="utf-8")

    verdict = verify_post(
        title="t", text="x", city=None, niche="cv",
        regex_score=50, regex_breakdown={},
        cache_dir=tmp_path,
    )
    assert verdict.available is True
    assert verdict.kind == "lead"
    assert verdict.reason == "uit cache"


@pytest.mark.parametrize("regex,verdict,expected", [
    (50, LlmVerdict(available=False, kind=None, confidence=0, refined_score=None,
                    is_real_lead=None, reason="", model="m", skipped_reason="x"),
     50),
    (50, LlmVerdict(available=True, kind="promo", confidence=0.9, refined_score=10,
                    is_real_lead=False, reason="r", model="m"),
     0),
    (50, LlmVerdict(available=True, kind="discussion", confidence=0.8, refined_score=20,
                    is_real_lead=False, reason="r", model="m"),
     0),
    (50, LlmVerdict(available=True, kind="info", confidence=0.8, refined_score=15,
                    is_real_lead=False, reason="r", model="m"),
     15),
    (50, LlmVerdict(available=True, kind="lead", confidence=0.8, refined_score=80,
                    is_real_lead=True, reason="r", model="m"),
     65),
    (50, LlmVerdict(available=True, kind="lead", confidence=0.8, refined_score=30,
                    is_real_lead=False, reason="r", model="m"),
     30),
])
def test_combine_score(regex: int, verdict: LlmVerdict, expected: int) -> None:
    assert combine_score(regex, verdict) == expected


def test_combine_score_low_confidence_promo_keeps_regex() -> None:
    v = LlmVerdict(available=True, kind="promo", confidence=0.3, refined_score=10,
                   is_real_lead=False, reason="r", model="m")
    assert combine_score(55, v) == 55


@pytest.mark.llm
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"),
                    reason="needs ANTHROPIC_API_KEY")
def test_verify_post_live_call(tmp_path: Path) -> None:
    """Echte Claude-call. Skipt zonder API key."""
    verdict = verify_post(
        title="CV-ketel kapot Utrecht, zoek monteur",
        text="Mijn cv is kapot, geen warm water, met spoed monteur nodig.",
        city="utrecht", niche="cv",
        regex_score=60, regex_breakdown={"location": 20, "urgency": 35},
        cache_dir=tmp_path,
    )
    assert verdict.available is True
    assert verdict.kind == "lead"
    assert verdict.refined_score is not None
    assert verdict.refined_score >= 70
