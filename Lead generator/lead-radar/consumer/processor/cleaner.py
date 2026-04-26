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
