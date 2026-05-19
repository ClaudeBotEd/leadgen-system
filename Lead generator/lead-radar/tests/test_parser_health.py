"""Per-source parser-health audit.

Each source ships with a captured live-sample fixture in
tests/fixtures/parser_health/<source>/. The parser must extract at
least one RawPost with the required fields populated.

If a fixture is missing, the test fails with instructions for capturing
one. See the URL pattern in each source module's top-of-file docstring.

Run subset:
    python -m pytest tests/test_parser_health.py -v
    python -m pytest tests/test_parser_health.py -v -k reddit
"""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer.sources import REGISTRY

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "parser_health"

SOURCES_TO_AUDIT: list[str] = [
    "reddit", "reddit_new", "tweakers",
    "bouwinfo", "bouwinfo_forum",
    "klusidee_forum", "ouders_forum",
    "google", "marktplaats", "2dehands",
]


@pytest.mark.parametrize("source_name", SOURCES_TO_AUDIT)
def test_source_registered(source_name):
    """Sanity — source must still be in REGISTRY for Plan B to activate it."""
    assert source_name in REGISTRY, f"Source {source_name!r} missing from REGISTRY"


@pytest.mark.parametrize("source_name", SOURCES_TO_AUDIT)
def test_parser_health_fixture_exists(source_name):
    """Each audited source must have a captured fixture for offline validation."""
    source_dir = FIXTURES_DIR / source_name
    if not source_dir.exists() or not any(source_dir.iterdir()):
        pytest.fail(
            f"Missing parser-health fixture for {source_name!r}.\n"
            f"Capture one — see test docstring for URL pattern."
        )


def _load_fixture(source_name: str, ext: str = "html") -> str:
    path = FIXTURES_DIR / source_name / f"sample.{ext}"
    if not path.exists():
        pytest.skip(f"Fixture not captured: {path}")
    return path.read_text(encoding="utf-8")


# Per-source parser tests — adapted to the actual private helpers in each
# source module. If a module has no parse-from-string helper, one is
# extracted in Step 4 of the audit task.


def test_reddit_parser_extracts_post():
    from consumer.sources import reddit as src
    import json
    data = json.loads(_load_fixture("reddit", "json"))
    posts = src._parse_listing(data)
    assert posts, "Reddit fixture must contain at least one listing"
    p = posts[0]
    assert p.source == "reddit"
    assert p.source_id.startswith("reddit:r/")
    assert p.url.startswith("https://")
    assert p.id


def test_reddit_new_parser_extracts_post():
    from consumer.sources import reddit_new as src
    if not hasattr(src, "fetch_from_json"):
        pytest.skip(
            "reddit_new needs a fetch_from_json(data, sub=...) helper for "
            "offline testing — extract one in this task."
        )
    import json
    data = json.loads(_load_fixture("reddit_new", "json"))
    posts = src.fetch_from_json(data, sub="DIYNL")
    assert posts
    p = posts[0]
    assert p.source == "reddit_new"
    assert p.source_id == "reddit_new:r/DIYNL"


def test_tweakers_parser_extracts_post():
    from consumer.sources import tweakers as src
    html = _load_fixture("tweakers", "html")
    posts = src._parse_search(html)
    assert posts, "Tweakers fixture must yield >=1 post"
    assert all(p.source == "tweakers" for p in posts)
    assert all(p.source_id.startswith("tweakers:") for p in posts)


def test_bouwinfo_parser_extracts_post():
    """bouwinfo.py exposes _parse(html) — the test uses that name."""
    from consumer.sources import bouwinfo as src
    html = _load_fixture("bouwinfo", "html")
    posts = src._parse(html)
    assert posts, "Bouwinfo fixture must yield >=1 post"
    assert all(p.source == "bouwinfo" for p in posts)


def test_bouwinfo_forum_parser_extracts_post():
    from consumer.sources import bouwinfo_forum as src
    html = _load_fixture("bouwinfo_forum", "html")
    posts = src._parse_category_page(html, subforum_slug="zonnepanelen-warmtepompen-laadpalen")
    assert posts, "Bouwinfo-forum fixture must yield >=1 post"
    assert all(p.source == "bouwinfo" for p in posts)  # source_name = "bouwinfo" in module
    assert all(p.source_id.startswith("bouwinfo_forum:") for p in posts)


def test_klusidee_forum_parser_extracts_post():
    """klusidee_forum exposes _parse_category_page (not _parse_subforum)."""
    from consumer.sources import klusidee_forum as src
    html = _load_fixture("klusidee_forum", "html")
    posts = src._parse_category_page(html, subforum_slug="cv-ketels-gaskachels-en-geisers.33")
    assert posts, "Klusidee fixture must yield >=1 post"
    assert all(p.source == "klusidee" for p in posts)
    assert all(p.source_id.startswith("klusidee_forum:") for p in posts)


def test_ouders_forum_parser_extracts_post():
    """ouders_forum._parse_subforum_page takes only html (no subforum_slug param)."""
    from consumer.sources import ouders_forum as src
    html = _load_fixture("ouders_forum", "html")
    posts = src._parse_subforum_page(html)
    assert posts, "Ouders forum fixture must yield >=1 post"
    assert all(p.source == "ouders" for p in posts)
    assert all(p.source_id.startswith("ouders_forum:") for p in posts)


def test_google_ddg_parser_extracts_post():
    """google source uses duckduckgo_search lib — no offline HTML parser.

    We verify _parse_results(results_list) exists for offline testing.
    It should accept a list of dicts like {'href': ..., 'title': ..., 'body': ...}
    and return RawPosts.
    """
    from consumer.sources import google as src
    if not hasattr(src, "_parse_results"):
        pytest.skip(
            "google source has no _parse_results(results) helper for offline "
            "testing — extract one in this task. It should accept a list of "
            "dicts like {'href': ..., 'title': ..., 'body': ...} and return RawPosts."
        )
    import json
    data = json.loads(_load_fixture("google", "json"))
    posts = src._parse_results(data)
    assert posts, "DDG fixture must yield >=1 result"
    assert all(p.source == "google" for p in posts)
    assert all(p.source_id.startswith("google:") for p in posts)


def test_marktplaats_parser_extracts_post():
    from consumer.sources import marktplaats as src
    html = _load_fixture("marktplaats", "html")
    posts = src._parse_html(
        html,
        base="https://www.marktplaats.nl",
        source_id_prefix="marktplaats:diensten/amsterdam",
        source_name="marktplaats",
    )
    assert posts, "Marktplaats fixture must yield >=1 listing"
    assert all(p.source == "marktplaats" for p in posts)
    assert all(p.source_id.startswith("marktplaats:") for p in posts)


def test_tweedehands_parser_extracts_post():
    """2dehands.be uses the same parser as marktplaats with a different source_name."""
    from consumer.sources import marktplaats as src
    html = _load_fixture("2dehands", "html")
    posts = src._parse_html(
        html,
        base="https://www.2dehands.be",
        source_id_prefix="2dehands:diensten/antwerpen",
        source_name="2dehands",
    )
    assert posts, "2dehands fixture must yield >=1 listing"
    assert all(p.source == "2dehands" for p in posts)
    assert all(p.source_id.startswith("2dehands:") for p in posts)
