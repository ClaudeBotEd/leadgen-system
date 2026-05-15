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


# === Renovatie-niche vendor patterns (waargenomen 2026-05-15 daily-run) ===
# 15 vendor-leads scoorden 60-100 (WARM/HOT) op renovatie omdat de vorige
# vendor-patterns vooral spoed/24-7 vocab waren. Renovatie-vendors gebruiken
# scope-claims ("van A tot Z", "Complete Renovaties"), B2C-pitches
# ("voor al uw"), en kwalificatie-claims ("Erkend Elektricien").
@pytest.mark.parametrize("title", [
    # van A tot Z — vendor scope claim
    "Aannemer/Huisrenovatie/ van A tot Z / Whats App",
    "Renovatie van a tot z, scherpe prijs",
    # voor al uw — B2C vendor-pitch
    "Erkend Elektricien voor al uw Elektriciteitswerken",
    "Loodgieter voor al uw lekkages",
    # samenwerking gezocht — B2B partnership ad
    "Ervaren Timmerman Gezocht samenwerking gezocht vakman badkamer",
    # complete/totale renovaties — vendor scope
    "Renova Bouwgroep – Complete Renovaties & Verbouwingen",
    "Totale renovatie van uw woning binnen 2 weken",
    # renovaties regio — vendor service-area phrasing
    "Ervaren Aannemer – Renovaties Regio Den Bosch",
    # erkende/gediplomeerd + role — vendor qualification
    "Gediplomeerd installateur warmtepomp Amsterdam",
    "Gecertificeerde loodgieter regio Utrecht",
    # [role] zoekt [X] — reverse offer (vendor)
    "Vakman zoekt huis te huur – onderhoud mogelijk",
    "Aannemer zoekt projecten in Den Haag",
    # direct/nu beschikbaar — vendor availability claim
    "Aannemer gezocht? Proffesionele bouwteam direct beschikbaar",
    "Klusbedrijf nu beschikbaar voor uw verbouwing",
    # snel geholpen — vendor service-promise
    "Loodgieter Gezocht? Snel geholpen bij storing en renovatie",
    # totaalbouw — vendor scope keyword
    "Aannemer voor verbouwingen, afbouw, aanbouw en totaalbouw",
    # bouwgroep/bouwbedrijf/klusbedrijf — vendor brand pattern
    "Smit Bouwbedrijf voor uw verbouwing",
    "Klusbedrijf Jansen — alle voorkomende werkzaamheden",
])
def test_renovatie_vendor_titles_blocked(title: str) -> None:
    """Renovatie-niche vendor titels moeten hard-block triggeren."""
    post = RawPost(
        id="x", source="marktplaats",
        url="https://www.marktplaats.nl/v/diensten-en-vakmensen/aannemers/x",
        title=title, text="",
    )
    result = check_hardblock(post)
    assert result.blocked, f"Renovatie-vendor niet geblocked: {title!r}"
    assert result.reason and result.reason.startswith("vendor_title:"), result.reason


@pytest.mark.parametrize("title", [
    # Consumer-renovatie posts: legitimate vragen, geen vendor-language
    "Gezocht: aannemer die badkamer kan renoveren",
    "Aannemer gezocht voor verbouwing badkamer in Utrecht",
    "Wie kan helpen met renovatie van mijn keuken?",
    "Tip nodig voor goede aannemer Amsterdam regio",
    "Ik wil mijn badkamer laten renoveren — offerte gezocht",
    "Verbouwing thuis: zoek vakman voor tegelwerk",
])
def test_legitimate_consumer_renovatie_not_blocked(title: str) -> None:
    """Echte renovatie-vragen van consumers mogen NIET door vendor-filter."""
    post = RawPost(
        id="x", source="reddit",
        url="https://reddit.com/r/Klussen/comments/abc/",
        title=title, text="",
    )
    result = check_hardblock(post)
    assert not result.blocked, (
        f"Consumer-renovatie onterecht geblocked: {title!r} "
        f"(reason={result.reason})"
    )


