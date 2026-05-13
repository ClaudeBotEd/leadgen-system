"""Cleaner — normaliseert HTML/whitespace en extraheert summary + city.

Geen heavy NLP — gewoon regex en woordenlijsten zodat alles offline werkt
zonder paid API of model download.
"""
from __future__ import annotations

import html
import re
import unicodedata

from .. import RawPost

NL_CITIES = {
    "amsterdam", "rotterdam", "den haag", "'s-gravenhage", "the hague",
    "utrecht", "eindhoven", "groningen", "tilburg", "almere", "breda",
    "nijmegen", "apeldoorn", "haarlem", "arnhem", "zaanstad", "amersfoort",
    "haarlemmermeer", "den bosch", "'s-hertogenbosch", "zwolle", "leiden",
    "zoetermeer", "leeuwarden", "maastricht", "dordrecht", "ede", "alphen",
    "westland", "alkmaar", "delft", "venlo", "deventer", "helmond", "oss",
    "amstelveen", "hilversum", "heerlen", "purmerend", "roosendaal", "schiedam",
    "spijkenisse", "vlaardingen", "almelo", "gouda", "lelystad", "hoorn",
    "veenendaal", "hengelo", "katwijk", "nieuwegein", "emmen", "kampen",
    "doetinchem", "ridderkerk", "barneveld", "oosterhout", "rijswijk",
    "tiel", "harderwijk",
}
BE_CITIES = {
    "antwerpen", "antwerp", "gent", "ghent", "brugge", "bruges", "leuven",
    "louvain", "mechelen", "hasselt", "kortrijk", "oostende", "ostend",
    "aalst", "sint-niklaas", "brussel", "brussels", "bruxelles", "namur",
    "namen", "luik", "liege", "liège", "charleroi", "doornik", "tournai",
    "genk", "roeselare", "vilvoorde", "ieper", "ypres", "turnhout", "lier",
    "geel", "tienen", "halle", "deinze", "lokeren", "aarschot", "heist",
    "bilzen", "tongeren", "diest", "waregem", "izegem", "menen", "wevelgem",
    "harelbeke", "diepenbeek", "geraardsbergen", "ronse", "zottegem",
    "ninove", "dendermonde", "beveren", "temse", "merksem", "deurne",
    "berchem", "borgerhout",
}
ALL_CITIES = NL_CITIES | BE_CITIES

RE_POSTCODE_NL = re.compile(r"\b\d{4}\s?[A-Z]{2}\b", re.IGNORECASE)
RE_POSTCODE_BE = re.compile(r"\b[1-9]\d{3}\b")
RE_URL = re.compile(r"https?://\S+")
RE_WHITESPACE = re.compile(r"\s+")
RE_HTML_TAG = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    if not text:
        return ""
    no_tags = RE_HTML_TAG.sub(" ", text)
    decoded = html.unescape(no_tags)
    return decoded


RE_CAMELSPLIT = re.compile(r"([a-z])([A-Z])")


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    # Marktplaats e.d. zetten title+description vaak smushed naast elkaar
    # ("monteurZoekt u").  Split CamelCase boundaries terug uit elkaar
    # zodat regex en woord-detectie blijft werken.
    decamel = RE_CAMELSPLIT.sub(r"\1 \2", text)
    return RE_WHITESPACE.sub(" ", decamel).strip()


