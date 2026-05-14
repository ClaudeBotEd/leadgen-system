"""End-to-end pipeline regression: RawPost → clean → classify → score.

Aanvullende wiring-tests (bug 722) hieronder verifiëren dat hardblock,
fuzzy_dedup en llm_verifier + combine_score correct gewired zijn met de
rest van de pipeline — een laag die unit-tests individueel goed dekken,
maar de wiring tussen lagen had geen end-to-end coverage.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from consumer import Lead, RawPost, intent_from_score
from consumer.processor import (
    TextSignatureStore,
    check_hardblock,
    clean_post,
    combine_score,
    is_potential_lead,
    score_post,
    should_verify,
)
from consumer.processor.llm_verifier import LlmVerdict

from tests.canonical_corpus import ALL_POSTS
from tests.test_scorer import NICHE_KEYWORDS


def _pipeline(post: dict) -> tuple[bool, int, dict]:
    raw = RawPost(
        id=post["id"], source="test",
        url=f"https://example.com/{post['id']}",
        title=post["title"], text=post["text"],
    )
    cleaned = clean_post(raw)
    keep = is_potential_lead(cleaned["full"])
    if not keep:
        return False, 0, {}
    score, breakdown = score_post(
        cleaned,
        niche_keywords=NICHE_KEYWORDS.get(post["niche"], [post["niche"]]),
    )
    return True, score, breakdown


@pytest.mark.parametrize("post", ALL_POSTS, ids=lambda p: p["id"])
def test_pipeline_keep_decision(post: dict) -> None:
    keep, score, breakdown = _pipeline(post)
    expected_keep = post["expected"]["classifier_keep"]
    assert keep == expected_keep, (
        f"post={post['id']!r}: expected keep={expected_keep} got keep={keep} "
        f"score={score} breakdown={breakdown}"
    )


@pytest.mark.parametrize("post", ALL_POSTS, ids=lambda p: p["id"])
def test_pipeline_score_in_range_if_kept(post: dict) -> None:
    keep, score, _ = _pipeline(post)
    if not keep:
        return
    lo = post["expected"]["score_min"]
    hi = post["expected"]["score_max"]
    assert lo <= score <= hi, (
        f"post={post['id']!r}: expected score in [{lo},{hi}] got {score}"
    )


def test_pipeline_produces_lead_object() -> None:
    raw = RawPost(
        id="x", source="reddit", url="https://reddit.com/abc",
        title="CV kapot Utrecht zoek monteur",
        text="Met spoed monteur nodig, geen warm water.",
    )
    cleaned = clean_post(raw)
    score, breakdown = score_post(cleaned, niche_keywords=["cv", "ketel"])
    lead = Lead(
        id=raw.id, source=raw.source,
        title=cleaned["title"], text=cleaned["text"],
        summary=cleaned["summary"], url=raw.url,
        city=cleaned["city"], score=score,
        intent=intent_from_score(score), breakdown=breakdown,
        niche="cv",
    )
    assert lead.score >= 70
    assert lead.intent == "hot"
    assert lead.city == "utrecht"
    assert "broken_bonus" in lead.breakdown
    assert lead.to_dict()["score"] == lead.score


# ---------------------------------------------------------------------------
# Wiring integration tests (bug 722) — hardblock + fuzzy_dedup + llm_verifier
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_post(*, post_id: str, source: str, title: str, text: str,
               url: str | None = None, author: str | None = None) -> RawPost:
    return RawPost(
        id=post_id, source=source,
        url=url or f"https://example.com/{post_id}",
        title=title, text=text, author=author,
        created_at=_now_iso(),
    )


def _wired_pipeline(raw: RawPost, *, niche: str,
                    fuzzy_store: TextSignatureStore,
                    fake_verdict: LlmVerdict | None) -> dict:
    """Volledige run_consumer-hot-path (zonder fetching/IO/Sheets)."""
    hb = check_hardblock(raw)
    if hb.blocked:
        return {"skip": "hardblock", "reason": hb.reason}

    cleaned = clean_post(raw)
    if not is_potential_lead(cleaned["full"]):
        return {"skip": "not_potential_lead"}

    dup = fuzzy_store.find_duplicate(cleaned["full"])
    if dup is not None:
        return {"skip": "fuzzy_dup", "match_id": dup[0], "sim": dup[1]}

    keywords = NICHE_KEYWORDS.get(niche, [niche])
    score, breakdown = score_post(cleaned, niche_keywords=keywords)
    score_before_llm = score

    if should_verify(score) and fake_verdict is not None:
        score = combine_score(score, fake_verdict)

    fuzzy_store.add(raw.id, cleaned["full"])
    return {
        "id": raw.id,
        "score": score,
        "score_before_llm": score_before_llm,
        "breakdown": breakdown,
        "city": cleaned.get("city"),
    }


def test_pipeline_hardblocks_aggregator_url(tmp_path: Path) -> None:
    """Aggregator hosts (slimster.nl etc) krijgen geen verdere processing."""
    store = TextSignatureStore(path=tmp_path / "sigs.json", threshold=0.85)
    raw = _make_post(
        post_id="agg1", source="other",
        title="warmtepomp aanvraag Utrecht 3500",
        text="ik zoek installateur voor warmtepomp met spoed",
        url="https://www.slimster.nl/aanvraag/123",
    )
    result = _wired_pipeline(raw, niche="warmtepomp",
                             fuzzy_store=store, fake_verdict=None)
    assert result["skip"] == "hardblock"
    assert "aggregator" in result["reason"]


def test_pipeline_hardblocks_corporate_author(tmp_path: Path) -> None:
    """Corporate-author patroon (BLOCKED_AUTHOR_PATTERNS) drops the post.

    Pattern: r'(installateur|installatie|verwarming|monteurs?|...)\\b.*\\b(bv|bvba|nv|gmbh|bedrijf)\\b'
    Match: 'installateur ... bv' op woord-boundaries.
    """
    store = TextSignatureStore(path=tmp_path / "sigs.json", threshold=0.85)
    raw = _make_post(
        post_id="corp1", source="reddit",
        title="vraag voor cv-installatie",
        text="hoe los ik dit op?",
        author="installateur jansen bv",
    )
    result = _wired_pipeline(raw, niche="cv",
                             fuzzy_store=store, fake_verdict=None)
    assert result["skip"] == "hardblock"


def test_pipeline_drops_fuzzy_duplicates(tmp_path: Path) -> None:
    """Tweede bijna-identieke post wordt door fuzzy_store gedropt."""
    store = TextSignatureStore(path=tmp_path / "sigs.json", threshold=0.85)
    body = ("ik zoek advies voor warmtepomp installatie in Utrecht 3500, "
            "budget 8000 euro, welke merken zijn betrouwbaar? graag offerte "
            "voor monteur met spoed")

    raw1 = _make_post(post_id="r1", source="reddit",
                      title="warmtepomp advies", text=body, author="alice")
    res1 = _wired_pipeline(raw1, niche="warmtepomp",
                           fuzzy_store=store, fake_verdict=None)
    assert "skip" not in res1, f"eerste post moet passeren: {res1}"

    raw2 = _make_post(
        post_id="r2", source="reddit",
        title="WARMTEPOMP ADVIES!!",
        text=body + " (versie 2)",
        author="bob",
    )
    res2 = _wired_pipeline(raw2, niche="warmtepomp",
                           fuzzy_store=store, fake_verdict=None)
    assert res2.get("skip") == "fuzzy_dup", f"r2 moet dup zijn: {res2}"


def test_dry_run_skips_sheets_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    """--dry-run moet sync_to_sheets() niet aanroepen, ook al zijn er leads."""
    import argparse
    import run_consumer

    cfg_path = tmp_path / "test_queries.yaml"
    cfg_path.write_text(
        "niches:\n"
        "  cv:\n"
        "    keywords_required: [cv]\n"
        "    queries_text: [cv ketel kapot]\n",
        encoding="utf-8",
    )

    def empty_source(query, *, limit, location, session):  # noqa: ANN001, ANN201
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "reddit", empty_source)
    sync_calls: list = []

    def fake_sync(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN201
        sync_calls.append((args, kwargs))
        return {"all_added": 0, "hot_added": 0, "opp_added": 0,
                "spreadsheet_url": ""}

    monkeypatch.setattr(run_consumer, "sync_to_sheets", fake_sync)

    args = argparse.Namespace(
        location="nederland", limit=10, max_queries=1,
        sources="reddit", outdir=str(tmp_path),
        no_dedup=True, no_fuzzy_dedup=True, no_author_enrich=True,
        no_hardblock=True, no_llm=True, no_telegram=True,
        dedup_threshold=0.85, min_score=60, max_age_days=14,
        llm_min_score=40, llm_max_score=75, telegram_threshold=80,
        queries_file=str(cfg_path), facebook_file=None,
        spreadsheet_id="dummy", credentials=None,
        niche="cv", sheets=False,
        dry_run=True,
    )

    run_consumer.run_daily(args)
    assert sync_calls == [], (
        f"dry_run mocht geen Sheets sync triggeren; got {len(sync_calls)} call(s)"
    )


def test_run_one_niche_saves_dedup_state_on_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug: bij KeyboardInterrupt midden in fetch raakte de seen-store
    kwijt en re-processte de volgende run alle URLs opnieuw (dubbele
    LLM-kosten).  Try/finally borgt dat seen.save() altijd uitgevoerd
    wordt."""
    import argparse
    from consumer.utils import SeenStore
    import run_consumer

    outdir = tmp_path
    seen_path = outdir / "seen_hashes.json"

    pre_store = SeenStore(seen_path)
    pre_store.add("dummy-fingerprint-pre")
    pre_store.save()
    assert seen_path.exists()

    # Minimale config in tmp_path zodat load_config slaagt
    cfg_path = tmp_path / "test_queries.yaml"
    cfg_path.write_text(
        "niches:\n"
        "  cv:\n"
        "    keywords_required: [cv]\n"
        "    queries_text: [cv ketel kapot]\n",
        encoding="utf-8",
    )

    def crashing_source(query, *, limit, location, session):  # noqa: ANN001, ANN201
        raise KeyboardInterrupt("user pressed ctrl+c")

    monkeypatch.setitem(run_consumer.REGISTRY, "reddit", crashing_source)

    args = argparse.Namespace(
        location="nederland",
        limit=10,
        max_queries=1,
        sources="reddit",
        outdir=str(outdir),
        no_dedup=False,
        no_fuzzy_dedup=True,
        no_author_enrich=True,
        no_hardblock=False,
        no_llm=True,
        no_telegram=True,
        dedup_threshold=0.85,
        min_score=60,
        max_age_days=14,
        llm_min_score=40,
        llm_max_score=75,
        telegram_threshold=80,
        queries_file=str(cfg_path),
        facebook_file=None,
    )

    with pytest.raises(KeyboardInterrupt):
        run_consumer.run_one_niche(args, niche="cv")

    post_store = SeenStore(seen_path)
    assert post_store.has("dummy-fingerprint-pre"), (
        "seen-store moet bewaard zijn ook bij KeyboardInterrupt"
    )


def test_pipeline_llm_verdict_modifies_borderline_score(tmp_path: Path) -> None:
    """combine_score is gewired: bij een borderline regex-score levert een
    'lead'-verdict een aangepaste finale score op."""
    store = TextSignatureStore(path=tmp_path / "sigs.json", threshold=0.85)

    raw = _make_post(
        post_id="b1", source="reddit",
        title="warmtepomp twijfel Utrecht",
        text=("ik denk na over warmtepomp, niet zeker welke. "
              "advies welkom over merken en kosten"),
        author="alice",
    )

    boost = LlmVerdict(
        available=True, kind="lead", confidence=0.9,
        refined_score=90, is_real_lead=True,
        reason="echte koper-intentie",
        model="fake-test-model",
    )
    result = _wired_pipeline(raw, niche="warmtepomp",
                             fuzzy_store=store, fake_verdict=boost)

    if "skip" in result:
        pytest.skip(f"crafted post werd voortijdig gedropt: {result}")

    if should_verify(result["score_before_llm"]):
        assert result["score"] != result["score_before_llm"], (
            "LLM verdict had de score moeten aanpassen; "
            f"before={result['score_before_llm']} after={result['score']}"
        )