# === Marktplaats/2dehands vendor signals (waargenomen 2026-05-15) ===
# Listings in /diensten-en-vakmensen/ URL-pad zijn betaalde dienst-listings
# door installateurs/aannemers. Body bevat marktplaats "Topadvertentie" /
# "Dagtopper" / "Topzoekertje" tags wanneer de adverteerder voor zichtbaarheid
# heeft betaald — sterk vendor-signaal. Beide checks zijn source-gefilterd
# om Reddit/forum posts die marktplaats noemen NIET te raken.
@pytest.mark.parametrize("url,source", [
    ("https://www.marktplaats.nl/v/diensten-en-vakmensen/aannemers/x", "marktplaats"),
    ("https://www.marktplaats.nl/v/diensten-en-vakmensen/klussers-en-klusbedrijven/x", "marktplaats"),
    ("https://www.marktplaats.nl/v/diensten-en-vakmensen/stukadoors-en-tegelzetters/x", "marktplaats"),
    ("https://www.2dehands.be/v/diensten-en-vakmensen/elektriciens/x", "2dehands"),
])
def test_marktplaats_vendor_url_path_blocked(url: str, source: str) -> None:
    """Marktplaats/2dehands listings in /diensten-en-vakmensen/ pad zijn altijd vendor."""
    post = RawPost(
        id="x", source=source, url=url,
        title="Aannemer Tegelzetter keuken badkamer", text="",
    )
    result = check_hardblock(post)
    assert result.blocked, f"Vendor-pad niet geblocked: {url}"
    assert result.reason and "marktplaats_vendor" in result.reason, result.reason


@pytest.mark.parametrize("body_text", [
    "Renovatie tegen scherpe prijs Topadvertentie",
    "Bouw van a tot z Dagtopper",
    "Elektriciteitswerken op maat Topzoekertje",
])
def test_marktplaats_promo_tag_blocked(body_text: str) -> None:
    """Marktplaats paid-promotion tags in body zijn vendor-signaal."""
    post = RawPost(
        id="x", source="marktplaats",
        url="https://www.marktplaats.nl/v/huis-en-inrichting/badkamer-badtextiel/x",
        title="Aannemer Tegelzetter keuken badkamer loodgieter", text=body_text,
    )
    result = check_hardblock(post)
    assert result.blocked, f"Promo-tag niet geblocked: {body_text!r}"
    assert result.reason and "marktplaats_promo" in result.reason, result.reason


@pytest.mark.parametrize("url,source,text", [
    # Consumer-categorie: badkamer renovatie vraag
    ("https://www.marktplaats.nl/v/huis-en-inrichting/badkamer-complete-badkamers/m123-aannemer-gezocht",
     "marktplaats", "Aannemer gezocht voor renovatie badkamer"),
    # Reddit-post met Topadvertentie in tekst (bv. iemand klaagt over marktplaats) — NIET blokken
    ("https://reddit.com/r/Klussen/comments/abc/",
     "reddit", "Heeft iemand ervaring met die Topadvertentie ads op marktplaats?"),
    # Bouwinfo-forum (geen marktplaats source) — pad-check moet niet fire
    ("https://www.bouwinfo.be/bouwforum/threads/12345/diensten-en-vakmensen-tip",
     "bouwinfo_forum", "Tip voor aannemer in regio"),
])
def test_marktplaats_signals_not_blocked_other_sources(url: str, source: str, text: str) -> None:
    """URL-pad en body-tags fire alleen op marktplaats/2dehands source."""
    post = RawPost(
        id="x", source=source, url=url,
        title="Renovatie hulp gezocht", text=text,
    )
    result = check_hardblock(post)
    assert not result.blocked, (
        f"Onterecht geblocked op marktplaats-signaal: source={source} url={url} "
        f"text={text!r} (reason={result.reason})"
    )
