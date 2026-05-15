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


# === Vendor-offering body patterns (waargenomen 2026-05-15 cv-niche) ===
# 4 vendor-leads in cv-niche scoorden 60-100 ondanks dat ze niet in
# /diensten-en-vakmensen/ pad staan en geen promo-tag in body hebben.
# Wat hen wel verraadt: classiek vendor-jargon in body-text.
# Body-only check (source-agnostisch) — vendor language is universeel.
@pytest.mark.parametrize("body_text", [
    # Row 5 cv CSV: "Cv monteur beschikbaar in rotterdam en omgeving"
    "Cv monteur beschikbaar in rotterdam en omgeving. Werkzaamheden: cv installatie.",
    "Vakman werkzaam in regio Den Haag, bel voor afspraak.",
    # Row 14 cv CSV: "Beste lezer, leuk dat u op mijn advertentie terecht bent gekomen"
    "Beste lezer, leuk dat u op mijn advertentie terecht bent gekomen!",
    # Row 16 cv CSV: "bent u bij mij aan het juiste adres"
    "Met ervaring in het plaatsen, bent u bij mij aan het juiste adres.",
    "Bij ons bent u aan het juiste adres voor al uw klussen.",
    # Row 21 cv CSV: "S.j.s technicus staat voor u klaar"
    "S.j.s technicus staat voor u klaar voor onderhoud aan uw cv.",
    "Wij staan voor u klaar dag en nacht.",
    # Vendor corporate self-id
    "Wij zijn gespecialiseerd in cv-ketels en warmtepompen.",
    "Wij zijn uw installatiebedrijf in regio Amsterdam.",
    # Vendor catchphrases
    "Wij verzorgen al uw installatiewerk van A tot Z.",
    "Wij bieden complete renovaties tegen scherpe prijs.",
    "Onze diensten omvatten cv-installatie en onderhoud.",
    "Onze klanten waarderen onze betrouwbaarheid.",
    # Vendor scope
    "Voor alle voorkomende werkzaamheden in en om uw huis.",
    "Wij doen alle voorkomende klussen netjes en betaalbaar.",
    # "We" naast "Wij" — informele vorm (renovatie Row 17 echte CSV body)
    "We zijn een aannemersbedrijf in de buurt van arnhem, gespecialiseerd in verbouw en renovatie.",
    "We bieden complete renovaties tegen scherpe prijs.",
    "We staan voor u klaar dag en nacht.",
    "We verzorgen alle voorkomende werkzaamheden.",
])
def test_vendor_offering_body_blocked(body_text: str) -> None:
    """Vendor-offering body-language is altijd vendor — geen consumer."""
    post = RawPost(
        id="x", source="marktplaats",
        url="https://www.marktplaats.nl/v/doe-het-zelf-en-verbouw/verwarming-en-radiatoren/x",
        title="CV onderhoud advertentie", text=body_text,
    )
    result = check_hardblock(post)
    assert result.blocked, f"Vendor-offering body niet geblocked: {body_text!r}"
    assert result.reason and result.reason.startswith("vendor_offering:"), result.reason


@pytest.mark.parametrize("body_text", [
    # Row 9 renovatie CSV: legit consumer
    "Gezocht betrouwbare vakman huis schilder voor de maand juli of augustus. "
    "Kleine klus: paar wanden en wat lichte renovatie binnen.",
    # Row 11 renovatie CSV: legit consumer
    "Ik ben momenteel op zoek naar een aannemer voor de verbouwing van mijn badkamer. "
    "Omgeving gouda/alphen ad rijn.",
    # Consumer met installateur-vraag
    "CV ketel kapot, wie kan helpen? Heb hulp nodig met installateur in Amsterdam.",
    "Wij willen onze warmtepomp laten installeren. Heeft iemand een tip voor een goede vakman?",
    # Consumer noemt 'ervaring' zonder vendor te zijn (research-penalty is apart)
    "Iemand ervaring met Daikin warmtepomp? Wij overwegen er een te kopen.",
])
def test_consumer_body_not_blocked_by_offering_filter(body_text: str) -> None:
    """Consumer bodies mogen niet door vendor-offering filter geraakt worden."""
    post = RawPost(
        id="x", source="reddit",
        url="https://reddit.com/r/Klussen/comments/abc/",
        title="Hulp gezocht", text=body_text,
    )
    result = check_hardblock(post)
    assert not result.blocked, (
        f"Consumer body onterecht geblocked: {body_text!r} (reason={result.reason})"
    )


