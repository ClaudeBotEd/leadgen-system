"""Regression-tests voor llm_verifier — pure-function delen + skipped paths."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from consumer.processor.llm_verifier import (
    DEFAULT_CACHE_DIR,
    LlmVerdict,
    _build_user_prompt,
    _parse_response,
    _post_hash,
    combine_score,
    get_run_stats,
    reset_run_counters,
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


def test_default_cache_dir_is_absolute() -> None:
    """DEFAULT_CACHE_DIR moet absoluut zijn — anders mist cache hits onder
    cron/systemd waar cwd niet de repo-root is. Cache miss = elke borderline
    post triggert een echte Anthropic API call (kost geld)."""
    assert DEFAULT_CACHE_DIR.is_absolute(), (
        f"DEFAULT_CACHE_DIR={DEFAULT_CACHE_DIR!r} is relatief; werkt niet onder cron."
    )


def test_default_cache_dir_anchored_to_lead_radar_root() -> None:
    """Cache zit op lead-radar/.cache/llm_verifier/ ongeacht waar Python wordt
    aangeroepen."""
    assert DEFAULT_CACHE_DIR.name == "llm_verifier"
    assert DEFAULT_CACHE_DIR.parent.name == ".cache"
    expected_root = Path(__file__).resolve().parent.parent
    assert DEFAULT_CACHE_DIR.parent.parent == expected_root, (
        f"Expected cache under {expected_root}, got {DEFAULT_CACHE_DIR}"
    )


def test_parse_response_handles_trailing_text() -> None:
    """Claude voegt soms uitleg toe na het JSON-object. Oude greedy regex
    .{.*} matchte van eerste { tot laatste } — bij een tweede { } verderop
    gaf het invalid JSON en silently dropte de hele verdict."""
    text = '{"kind": "lead", "confidence": 0.9, "refined_score": 85} extra explanation {meta: ok}'
    out = _parse_response(text)
    assert out is not None
    assert out["kind"] == "lead"
    assert out["refined_score"] == 85


def test_parse_response_handles_prefix_text() -> None:
    """Tekst vóór het JSON-object mag het parsen niet verstoren."""
    text = 'Here is my analysis: {"kind": "info", "confidence": 0.5, "refined_score": 30}'
    out = _parse_response(text)
    assert out is not None
    assert out["kind"] == "info"


def test_parse_response_handles_nested_objects() -> None:
    """Geneste objecten binnen het JSON-object moeten correct geteld worden."""
    text = '{"kind": "lead", "meta": {"nested": true}, "refined_score": 90}'
    out = _parse_response(text)
    assert out is not None
    assert out["kind"] == "lead"
    assert out["refined_score"] == 90


def test_parse_response_returns_none_on_no_json() -> None:
    """Geen JSON in tekst → None."""
    assert _parse_response("Sorry, I cannot answer that.") is None
    assert _parse_response("") is None


# --- Budget cap (issue 721) -------------------------------------------------


def test_verify_post_skipped_when_budget_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """LEAD_RADAR_LLM_BUDGET_EUR=0 → skipt zonder API call, geen kosten."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-budget-test")
    monkeypatch.setenv("LEAD_RADAR_LLM_BUDGET_EUR", "0")
    reset_run_counters()
    verdict = verify_post(
        title="t", text="x", city=None, niche="cv",
        regex_score=50, regex_breakdown={},
        cache_dir=tmp_path,
    )
    assert verdict.available is False
    assert verdict.skipped_reason == "budget_exhausted"


def test_verify_post_no_budget_var_proceeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Geen env var → geen cap; API-call wordt geprobeerd (faalt op fake key
    of network, dat is OK — we testen dat budget_exhausted niet triggert)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-budget-test")
    monkeypatch.delenv("LEAD_RADAR_LLM_BUDGET_EUR", raising=False)
    reset_run_counters()
    verdict = verify_post(
        title="t", text="x", city=None, niche="cv",
        regex_score=50, regex_breakdown={},
        cache_dir=tmp_path,
    )
    assert verdict.skipped_reason != "budget_exhausted"


def test_verify_post_invalid_budget_var_treated_as_no_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ongeldige value → log warning, behandelen als geen cap (defensief)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-budget-test")
    monkeypatch.setenv("LEAD_RADAR_LLM_BUDGET_EUR", "not-a-number")
    reset_run_counters()
    verdict = verify_post(
        title="t", text="x", city=None, niche="cv",
        regex_score=50, regex_breakdown={},
        cache_dir=tmp_path,
    )
    assert verdict.skipped_reason != "budget_exhausted"


def test_reset_run_counters_is_callable() -> None:
    """reset_run_counters() moet callable zijn zonder args, geen exceptions."""
    reset_run_counters()
    reset_run_counters()  # idempotent


def test_get_run_stats_returns_zero_after_reset() -> None:
    """Stats moeten 0 zijn direct na reset_run_counters()."""
    reset_run_counters()
    stats = get_run_stats()
    assert stats["api_calls"] == 0
    assert stats["cache_hits"] == 0
    assert stats["cache_misses"] == 0


def test_cache_hit_increments_counter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Een cache-hit moet cache_hits ophogen, niet cache_misses."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-cache-test")
    reset_run_counters()

    # Seed cache met een voorberekende verdict
    prompt = _build_user_prompt(
        title="t", text="x", city=None, niche="cv",
        regex_score=50, regex_breakdown={},
    )
    key = _post_hash(prompt, "claude-haiku-4-5-20251001")
    cached = {
        "available": True, "kind": "lead", "confidence": 0.9,
        "refined_score": 80, "is_real_lead": True,
        "reason": "uit cache", "model": "claude-haiku-4-5-20251001",
        "skipped_reason": None,
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{key}.json").write_text(json.dumps(cached), encoding="utf-8")

    verify_post(
        title="t", text="x", city=None, niche="cv",
        regex_score=50, regex_breakdown={},
        cache_dir=tmp_path,
    )
    stats = get_run_stats()
    assert stats["cache_hits"] == 1
    assert stats["cache_misses"] == 0


def test_post_hash_changes_when_system_prompt_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bug: als SYSTEM_PROMPT verandert (bv. om classificatie aan te
    scherpen), bleef de cache-key hetzelfde — oude verdicts werden
    geserveerd vanaf disk en de nieuwe prompt had geen effect totdat
    cache handmatig leeggemaakt werd."""
    from consumer.processor import llm_verifier

    h_before = _post_hash("test text", "claude-haiku")
    monkeypatch.setattr(llm_verifier, "_SYSTEM_PROMPT_FINGERPRINT", "deadbeef")
    h_after = _post_hash("test text", "claude-haiku")
    assert h_before != h_after, (
        "Cache key moet veranderen als SYSTEM_PROMPT-fingerprint verandert"
    )
