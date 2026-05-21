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
    assert intent in {"hot", "warm", "opp", "cold"}


def test_offtopic_penalty_applies() -> None:
    raw = RawPost(
        id="x", source="test", url="https://example.com/x",
        title="Wie kent een fietsenmaker in Amsterdam",
        text="Mijn fiets is kapot, zoek monteur in Amsterdam met spoed.",
    )
    cleaned = clean_post(raw)
    score, breakdown = score_post(cleaned, niche_keywords=["warmtepomp"])
    assert breakdown.get("off_topic_penalty") == -50


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


# === HOT-tier gate (waargenomen 2026-05-15 audit) ===
# Reddit news-artikel over hypotheekrenteaftrek scoorde 80 (zonder
# author_penalty) door soft-signal stacking: location 20 (city in quote) +
# urgency_soft 20 ("deze week") + situation 15 ("woning") + budget 15
# ("kosten") + intent_bonus 10 ("deze week"). Geen hard koop-signal.
#
# Beleid: HOT (>=70) vereist >=1 hard signal —
# urgency_hard (35) / broken_bonus (40) / deadline_bonus (25) /
# offer_received_bonus (20). Anders cap op WARM-high (65).


def _score_for(title: str, text: str, niche: str = "cv") -> tuple[int, dict]:
    raw = RawPost(
        id="x", source="test", url="https://example.com/x",
        title=title, text=text,
    )
    cleaned = clean_post(raw)
    keywords = NICHE_KEYWORDS.get(niche, [niche])
    return score_post(cleaned, niche_keywords=keywords)


def test_hot_tier_gate_caps_pure_soft_signals_to_65() -> None:
    """Stack van soft-signals zonder hard signal mag niet HOT worden."""
    score, breakdown = _score_for(
        title="Renovatie installateur Amsterdam — graag offerte",
        text=(
            "Onze woning in Amsterdam heeft een renovatie nodig. "
            "Wie kent een goede installateur? Budget rond 5000 euro. "
            "Laten plaatsen graag, offerte gevraagd."
        ),
        niche="renovatie",
    )
    assert score <= 65, (
        f"Pure soft-signal stack moet capped worden op 65, kreeg {score}. "
        f"breakdown={breakdown}"
    )
    assert "soft_signals_only_cap" in breakdown, breakdown


def test_hot_tier_gate_allows_hot_with_broken_bonus() -> None:
    """Soft signals + broken_bonus = HOT toegestaan."""
    score, breakdown = _score_for(
        title="CV ketel kapot Amsterdam, monteur nodig",
        text=(
            "Onze cv-ketel is kapot, geen warm water, storing. "
            "Wie kent een goede monteur in Amsterdam? Offerte gewenst."
        ),
        niche="cv",
    )
    assert score >= 70, f"Met broken_bonus moet HOT mogelijk zijn, kreeg {score}"
    assert "soft_signals_only_cap" not in breakdown, breakdown


def test_hot_tier_gate_allows_hot_with_urgency_hard() -> None:
    """Soft signals + urgency_hard = HOT toegestaan."""
    score, breakdown = _score_for(
        title="Warmtepomp installateur Amsterdam, met spoed",
        text=(
            "Ik wil een warmtepomp laten plaatsen in mijn woning. "
            "Met spoed nodig, asap. Budget 8000 euro."
        ),
        niche="warmtepomp",
    )
    assert score >= 70, f"Met urgency_hard moet HOT mogelijk zijn, kreeg {score}"
    assert "soft_signals_only_cap" not in breakdown, breakdown


def test_hot_tier_gate_allows_hot_with_deadline() -> None:
    """Soft signals + deadline_bonus = HOT toegestaan."""
    score, breakdown = _score_for(
        title="Renovatie aannemer Rotterdam binnen 2 weken",
        text=(
            "Wij willen onze woning renoveren in Rotterdam. "
            "Aannemer gezocht die binnen 2 weken kan starten. Budget 15000 euro."
        ),
        niche="renovatie",
    )
    assert score >= 70, f"Met deadline_bonus moet HOT mogelijk zijn, kreeg {score}"
    assert "soft_signals_only_cap" not in breakdown, breakdown


def test_hot_tier_gate_allows_hot_with_offer_received() -> None:
    """Soft signals + offer_received_bonus = HOT toegestaan."""
    score, breakdown = _score_for(
        title="Warmtepomp Eindhoven — andere offerte vergelijken",
        text=(
            "Ik heb al een offerte gehad voor een warmtepomp in Eindhoven. "
            "Wil graag een tweede mening. Installateur gezocht voor offerte."
        ),
        niche="warmtepomp",
    )
    assert score >= 70, f"Met offer_received_bonus moet HOT mogelijk zijn, kreeg {score}"
    assert "soft_signals_only_cap" not in breakdown, breakdown


def test_hot_tier_gate_below_70_unaffected() -> None:
    """Onder 70 punten doet de gate niets — geen cap penalty."""
    score, breakdown = _score_for(
        title="Renovatie woning Brugge",
        text="Wij gaan onze woning renoveren in Brugge. Bouwjaar 1972, 150m2.",
        niche="renovatie",
    )
    assert score < 70
    assert "soft_signals_only_cap" not in breakdown, breakdown