# === Vendor leaks waargenomen 2026-05-15 daily-run ===
# Vier vendors scoorden 50-100 (HOT) in productieoutput omdat ze patterns
# gebruikten die niet door bestaande hardblock-rules werden gevangen.
@pytest.mark.parametrize("title", [
    # Vendor rhetorical question: "Is u [device] kapot/stuk/defect?"
    "Cv instalatie monteur spoed Is u cv ketel kapot",
    "Is uw ketel kapot? Bel ons direct",
    "Loodgieter nodig? Is uw afvoer verstopt?",
    # Emoji + vendor role marketing (🔥 / ⭐ / ✅)
    "Installateur🔥 installateur nodig in haaksbergen",
    "🔥 Vakman renovatie ✅ scherpe prijs",
    "⭐ Erkend cv-monteur beschikbaar ⭐",
    # Vendor CTA: "[role] nodig, bericht/reactie/mail"
    "Lekkage? Loodgieter nodig, bericht!",
    "Cv ketel kapot? Monteur nodig, bericht ons",
    "Aannemer nodig? Reactie via WhatsApp",
])
def test_vendor_leak_patterns_blocked(title: str) -> None:
    """Vendor titels die op 2026-05-15 door hardblock glipten."""
    post = RawPost(
        id="x", source="marktplaats",
        url="https://www.marktplaats.nl/v/test",
        title=title, text="",
    )
    result = check_hardblock(post)
    assert result.blocked, f"Vendor-leak titel niet geblocked: {title!r}"


@pytest.mark.parametrize("title", [
    # Vendor self-offering in TITLE (body patterns moeten ook title checken)
    "CV monteur – installatie, radiator en lekkage Cv monteur beschikbaar in rotterdam",
    "Loodgieter beschikbaar in regio Amsterdam voor spoedklussen",
    "Wij verzorgen complete badkamerrenovaties voor scherpe prijs",
])
def test_vendor_offering_in_title_blocked(title: str) -> None:
    """Vendor-offering patterns in TITEL (niet alleen body) moeten geblocked."""
    post = RawPost(
        id="x", source="marktplaats",
        url="https://www.marktplaats.nl/v/test",
        title=title, text="",
    )
    result = check_hardblock(post)
    assert result.blocked, f"Vendor-offering in titel niet geblocked: {title!r}"


@pytest.mark.parametrize("title", [
    # Consumer "is X kapot?" naar zichzelf-publiek toe (forum context)
    "Mijn cv ketel is kapot, wie kan helpen?",
    "CV ketel kapot — wat moet ik doen?",
    # Consumer noemt installateur "nodig" zonder bericht-CTA
    "Installateur nodig in Amsterdam voor warmtepomp",
    # Emoji in consumer post — moet niet automatisch blokkeren
    "🙏 Hulp gezocht: warmtepomp advies",
])
def test_vendor_leak_patterns_no_false_positives(title: str) -> None:
    """De nieuwe vendor-leak patterns mogen consumer-vragen niet raken."""
    post = RawPost(
        id="x", source="reddit",
        url="https://reddit.com/r/Klussen/comments/abc/",
        title=title, text="",
    )
    result = check_hardblock(post)
    assert not result.blocked, (
        f"Consumer-titel onterecht geblocked: {title!r} (reason={result.reason})"
    )