def normalize_unicode(text: str) -> str:
    """Normaliseer accenten zodat 'Liège' en 'Liege' beide matchen."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def detect_city(text: str) -> str | None:
    """Vind een NL/BE-stad in de tekst — eerste match wint."""
    if not text:
        return None
    flat = normalize_unicode(text).lower()
    for city in sorted(ALL_CITIES, key=len, reverse=True):
        idx = flat.find(city)
        if idx == -1:
            continue
        before_ok = idx == 0 or not flat[idx - 1].isalpha()
        end = idx + len(city)
        after_ok = end == len(flat) or not flat[end].isalpha()
        if before_ok and after_ok:
            return city
    if RE_POSTCODE_NL.search(text):
        return "nl-postcode"
    if RE_POSTCODE_BE.search(text):
        return "be-postcode"
    return None


# Stad → provincie mapping (NL + BE).  Onbekende stad → None.
_CITY_TO_PROVINCE: dict[str, str] = {
    # --- Noord-Holland
    **{c: "Noord-Holland" for c in (
        "amsterdam", "haarlem", "alkmaar", "zaanstad", "amstelveen",
        "haarlemmermeer", "hoorn", "purmerend", "hilversum",
    )},
    # --- Zuid-Holland
    **{c: "Zuid-Holland" for c in (
        "rotterdam", "den haag", "'s-gravenhage", "the hague", "leiden",
        "dordrecht", "zoetermeer", "alphen", "delft", "gouda", "schiedam",
        "vlaardingen", "spijkenisse", "ridderkerk", "rijswijk", "westland",
        "katwijk",
    )},
    # --- Utrecht
    **{c: "Utrecht" for c in (
        "utrecht", "amersfoort", "nieuwegein", "veenendaal",
    )},
    # --- Noord-Brabant
    **{c: "Noord-Brabant" for c in (
        "eindhoven", "tilburg", "breda", "helmond", "oss",
        "den bosch", "'s-hertogenbosch", "oosterhout", "roosendaal",
    )},
    # --- Gelderland
    **{c: "Gelderland" for c in (
        "nijmegen", "arnhem", "apeldoorn", "ede", "doetinchem",
        "harderwijk", "barneveld", "tiel",
    )},
    # --- Overijssel
    **{c: "Overijssel" for c in (
        "zwolle", "almelo", "hengelo", "deventer", "kampen",
    )},
    # --- Groningen
    "groningen": "Groningen",
    # --- Friesland
    "leeuwarden": "Friesland",
    # --- Drenthe
    "emmen": "Drenthe",
    # --- Flevoland
    **{c: "Flevoland" for c in ("almere", "lelystad")},
    # --- Limburg (NL)
    **{c: "Limburg (NL)" for c in ("maastricht", "venlo", "heerlen")},

    # --- BE: Antwerpen
    **{c: "Antwerpen" for c in (
        "antwerpen", "antwerp", "mechelen", "lier", "turnhout", "geel",
        "merksem", "deurne", "berchem", "borgerhout",
    )},
    # --- BE: Vlaams-Brabant
    **{c: "Vlaams-Brabant" for c in (
        "leuven", "louvain", "vilvoorde", "halle", "diest", "tienen",
        "aarschot",
    )},
    # --- BE: Limburg (BE)
    **{c: "Limburg (BE)" for c in (
        "hasselt", "genk", "bilzen", "tongeren", "diepenbeek",
    )},
    # --- BE: Oost-Vlaanderen
    **{c: "Oost-Vlaanderen" for c in (
        "gent", "ghent", "aalst", "sint-niklaas", "dendermonde", "lokeren",
        "geraardsbergen", "ronse", "zottegem", "ninove", "deinze",
        "beveren", "temse",
    )},
    # --- BE: West-Vlaanderen
    **{c: "West-Vlaanderen" for c in (
        "brugge", "bruges", "kortrijk", "oostende", "ostend", "roeselare",
        "ieper", "ypres", "izegem", "menen", "wevelgem", "harelbeke",
        "waregem",
    )},
    # --- BE: Henegouwen / Luik / Namen / Brussel
    **{c: "Henegouwen" for c in ("charleroi", "doornik", "tournai")},
    **{c: "Luik" for c in ("luik", "liege", "liège")},
    **{c: "Namen" for c in ("namur", "namen")},
    **{c: "Brussel" for c in ("brussel", "brussels", "bruxelles")},
}


def detect_province(city: str | None) -> str | None:
    """Map een stad (lowercase) naar provincie.  Onbekend = None."""
    if not city:
        return None
    if city == "nl-postcode":
        return "NL (postcode)"
    if city == "be-postcode":
        return "BE (postcode)"
    return _CITY_TO_PROVINCE.get(city.strip().lower())


def make_summary(text: str, max_chars: int = 220) -> str:
    if not text:
        return ""
    flat = normalize_whitespace(text)
    if len(flat) <= max_chars:
        return flat
    cut = flat[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars * 0.6:
        cut = cut[:last_space]
    return cut.rstrip(" ,.;:") + "…"


_NICHE_LABEL = {
    "warmtepomp": "warmtepomp",
    "airco": "airco",
    "zonnepanelen": "zonnepanelen",
    "cv": "cv-ketel",
    "renovatie": "renovatie",
}

_URGENCY_RX = re.compile(
    r"\b(z\.?s\.?m\.?|asap|spoed|dringend|haast|"
    r"deze week|deze maand|binnenkort|vandaag|morgen|volgende week|"
    r"met spoed|snel mogelijk)\b",
    re.IGNORECASE,
)


def has_urgency(text: str) -> bool:
    return bool(_URGENCY_RX.search(text or ""))


def smart_summary(*, text: str, title: str, city: str | None, niche: str) -> str:
    """1 korte zin in simpel Nederlands die direct duidelijk maakt wat iemand wil.

    Voorbeelden:
      - "Zoekt installateur voor warmtepomp in Utrecht, wil snel beginnen"
      - "Wil offerte voor airco in Amsterdam"
      - "Heeft probleem met cv-ketel"
    """
    full = f"{title} {text}".lower()

    if any(w in full for w in ("kapot", "stuk", "defect", "storing", "werkt niet", "lekkage", "lekt")):
        verb = "Heeft probleem met"
    elif any(w in full for w in ("offerte", "prijsopgave", "kostenraming", "aanbieding", "wat kost", "prijs voor")):
        verb = "Wil offerte voor"
    elif any(w in full for w in (
        "zoek installateur", "zoek monteur", "zoek vakman", "wie kan", "wie heeft",
        "iemand een", "iemand tip", "tip voor", "tip nodig", "tips voor",
        "installateur gezocht", "monteur gezocht", "vakman gezocht",
    )) or " installateur " in f" {full} " or " monteur " in f" {full} ":
        verb = "Zoekt installateur voor"
    elif any(w in full for w in ("advies", "advice", "tips", "aanrader", "aanraden", "raden", "welke kiezen")):
        verb = "Zoekt advies over"
    elif any(w in full for w in ("vervangen", "nieuwe", "laten plaatsen", "aanleggen", "laten installeren")):
        verb = "Wil"
    else:
        verb = "Geïnteresseerd in"

    label = _NICHE_LABEL.get((niche or "").lower(), (niche or "installatie"))

    loc = ""
    if city:
        if city == "nl-postcode":
            loc = " (NL)"
        elif city == "be-postcode":
            loc = " (BE)"
        else:
            loc = f" in {city.title()}"

    suffix = ""
    if has_urgency(full):
        suffix = ", wil snel beginnen"

    sentence = f"{verb} {label}{loc}{suffix}".strip()
    # Cap zacht op 140 tekens
    if len(sentence) > 140:
        sentence = sentence[:139].rstrip(" ,.;:") + "…"
    return sentence


def clean_post(post: RawPost) -> dict:
    """Run alle cleaners en geef structuur klaar voor scoring."""
    clean_title = normalize_whitespace(strip_html(post.title))
    clean_text = normalize_whitespace(strip_html(post.text))
    full = f"{clean_title}\n\n{clean_text}".strip()
    full_no_url = RE_URL.sub("", full)
    return {
        "title": clean_title,
        "text": clean_text,
        "full": full,
        "full_no_url": full_no_url,
        "lower": normalize_unicode(full).lower(),
        "city": detect_city(full),
        "summary": make_summary(clean_text or clean_title),
    }


# Niche → vakman + (optioneel) installatie-werkwoord voor outreach.
_NICHE_PRO = {
    "warmtepomp":   ("installateur", "warmtepomp"),
    "airco":        ("installateur", "airco"),
    "zonnepanelen": ("installateur", "zonnepanelen"),
    "cv":           ("cv-monteur", "cv-ketel"),
    "renovatie":    ("aannemer", "renovatie"),
}


def _detect_intent_for_message(full_lower: str) -> str:
    """Pak het overheersende intent-signaal voor de outreach-tone."""
    if any(w in full_lower for w in (
        "kapot", "stuk", "defect", "storing", "werkt niet",
        "lekkage", "lekt", "doet het niet", "geen warm water",
    )):
        return "broken"
    if any(w in full_lower for w in (
        "offerte gehad", "al een offerte", "al offertes",
        "andere offertes", "offertes vergelijken", "ik heb een offerte",
    )):
        return "comparing"
    if any(w in full_lower for w in (
        "offerte", "prijsopgave", "kostenraming", "wat kost", "prijs voor",
    )):
        return "quote"
    if any(w in full_lower for w in (
        "zsm", "spoed", "dringend", "deze week", "binnen ",
        "snel mogelijk", "vandaag", "morgen",
    )):
        return "urgent"
    return "default"


def generate_message(
    *,
    niche: str,
    city: str | None,
    text: str = "",
    title: str = "",
) -> str:
    """Genereer een kort NL outreach-bericht (2-3 zinnen, human tone).

    Voorbeeld:
      "Hoi, ik zag dat je een warmtepomp installateur zoekt in Utrecht.
       Ik werk met installateurs die daar nog plek hebben. Zal ik je koppelen?"
    """
    pro, label = _NICHE_PRO.get((niche or "").lower(), ("installateur", niche or "installatie"))
    full_lower = f"{title} {text}".lower()
    intent = _detect_intent_for_message(full_lower)

    if city and city not in ("nl-postcode", "be-postcode"):
        in_city = f" in {city.title()}"
        there = " daar"
    elif city == "nl-postcode":
        in_city = " (NL)"
        there = ""
    elif city == "be-postcode":
        in_city = " (BE)"
        there = ""
    else:
        in_city = ""
        there = ""

    # Kort en direct: 2 zinnen.  Geen "Ik werk met..."-tussenzin.
    # CTA is een concrete ja/nee-vraag.
    if intent == "broken" and niche in ("warmtepomp", "airco", "cv"):
        equip = {"warmtepomp": "warmtepomp", "airco": "airco", "cv": "cv-ketel"}[niche]
        hook = f"Hoi, las dat je {equip} kapot is{in_city}."
        cta = "Heb een monteur die snel kan — zal ik 'm doorsturen?"
    elif intent == "comparing":
        hook = f"Hoi, las dat je offertes vergelijkt voor {label}{in_city}."
        cta = "Heb een scherpe partij — prijs erbij?"
    elif intent == "quote":
        hook = f"Hoi, las dat je een offerte zoekt voor {label}{in_city}."
        cta = "Kan er 1-2 voor je opvragen — akkoord?"
    elif intent == "urgent":
        hook = f"Hoi, las dat je snel een {pro} zoekt voor {label}{in_city}."
        cta = "Heb iemand die deze week nog kan — interesse?"
    else:
        hook = f"Hoi, las je vraag over {label}{in_city}."
        cta = f"Ik ken een goede {pro}{there} — interesse?"

    return f"{hook} {cta}"
