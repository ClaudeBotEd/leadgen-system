"""Runtime dead-source detector — voorkomt dat een kapotte source elke
niche-loc combo nutteloos blijft proberen.

Bij --daily --locations all worden sources tot 23× per niche aangeroepen.
Als een source HTML-structuur is veranderd, API-key vervallen of host
down: alle calls geven 0 yields maar kosten wel HTTP-budget + wall-clock.

Detector: telt consecutive 0-yield invocations per source.  Bij N (default
3) hits-in-a-row markeert source als 'dead' voor rest van de run.  Dead
sources worden geskipt door dispatch-loop.

Counter wordt gereset op succes (>0 yields) of bij reset_source_health().
"""
from __future__ import annotations


def test_reset_source_health_exists() -> None:
    from consumer.sources import reset_source_health, is_source_dead
    reset_source_health()
    assert is_source_dead("anything") is False


def test_three_consecutive_zero_yields_marks_dead() -> None:
    from consumer.sources import (
        reset_source_health, mark_source_yield, is_source_dead,
    )
    reset_source_health()

    mark_source_yield("bouwinfo", 0)
    assert not is_source_dead("bouwinfo")
    mark_source_yield("bouwinfo", 0)
    assert not is_source_dead("bouwinfo")
    mark_source_yield("bouwinfo", 0)
    assert is_source_dead("bouwinfo"), "Na 3× 0-yield zou source dead moeten zijn"


def test_yield_resets_zero_counter() -> None:
    from consumer.sources import (
        reset_source_health, mark_source_yield, is_source_dead,
    )
    reset_source_health()

    mark_source_yield("reddit", 0)
    mark_source_yield("reddit", 0)
    mark_source_yield("reddit", 5)  # success — counter reset
    mark_source_yield("reddit", 0)
    mark_source_yield("reddit", 0)
    assert not is_source_dead("reddit"), (
        "Succes zou counter moeten resetten; na 2× 0 mag source niet dead zijn"
    )


def test_reset_clears_dead_state() -> None:
    from consumer.sources import (
        reset_source_health, mark_source_yield, is_source_dead,
    )
    reset_source_health()
    mark_source_yield("tweakers", 0)
    mark_source_yield("tweakers", 0)
    mark_source_yield("tweakers", 0)
    assert is_source_dead("tweakers")
    reset_source_health()
    assert not is_source_dead("tweakers")


def test_dead_sources_independent_per_source() -> None:
    from consumer.sources import (
        reset_source_health, mark_source_yield, is_source_dead,
    )
    reset_source_health()
    for _ in range(3):
        mark_source_yield("bouwinfo", 0)
    assert is_source_dead("bouwinfo")
    assert not is_source_dead("reddit")
    assert not is_source_dead("tweakers")


# ─── Integration met run_one_niche dispatch ─────────────────────────────


def test_dispatch_skips_dead_source(tmp_path, monkeypatch) -> None:
    """Wanneer een source 3× 0 yields gaf, slaat run_one_niche hem over."""
    import argparse
    import run_consumer
    from consumer.sources import reset_source_health, mark_source_yield

    reset_source_health()
    for _ in range(3):
        mark_source_yield("bouwinfo", 0)

    cfg_path = tmp_path / "queries.yaml"
    cfg_path.write_text(
        "niches:\n"
        "  cv:\n"
        "    keywords_required: [cv]\n"
        "    queries_text: [cv ketel]\n",
        encoding="utf-8",
    )

    bouwinfo_calls: list[str] = []

    def tracking_bouwinfo(query, *, limit, location, session, **_):  # noqa: ANN001, ANN201
        bouwinfo_calls.append(query)
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "bouwinfo", tracking_bouwinfo)

    args = argparse.Namespace(
        daily=False,
        location="nederland", locations=None,
        sources="bouwinfo", niche="cv",
        limit=10, max_queries=2,
        min_score=30, max_age_days=0,
        max_runtime_minutes=0.0,
        queries_file=str(cfg_path), outdir=str(tmp_path),
        no_dedup=True, no_fuzzy_dedup=True, no_author_enrich=True,
        no_hardblock=True, no_llm=True, no_telegram=True,
        facebook_file=None, manual_file=None, manual_platform="facebook",
        dedup_threshold=0.85, llm_min_score=40, llm_max_score=75,
        telegram_threshold=80,
        sheets=False, spreadsheet_id=None, credentials=None,
        dry_run=True, verbose=False,
    )
    run_consumer.run_one_niche(args, niche="cv")

    assert bouwinfo_calls == [], (
        f"Dead source 'bouwinfo' mag niet gecalled worden; was: {bouwinfo_calls}"
    )
