"""Structurele validatie van consumer/queries.yaml.

queries.yaml is data-driven config voor de hele pipeline.  YAML-typo's
of structuurfouten zouden silent kunnen breken (niche niet gevonden,
lege subreddit-lijst, kapotte string-interpolatie).  Deze tests vangen
zulke regressies in CI vóór ze in productie zorgen voor 0 leads.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


QUERIES_YAML = Path(__file__).resolve().parent.parent / "consumer" / "queries.yaml"
EXPECTED_NICHES = ["warmtepomp", "airco", "zonnepanelen", "cv", "renovatie"]


@pytest.fixture(scope="module")
def cfg() -> dict:
    data = yaml.safe_load(QUERIES_YAML.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "queries.yaml moet op top-level een dict zijn"
    return data


def test_defaults_reddit_subreddits_is_nonempty_list_of_strings(cfg: dict) -> None:
    """defaults.reddit_subreddits wordt door run_consumer.extra_kwargs_for_source
    doorgegeven aan reddit.fetch.  Kapotte lijst = source valt terug op
    hardcoded DEFAULT_SUBS — verlies van geconfigureerde coverage."""
    defaults = cfg.get("defaults") or {}
    subs = defaults.get("reddit_subreddits")
    assert isinstance(subs, list), f"reddit_subreddits moet list zijn, kreeg {type(subs).__name__}"
    assert subs, "reddit_subreddits is leeg — alle reddit-coverage uit queries.yaml verloren"
    for s in subs:
        assert isinstance(s, str) and s.strip(), f"subreddit-naam ongeldig: {s!r}"


def test_all_expected_niches_present(cfg: dict) -> None:
    """Daily mode loopt over deze 5 niches (DAILY_NICHES in run_consumer.py)."""
    niches = cfg.get("niches") or {}
    missing = [n for n in EXPECTED_NICHES if n not in niches]
    assert not missing, f"Niches ontbreken in queries.yaml: {missing}"


@pytest.mark.parametrize("niche", EXPECTED_NICHES)
def test_each_niche_has_required_query_buckets(cfg: dict, niche: str) -> None:
    """Elke niche moet queries_text + google_queries + marktplaats_queries
    hebben (anders krijgt expand_queries lege lijsten → silent skip)."""
    niche_cfg = (cfg.get("niches") or {}).get(niche) or {}
    for bucket in ("queries_text", "google_queries", "marktplaats_queries"):
        qs = niche_cfg.get(bucket)
        assert isinstance(qs, list) and qs, (
            f"Niche {niche!r} mist of heeft lege {bucket!r}"
        )


@pytest.mark.parametrize("niche", EXPECTED_NICHES)
def test_each_niche_has_keywords_required(cfg: dict, niche: str) -> None:
    """keywords_required wordt gebruikt in processor.intent_classifier.
    Lege lijst → niche kan niet gefilterd worden."""
    niche_cfg = (cfg.get("niches") or {}).get(niche) or {}
    kws = niche_cfg.get("keywords_required")
    assert isinstance(kws, list) and kws, f"Niche {niche!r} mist keywords_required"
