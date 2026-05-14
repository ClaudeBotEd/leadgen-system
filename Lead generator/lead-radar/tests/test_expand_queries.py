"""Regression tests voor expand_queries — voorkomt silent zero-yield als
een source in REGISTRY zit maar geen queries-mapping krijgt.

De originele bug: '2dehands' zat in ALL_SOURCES + REGISTRY, maar
expand_queries() returnde een dict zónder '2dehands' key.  Dispatch-loop
deed dan `queries_per_source.get(source_name) or []` -> [] -> source
werd nooit aangeroepen.  Geen exception, geen leads, geen feedback.
"""
from __future__ import annotations

import pytest

from run_consumer import expand_queries
from consumer.sources import ALL_SOURCES


@pytest.fixture
def niche_cfg() -> dict:
    """Minimale niche-config met alle 3 query-buckets non-leeg."""
    return {
        "keywords_required": ["warmtepomp"],
        "queries_text": [
            "warmtepomp installateur gezocht",
            "warmtepomp offerte",
        ],
        "google_queries": [
            'site:reddit.com warmtepomp {location}',
            '"warmtepomp installateur" {location}',
        ],
        "marktplaats_queries": [
            "warmtepomp installateur gezocht",
            "warmtepomp monteur gevraagd",
        ],
    }


def test_expand_queries_covers_every_registered_source(niche_cfg: dict) -> None:
    """Geen silent gaps: elke source in ALL_SOURCES krijgt een queries-list.

    Falen betekent dat de dispatch-loop in run_consumer.py die source
    zal overslaan zonder error — exact het 2dehands-bug-pattern.
    """
    result = expand_queries(niche_cfg, location="nederland", max_queries=50)
    missing = [s for s in ALL_SOURCES if s not in result]
    assert not missing, (
        f"expand_queries mist mapping voor sources {missing}; "
        f"deze sources worden silent geskipt in run_consumer.py."
    )


def test_expand_queries_2dehands_uses_marktplaats_queries(niche_cfg: dict) -> None:
    """2dehands is de BE-zuster van marktplaats — moet dezelfde queries krijgen."""
    result = expand_queries(niche_cfg, location="antwerpen", max_queries=50)
    assert "2dehands" in result, "2dehands ontbreekt in expand_queries-output"
    assert result["2dehands"], "2dehands kreeg lege queries — zou marktplaats_queries moeten gebruiken"
    assert result["2dehands"] == result["marktplaats"], (
        "2dehands en marktplaats zijn dezelfde classifieds-engine; "
        "moeten exact dezelfde queries krijgen."
    )


def test_expand_queries_all_sources_get_nonempty_lists(niche_cfg: dict) -> None:
    """Voor een niche met queries in alle drie buckets moet elke source ≥1 query krijgen."""
    result = expand_queries(niche_cfg, location="amsterdam", max_queries=50)
    for source in ALL_SOURCES:
        qs = result.get(source) or []
        assert qs, f"Source {source!r} kreeg lege query-list bij volledige niche-config"
