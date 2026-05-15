"""Marktplaats source — query-variant control.

Standaard probeert fetch() 3 query-varianten ("q", "q gezocht", "q gevraagd")
voor maximale recall.  Bij daily multi-loc runs is dit 3× verspilling per
query × 23 locs × 5 niches.  Daily mode geeft `deep_variants=False` mee
zodat alleen de base-query gefetcht wordt.
"""
from __future__ import annotations


class _FakeResp:
    def __init__(self, text: str = ""):
        self._text = text
        self.text = text
        self.status_code = 200


class _RecordingSession:
    def __init__(self):
        self.calls: list[str] = []

    def get(self, url: str, *, params=None, accept_json: bool = False) -> _FakeResp:  # noqa: ANN001, ANN201
        self.calls.append(url)
        return _FakeResp(text="<html></html>")


def test_default_uses_three_variants() -> None:
    """Backwards compat: zonder deep_variants flag = 3 calls."""
    from consumer.sources import marktplaats
    sess = _RecordingSession()
    marktplaats.fetch("cv ketel", limit=10, session=sess)
    assert len(sess.calls) == 3, (
        f"Default zou 3 varianten moeten doen; was {len(sess.calls)}: {sess.calls}"
    )


def test_deep_variants_false_only_calls_base() -> None:
    """deep_variants=False: alleen base query, geen 'gezocht'/'gevraagd'."""
    from consumer.sources import marktplaats
    sess = _RecordingSession()
    marktplaats.fetch("cv ketel", limit=10, session=sess, deep_variants=False)
    assert len(sess.calls) == 1, (
        f"deep_variants=False zou 1 call moeten doen; was {len(sess.calls)}: {sess.calls}"
    )
    assert "gezocht" not in sess.calls[0]
    assert "gevraagd" not in sess.calls[0]


def test_deep_variants_true_explicit_three_variants() -> None:
    """deep_variants=True (expliciet) = ook 3 calls."""
    from consumer.sources import marktplaats
    sess = _RecordingSession()
    marktplaats.fetch("cv ketel", limit=10, session=sess, deep_variants=True)
    assert len(sess.calls) == 3


# ─── Integration: daily mode skipt varianten via extra_kwargs ───────────


def test_extra_kwargs_for_marktplaats_in_daily_drops_variants() -> None:
    """run_consumer.extra_kwargs_for_source moet 'deep_variants': False geven
    voor marktplaats/2dehands in daily mode."""
    from run_consumer import extra_kwargs_for_source
    kw_daily = extra_kwargs_for_source("marktplaats", defaults={}, daily=True)
    assert kw_daily.get("deep_variants") is False, kw_daily
    kw_2h = extra_kwargs_for_source("2dehands", defaults={}, daily=True)
    assert kw_2h.get("deep_variants") is False, kw_2h


def test_extra_kwargs_for_marktplaats_single_niche_keeps_deep() -> None:
    """In single-niche mode (daily=False) blijft deep_variants ongezet zodat
    fetch() default (True) gebruikt."""
    from run_consumer import extra_kwargs_for_source
    kw = extra_kwargs_for_source("marktplaats", defaults={}, daily=False)
    assert "deep_variants" not in kw
