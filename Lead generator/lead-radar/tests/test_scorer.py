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


def test_is_broken_rejects_bare_f_number() -> None:
    """F\\d alleen mag niet als kapot-signaal tellen — anders krijgt elke
    Formula 1 / functie-toets / F-150 post valselijk +40 broken_bonus."""
    from consumer.processor.scorer import _is_broken
    assert _is_broken("F1 was een spannende race in Spa") is False
    assert _is_broken("Ik gebruik functietoets F12 om te refreshen") is False
    assert _is_broken("De F-150 truck is mijn favoriet") is False


def test_is_broken_with_context_still_works() -> None:
    """Echte HVAC error-codes met context blijven werken via 'foutmelding'/'error code'."""
    from consumer.processor.scorer import _is_broken
    assert _is_broken("ketel geeft foutmelding F12") is True
    assert _is_broken("error code F8 op cv-ketel") is True
    assert _is_broken("Mijn cv-ketel heeft een storing") is True
    assert _is_broken("warmtepomp werkt niet meer") is True


def test_research_regex_does_not_flag_price_complaints() -> None:
    """'Prijs is niet de moeite waard' is een lead-klacht, geen research.
    Oude pattern 'is .{1,40} de moeite' vuurde valselijk → -25 penalty
    op échte leads die juist klagen over een offerte/prijs."""
    from consumer.processor.scorer import _RE_RESEARCH_ONLY
    assert _RE_RESEARCH_ONLY.search("de prijs is niet de moeite waard") is None
    assert _RE_RESEARCH_ONLY.search("offerte is niet de moeite") is None
    assert _RE_RESEARCH_ONLY.search("dit is niet het beste") is None


def test_research_regex_still_catches_research_phrases() -> None:
    """Echte research-phrasings blijven matchen via specifieke woorden."""
    from consumer.processor.scorer import _RE_RESEARCH_ONLY
    assert _RE_RESEARCH_ONLY.search("overweeg een warmtepomp aan te schaffen") is not None
    assert _RE_RESEARCH_ONLY.search("benieuwd naar de verschillen") is not None
    assert _RE_RESEARCH_ONLY.search("twijfel tussen warmtepomp en cv-ketel") is not None
    assert _RE_RESEARCH_ONLY.search("welk merk warmtepomp is beter") is not None
