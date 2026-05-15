"""Auto-scale max_queries bij multi-location daily-runs.

Bij --locations all (23 locaties) levert max_queries=12 een combinatorische
explosie: 23 × 12 = 276 query-permutaties per source per niche.  Query-
VARIATIE is bij multi-loc minder belangrijk omdat de locatie zelf al de
variatie levert.  We scalen daarom omlaag.

Formule: max(3, base // ceil(sqrt(n_locations))), gecapt op base.
- 1 loc: geen reductie
- 5 locs: 12/3 = 4
- 23 locs: 12/5 = 2 → bodem 3
- Reden voor sqrt: lineaire reductie zou te aggressief zijn bij weinig locs;
  sqrt geeft gradient gedrag.
"""
from __future__ import annotations

import pytest


def test_scale_max_queries_function_exists() -> None:
    """Functie moet importeerbaar zijn vanuit run_consumer."""
    from run_consumer import scale_max_queries_for_locations
    assert callable(scale_max_queries_for_locations)


def test_single_location_no_reduction() -> None:
    """1 locatie = single-loc mode = geen scaling."""
    from run_consumer import scale_max_queries_for_locations
    assert scale_max_queries_for_locations(12, 1) == 12


def test_zero_or_negative_locations_treated_as_single() -> None:
    """Defensief: 0 of negatief = treat als single-loc."""
    from run_consumer import scale_max_queries_for_locations
    assert scale_max_queries_for_locations(12, 0) == 12
    assert scale_max_queries_for_locations(12, -5) == 12


def test_five_locations_reduces_to_quarter() -> None:
    """5 locs: ceil(sqrt(5))=3, 12//3=4."""
    from run_consumer import scale_max_queries_for_locations
    assert scale_max_queries_for_locations(12, 5) == 4


def test_twenty_three_locations_hits_floor() -> None:
    """23 locs (preset 'all'): ceil(sqrt(23))=5, 12//5=2 → bodem 3."""
    from run_consumer import scale_max_queries_for_locations
    assert scale_max_queries_for_locations(12, 23) == 3


def test_huge_location_count_stays_at_floor() -> None:
    """100 locs blijft bij minimum 3, gaat niet onder."""
    from run_consumer import scale_max_queries_for_locations
    assert scale_max_queries_for_locations(12, 100) == 3


def test_low_base_does_not_scale_upward() -> None:
    """Als base lager is dan de bodem, scale niet omhoog — respect user intent."""
    from run_consumer import scale_max_queries_for_locations
    # base=2, 5 locs: zonder cap zou je max(3, 0)=3 krijgen → upward scale
    assert scale_max_queries_for_locations(2, 5) == 2


@pytest.mark.parametrize("base,n,expected", [
    (8, 1, 8),     # single-loc base 8
    (8, 4, 4),    # 4 locs: ceil(sqrt(4))=2, 8//2=4
    (8, 9, 3),     # 9 locs: ceil(sqrt(9))=3, 8//3=2 → bodem 3
    (20, 23, 4),   # 23 locs: ceil(sqrt(23))=5, 20//5=4
])
def test_scale_parametrized(base: int, n: int, expected: int) -> None:
    from run_consumer import scale_max_queries_for_locations
    assert scale_max_queries_for_locations(base, n) == expected


def test_run_daily_scales_max_queries_at_multi_location(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In run_daily bij 3 locs: args.max_queries wordt teruggebracht (van DAILY 12)."""
    import argparse
    import run_consumer

    cfg_path = tmp_path / "queries.yaml"
    cfg_path.write_text(
        "defaults:\n"
        "  cities_nl: [amsterdam, rotterdam, utrecht]\n"
        "niches:\n"
        "  cv:\n"
        "    keywords_required: [cv]\n"
        "    queries_text: [a, b, c, d, e, f, g, h, i, j, k, l, m, n, o]\n",
        encoding="utf-8",
    )

    observed_max_queries: list[int] = []

    def empty_source(query, *, limit, location, session, **_):  # noqa: ANN001, ANN201
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "reddit", empty_source)

    orig_run_one_niche = run_consumer.run_one_niche

    def tracking_run_one_niche(args, niche, **kwargs):  # noqa: ANN001, ANN003, ANN201
        observed_max_queries.append(args.max_queries)
        return orig_run_one_niche(args, niche, **kwargs)

    monkeypatch.setattr(run_consumer, "run_one_niche", tracking_run_one_niche)

    args = argparse.Namespace(
        daily=True, location=None,
        locations="nl",  # preset = 3 locaties (uit cities_nl above)
        sources="reddit", niche=None,
        limit=10, max_queries=8,  # default → DAILY zet naar 12
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
    run_consumer.run_daily(args)

    # 3 locs: ceil(sqrt(3))=2, 12//2=6 → expected 6
    assert observed_max_queries, "Geen run_one_niche calls geobserveerd"
    assert all(mq == 6 for mq in observed_max_queries), (
        f"max_queries niet auto-scaled bij 3 locs; observed={observed_max_queries}"
    )
