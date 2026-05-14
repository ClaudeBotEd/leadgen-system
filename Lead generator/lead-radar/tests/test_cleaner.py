"""Regression-tests voor cleaner: city/province detection, summary, message generation."""
from __future__ import annotations

import pytest

from consumer import RawPost
from consumer.processor.cleaner import (
    clean_post,
    detect_city,
    detect_province,
    generate_message,
    make_summary,
    normalize_unicode,
    smart_summary,
    strip_html,
)


def test_strip_html_removes_tags_and_decodes_entities() -> None:
    out = strip_html("Hoi <b>Jan</b>, dit kost &euro;500 &amp; meer")
    assert "<b>" not in out
    assert "Jan" in out
    assert "&amp;" not in out


def test_normalize_unicode_strips_accents() -> None:
    assert normalize_unicode("Liège") == "Liege"


def test_detect_city_exact_match() -> None:
    assert detect_city("Ik zoek monteur in Utrecht") == "utrecht"
    assert detect_city("Wonen in Antwerpen") == "antwerpen"


def test_detect_city_word_boundary() -> None:
    assert detect_city("Edelste kunstenaar Nederland") is None


def test_detect_city_postcode_fallback() -> None:
    assert detect_city("Mijn adres is 1234 AB") == "nl-postcode"
    assert detect_city("BE postcode 2000") == "be-postcode"


def test_detect_city_returns_none_when_no_match() -> None:
    assert detect_city("Geen stad in deze tekst") is None
    assert detect_city("") is None


@pytest.mark.parametrize("city,expected_province", [
    ("amsterdam", "Noord-Holland"),
    ("rotterdam", "Zuid-Holland"),
    ("eindhoven", "Noord-Brabant"),
    ("antwerpen", "Antwerpen"),
    ("gent", "Oost-Vlaanderen"),
    ("brugge", "West-Vlaanderen"),
    ("hasselt", "Limburg (BE)"),
    ("brussel", "Brussel"),
    ("nl-postcode", "NL (postcode)"),
    ("be-postcode", "BE (postcode)"),
])
def test_detect_province_known(city: str, expected_province: str) -> None:
    assert detect_province(city) == expected_province


def test_detect_province_unknown() -> None:
    assert detect_province("dorpje-x") is None
    assert detect_province(None) is None


def test_make_summary_truncates() -> None:
    long = "Dit is een hele lange tekst " * 30
    out = make_summary(long, max_chars=100)
    assert len(out) <= 101
    assert out.endswith("…")


def test_make_summary_short_unchanged() -> None:
    assert make_summary("kort", max_chars=100) == "kort"


def test_smart_summary_broken() -> None:
    s = smart_summary(text="Mijn cv-ketel is kapot", title="", city="utrecht", niche="cv")
    assert "probleem" in s.lower() or "kapot" in s.lower()
    assert "Utrecht" in s


def test_smart_summary_quote() -> None:
    s = smart_summary(text="Offerte gewenst voor airco", title="", city="leuven", niche="airco")
    assert "offerte" in s.lower()


def test_generate_message_broken_cv() -> None:
    msg = generate_message(
        niche="cv", city="utrecht",
        text="cv-ketel is kapot", title="CV kapot Utrecht",
    )
    assert "Utrecht" in msg
    assert any(w in msg.lower() for w in ("kapot", "monteur", "doorsturen"))


def test_generate_message_quote_intent() -> None:
    msg = generate_message(
        niche="warmtepomp", city="amsterdam",
        text="offerte zoeken", title="Wie maakt offerte",
    )
    assert "Amsterdam" in msg


def test_generate_message_no_city() -> None:
    msg = generate_message(niche="airco", city=None, text="iets", title="ietsje")
    assert msg.startswith("Hoi")
    assert "None" not in msg
    assert "undefined" not in msg.lower()


def test_clean_post_extracts_city_from_title() -> None:
    raw = RawPost(
        id="x", source="test", url="https://e.x",
        title="Zoek installateur Utrecht",
        text="extra info",
    )
    cleaned = clean_post(raw)
    assert cleaned["city"] == "utrecht"
    assert cleaned["full"]
    assert cleaned["summary"]


def test_clean_post_html_tags_stripped() -> None:
    raw = RawPost(
        id="x", source="test", url="https://e.x",
        title="<b>CV kapot</b>",
        text="<p>Mijn ketel is <i>defect</i></p>",
    )
    cleaned = clean_post(raw)
    assert "<b>" not in cleaned["title"]
    assert "<p>" not in cleaned["text"]
