"""End-to-end pipeline regression: RawPost → clean → classify → score."""
from __future__ import annotations

import pytest

from consumer import Lead, RawPost, intent_from_score
from consumer.processor import clean_post, is_potential_lead, score_post

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
