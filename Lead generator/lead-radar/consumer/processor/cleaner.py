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


def normalize_whitespace(text: str) -> str:
    return RE_WHITESPACE.sub(" ", text or "").strip()


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
