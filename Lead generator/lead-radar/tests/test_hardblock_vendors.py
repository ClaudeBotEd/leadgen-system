"""Vendor-title hardblock — voorkomt 'Loodgieter 24/7 Spoed Bel direct' leads.

Probleem (live waargenomen in daily-run 2026-05-15):
Marktplaats listings van CV-monteurs/loodgieters scoorden 100 (HOT) omdat
- titel bevat 'monteur' / 'installateur' (installer-match 25)
- titel bevat 'spoed' (urgency 35)
- titel bevat 'storing' (broken_bonus 40)
Maar deze posts zijn vendors (aanbieders), niet consumers (vragers).
is_potential_lead pakt enkele consumer-vibe woorden ('u kunt', 'het is')
en laat 'em door.

Hardblock-laag is robuuster: vendor-title patronen ('24/7', 'Bel direct',
'Snel ter plaatse', telefoonnummer in titel) zijn nooit consumer-intent.
"""
from __future__ import annotations

import pytest

from consumer import RawPost
from consumer.processor.hardblock import check_hardblock


@pytest.mark.parametrize("title", [
    "Loodgieter & CV Monteur 24/7 Spoed | Lekkage | Riool | Ketel",
    "CV Storing? Spoed Monteur Dani CV - Snel ter plaatse",
    "Verstopping? Bel direct uw afvoerspecialist",
    "Spoedmonteur 24/7 bereikbaar voor CV-installaties",
    "Snel ter plaatse — loodgieter Amsterdam 020-1234567",
    "Bel ons nu voor warmtepomp service",
])
def test_vendor_title_patterns_blocked(title: str) -> None:
    """Vendor-style titels moeten worden geblocked op hard-block niveau."""
    post = RawPost(
        id="x", source="marktplaats",
        url="https://www.marktplaats.nl/v/test",
        title=title, text="",
    )
    result = check_hardblock(post)
    assert result.blocked, f"Vendor title niet geblocked: {title!r}"
    assert result.reason and result.reason.startswith("vendor_title:"), result.reason


@pytest.mark.parametrize("title", [
    "Warmtepomp installateur gezocht in Amsterdam, met spoed",
    "CV ketel kapot, wie kan helpen?",
    "Advies nodig voor renovatie badkamer",
    "Wij willen onze warmtepomp laten installeren — offerte gezocht",
    "Spoed: cv-monteur nodig in Den Haag",
])
def test_legitimate_consumer_intent_not_blocked(title: str) -> None:
    """Echte consumer-vragen mogen niet door vendor-filter geraakt worden."""
    post = RawPost(
        id="x", source="reddit",
        url="https://reddit.com/r/test/comments/abc/",
        title=title, text="",
    )
    result = check_hardblock(post)
    assert not result.blocked, (
        f"Consumer-titel onterecht geblocked als vendor: {title!r} "
        f"(reason={result.reason})"
    )
