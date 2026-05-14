"""Regression-tests voor scorer.score_post."""
from __future__ import annotations

import pytest

from consumer import intent_from_score
from consumer.processor.cleaner import clean_post
from consumer.processor.scorer import score_post
from consumer import RawPost

from tests.canonical_corpus import ALL_POSTS

NICHE_KEYWORDS = {
    "warmtepomp":   ["warmtepomp", "warmtepompen"],
    "airco":        ["airco", "airconditioning"],
    "zonnepanelen": ["zonnepanelen", "zonne", "pv-installatie"],
    "cv":           ["cv", "cv-ketel", "ketel", "verwarming", "boiler"],
    "renovatie":    ["renovatie", "renoveren", "verbouwing"],
}


def _build_cleaned(post: dict) -> dict:
    raw = RawPost(
        id=post["id"],
        source="test",
        url="https://example.com/" + post["id"],
        title=post["title"],
        text=post["text"],
    )
    return clean_post(raw)


@pytest.mark.parametrize("post", ALL_POSTS, ids=lambda p: p["id"])
def test_score_in_range(post: dict) -> None:
    cleaned = _build_cleaned(post)
    keywords = NICHE_KEYWORDS.get(post["niche"], [post["niche"]])
    score, breakdown = score_post(cleaned, niche_keywords=keywords)
    lo = post["expected"]["score_min"]
    hi = post["expected"]["score_max"]
    assert lo <= score <= hi, (
        f"post={post['id']!r} expected score in [{lo},{hi}] but got {score}. "
        f"breakdown={breakdown}"
    )


@pytest.mark.parametrize("post", ALL_POSTS, ids=lambda p: p["id"])
def test_intent_matches(post: dict) -> None:
    cleaned = _build_cleaned(post)
    keywords = NICHE_KEYWORDS.get(post["niche"], [post["niche"]])
    score, _ = score_post(cleaned, niche_keywords=keywords)
    intent = intent_from_score(score)
    assert intent in {"hot", "warm", "cold"}


def test_offtopic_penalty_applies() -> None:
    raw = RawPost(
        id="x", source="test", url="https://example.com/x",
        title="Wie kent een fietsenmaker in Amsterdam",
        text="Mijn fiets is kapot, zoek monteur in Amsterdam met spoed.",
    )
    cleaned = clean_post(raw)
    score, breakdown = score_post(cleaned, niche_keywords=["warmtepomp"])
    assert breakdown.get("off_topic_penalty") == -30


def test_score_caps_at_100() -> None:
    raw = RawPost(
        id="x", source="test", url="https://example.com/x",
        title="CV kapot Utrecht zoek monteur met spoed!",
        text=(
            "Mijn cv-ketel is kapot, geen warm water, storing, foutmelding F12. "
            "Zoek installateur in Utrecht met spoed, asap, deze week nog. "
            "Budget 3000 euro, offerte nodig. Bouwjaar woning 1985, 120m2."
        ),
    )
    cleaned = clean_post(raw)
    score, _ = score_post(cleaned, niche_keywords=["cv", "ketel"])
    assert score == 100


def test_score_floors_at_0() -> None:
    raw = RawPost(id="x", source="test", url="https://example.com/x", title="", text="")
    cleaned = clean_post(raw)
    score, _ = score_post(cleaned, niche_keywords=["warmtepomp"])
    assert score == 0
