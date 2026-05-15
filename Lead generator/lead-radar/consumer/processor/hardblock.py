"""Hard-block filter — vroege exits voor posts die NOOIT een lead kunnen zijn.

Wordt direct na fetch + dedup gedraaid, vóór cleaning/classifying/scoring.
Voorbeelden:
- Lead-aggregators (Slimster/Werkspot/Bobex) die "tip nodig"-posts plaatsen
- Recruiters/bureau-advertenties die job ads als lead vermomd plaatsen
- Bedrijfsaccounts van installateurs die zelf vragen stellen (eigen marketing)
- Bot-/spam-patronen

Geeft (blocked: bool, reason: str | None) terug. Reason is voor logging/audit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .. import RawPost

# URL/host-patterns voor lead-aggregators (DIRECTE CONCURRENTEN).  Een post
# vanuit deze domeinen is geen consumer-lead — we pitchen ze niet en we
# verwerken hun listings niet.
AGGREGATOR_HOSTS: frozenset[str] = frozenset({
    "slimster.nl", "slimster.com",
    "bobex.nl", "bobex.be", "bobex.com",
    "trustoo.nl",
    "solvari.nl", "solvari.com",
    "werkspot.nl", "werkspot.com",
    "offerteadviseur.nl", "offerte-vergelijker.nl",
    "offerte.nl", "offertes.nl", "bouwoffertes.nl",
    "casius.nl", "moving.nl", "homedeal.nl",
    "warmtepompgids.nl", "warmtepomp.nu", "warmtepompplek.nl",
    "warmtepompspot.nl", "warmtepomprevolutie.nl",
    "warmtepompaanbieders.nl", "warmtepompnederland.nl",
    "warmtepompamsterdam.com", "warmtepompamsterdam.nl",
    "warmtepomp-amsterdam.com", "warmtepomp-info.nl",
    "warmtepompbedrijf.nl",
    "warmgarant.nl", "warmplus.nl", "zenovo.nl",
})

# Hard-block op auteur-namen die typisch corporate/bot zijn.  Lowercase.
BLOCKED_AUTHOR_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(
        r"^(admin|moderator|automoderator|automod|bot|systeem|system|"
        r"removalbot|reposterbot|mod[\-_]bot)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(installateur|installatie|verwarming|monteurs?|hvac|loodgieter)\b"
        r".*\b(bv|bvba|nv|gmbh|bedrijf)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(marketing|reclame|advertising|sales)\b", re.IGNORECASE),
)

# Titel/text patterns die ALTIJD spam/promo zijn — geen verdere processing.
HARD_PROMO_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(
        r"\b(verdien online|geld verdienen vanuit huis|crypto|forex|"
        r"online casino|betting|gokken)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(escort|massage|adult|18\+|seks|porno)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(daikin|mitsubishi|panasonic|lg|samsung|bosch|atag|"
        r"nefit|remeha|vaillant|stiebel|viessmann|intergas)\s+"
        r"(nederland|belgië|belgium|nv|bv)\b",
        re.IGNORECASE,
    ),
)

# Vendor-title patterns — service-aanbieders die zichzelf adverteren als
# "24/7 spoed monteur" of met telefoonnummer in titel.  Deze patronen
# komen niet voor in echte consumer-vragen ("CV ketel kapot, wie kan helpen?")
# maar wel in marktplaats/2dehands listings van installateurs.
#
# Belangrijk: alleen op de TITEL toepassen, niet op text — consumers
# kunnen "24/7 nodig" in body schrijven zonder vendor te zijn.
VENDOR_TITLE_PATTERNS: tuple[re.Pattern, ...] = (
    # 24/7 / 24-7 / 24x7 / 24/7 bereikbaar — vendor uptime claim
    re.compile(r"\b24\s*[/x\-]\s*7\b", re.IGNORECASE),
    # "snel ter plaats(e)" — vendor service-belofte
    re.compile(r"\bsnel ter plaats(e)?\b", re.IGNORECASE),
    # "spoedmonteur" / "spoed monteur" — meestal aanbod, niet vraag
    re.compile(r"\bspoed[\s-]?monteur\b", re.IGNORECASE),
    # "Bel ons/direct/nu" / "Whatsapp ons" — direct contact-CTA
    re.compile(r"\b(bel|whatsapp|mail)\s+(ons|direct|nu|naar)\b", re.IGNORECASE),
    # "Bel direct …" of "Direct bellen"
    re.compile(r"\b(direct bellen|bel direct|nu bellen)\b", re.IGNORECASE),
    # Telefoonnummer in titel: NL mobiel (06-XXXXXXXX) of vast (0XX-XXXXXXX)
    re.compile(r"\b0[1-9]\d?[\s\-]?\d{6,8}\b"),
    # === Renovatie-niche vendor patterns (toegevoegd 2026-05-15) ===
    # "van A tot Z" — vendor scope-claim, nooit consumer
    re.compile(r"\bvan\s+a\s+tot\s+z\b", re.IGNORECASE),
    # "voor al uw [X]" — klassieke B2C vendor-pitch
    re.compile(r"\bvoor\s+al\s+uw\b", re.IGNORECASE),
    # B2B partnership ad
    re.compile(r"\bsamenwerking\s+gezocht\b", re.IGNORECASE),
    # "Complete Renovaties" / "Totale verbouwingen" — vendor scope
    re.compile(r"\b(complete|totale)\s+(renovaties?|verbouwingen?)\b", re.IGNORECASE),
    # "Renovaties Regio Den Bosch" — vendor service-area phrasing
    re.compile(r"\brenovaties?\s+regio\b", re.IGNORECASE),
    # Vendor qualification: "Erkend/Gediplomeerd/Gecertificeerd + role"
    re.compile(
        r"\b(erkend(?:e)?|gediplomeerd(?:e)?|gecertificeerd(?:e)?)\s+"
        r"(aannemer|vakman|elektricien|elektriciens|loodgieter|installateur|"
        r"monteur|stukadoor|tegelzetter|timmerman|hovenier|metselaar|"
        r"dakdekker|stratenmaker|schilder)\b",
        re.IGNORECASE,
    ),
    # "[role] zoekt [X]" — reverse offer (vendor biedt diensten aan)
    re.compile(
        r"\b(vakman|aannemer|monteur|stukadoor|tegelzetter|loodgieter|"
        r"installateur|elektricien|klusbedrijf)\s+zoekt\b",
        re.IGNORECASE,
    ),
    # Vendor availability claim: "direct/nu/meteen beschikbaar"
    re.compile(r"\b(direct|nu|meteen)\s+beschikbaar\b", re.IGNORECASE),
    # Vendor service-promise: "snel geholpen"
    re.compile(r"\bsnel\s+geholpen\b", re.IGNORECASE),
    # Vendor scope keyword: "totaalbouw"
    re.compile(r"\btotaalbouw\b", re.IGNORECASE),
    # Vendor brand-pattern: "X Bouwgroep / Bouwbedrijf / Klusbedrijf"
    re.compile(r"\b(bouwgroep|bouwbedrijf|klusbedrijf)\b", re.IGNORECASE),
)


def _check_vendor_title(title: str) -> tuple[bool, str | None]:
    """True als titel een vendor-promo pattern bevat.  Alleen titel-tekst —
    body kan vrijuit dezelfde woorden gebruiken zonder vendor te zijn."""
    if not title:
        return False, None
    for pat in VENDOR_TITLE_PATTERNS:
        if pat.search(title):
            return True, f"vendor_title:{pat.pattern[:40]}"
    return False, None


# === Marktplaats/2dehands vendor signals ===
# Listings in /diensten-en-vakmensen/ pad zijn betaalde dienst-listings door
# installateurs/aannemers — geen consumer-leads.  Body-tags
# "Topadvertentie/Dagtopper/Topzoekertje" zijn paid-promotion markers
# afkomstig van de listing-UI (door scraper meegenomen in text).
MARKTPLAATS_SOURCES: frozenset[str] = frozenset({"marktplaats", "2dehands"})
MARKTPLAATS_VENDOR_PATH_RE = re.compile(r"/diensten-en-vakmensen/", re.IGNORECASE)
MARKTPLAATS_PROMO_TAG_RE = re.compile(
    r"\b(Topadvertentie|Dagtopper|Topzoekertje)\b",
)


def _check_marktplaats_vendor(post: "RawPost") -> tuple[bool, str | None]:
    """Marktplaats/2dehands-specifieke vendor-signalen op URL-pad en body."""
    if post.source not in MARKTPLAATS_SOURCES:
        return False, None
    if post.url and MARKTPLAATS_VENDOR_PATH_RE.search(post.url):
        return True, "marktplaats_vendor_path:/diensten-en-vakmensen/"
    if post.text and MARKTPLAATS_PROMO_TAG_RE.search(post.text):
        m = MARKTPLAATS_PROMO_TAG_RE.search(post.text)
        return True, f"marktplaats_promo_tag:{m.group(1) if m else ''}"
    return False, None


# === Vendor-offering body patterns ===
# Dispositieve vendor-signalen in body-text (source-agnostisch).  Een
# consumer die hulp zoekt schrijft NOOIT "wij zijn gespecialiseerd",
# "staat voor u klaar", "bij mij aan het juiste adres", "beschikbaar in
# regio".  Dit zijn vendor-jargon-catchphrases die elke installateur/
# aannemer/loodgieter in z'n advertentie zet — onafhankelijk van platform.
#
# Body-only (niet title): titel-patronen leven in VENDOR_TITLE_PATTERNS.
# Combinatie title+body geeft de breedste vendor-vangnet.
VENDOR_OFFERING_BODY_PATTERNS: tuple[re.Pattern, ...] = (
    # Vendor catchphrase: "aan het juiste adres"
    re.compile(
        r"\bbij\s+(mij|ons)\s+(bent\s+u\s+)?aan\s+het\s+juiste\s+adres\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bbent\s+u\s+aan\s+het\s+juiste\s+adres\b", re.IGNORECASE),
    # Vendor availability: "staat (voor u) klaar"
    re.compile(r"\bstaat\s+(voor\s+u\s+)?klaar\b", re.IGNORECASE),
    re.compile(r"\bstaan\s+(voor\s+u\s+)?klaar\b", re.IGNORECASE),
    # B2C pitch: "voor al uw [X]" (ook in body, niet alleen titel)
    re.compile(r"\bvoor\s+al\s+uw\b", re.IGNORECASE),
    # Vendor scope: "alle voorkomende (werkzaamheden|klussen)"
    re.compile(
        r"\balle\s+voorkomende\s+(werkzaamheden|klussen)\b", re.IGNORECASE,
    ),
    # Vendor service area: "(beschikbaar|werkzaam) in (de )?(regio|omgeving|stad)"
    re.compile(
        r"\b(beschikbaar|werkzaam)\s+in\s+(de\s+)?(regio|omgeving|stad)\b",
        re.IGNORECASE,
    ),
    # Vendor self-description: "[role] beschikbaar" — nooit consumer-taal.
    # Een consumer schrijft "ik zoek een monteur", niet "monteur beschikbaar".
    re.compile(
        r"\b(cv\-?monteur|monteur|installateur|aannemer|loodgieter|vakman|"
        r"elektricien|stukadoor|tegelzetter|timmerman|hovenier|metselaar|"
        r"dakdekker|schilder|technicus)\s+beschikbaar\b",
        re.IGNORECASE,
    ),
    # Vendor possessive: "mijn advertentie"
    re.compile(r"\bmijn\s+advertentie\b", re.IGNORECASE),
    # Vendor possessive: "onze (klanten|prijzen|tarieven|diensten|werkwijze)"
    re.compile(
        r"\bonze\s+(klanten|prijzen|tarieven|diensten|werkwijze|specialiteit|"
        r"vakmensen)\b",
        re.IGNORECASE,
    ),
    # Corporate self-id: "(wij|we) zijn (gespecialiseerd|uw|een [bedrijfsvorm])"
    re.compile(
        r"\b(?:wij|we)\s+zijn\s+(gespecialiseerd|uw|de\s+specialisten?|een\s+"
        r"(installatiebedrijf|loodgietersbedrijf|aannemersbedrijf|"
        r"klusbedrijf|bouwbedrijf|installateur))\b",
        re.IGNORECASE,
    ),
    # First-person plural offering: "(wij|we) (bieden|verzorgen|verrichten|doen|voeren ... uit)"
    re.compile(
        r"\b(?:wij|we)\s+(bieden|verzorgen|verrichten|doen|leveren)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:wij|we)\s+voeren\b", re.IGNORECASE),
)


def _check_vendor_offering_body(text: str) -> tuple[bool, str | None]:
    """Detecteer vendor-jargon in body-text — dispositief signaal."""
    if not text:
        return False, None
    for pat in VENDOR_OFFERING_BODY_PATTERNS:
        if pat.search(text):
            return True, f"vendor_offering:{pat.pattern[:50]}"
    return False, None


@dataclass(frozen=True)
class BlockResult:
    blocked: bool
    reason: str | None

    def __bool__(self) -> bool:
        return self.blocked


def _host_from_url(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"^https?://(?:www\.)?([^/]+)", url, re.IGNORECASE)
    return (m.group(1).lower() if m else "")


def check_hardblock(post: RawPost) -> BlockResult:
    """True = block (drop deze post zonder verdere processing)."""
    host = _host_from_url(post.url)
    if host:
        for agg in AGGREGATOR_HOSTS:
            if host == agg or host.endswith("." + agg):
                return BlockResult(True, f"aggregator:{agg}")

    if post.author:
        for pat in BLOCKED_AUTHOR_PATTERNS:
            if pat.search(post.author):
                return BlockResult(True, f"author_pattern:{pat.pattern[:40]}")

    title_text = f"{post.title or ''}\n{post.text or ''}"
    for pat in HARD_PROMO_PATTERNS:
        if pat.search(title_text):
            return BlockResult(True, f"promo_pattern:{pat.pattern[:40]}")

    vendor_hit, vendor_reason = _check_vendor_title(post.title or "")
    if vendor_hit:
        return BlockResult(True, vendor_reason)

    mp_hit, mp_reason = _check_marktplaats_vendor(post)
    if mp_hit:
        return BlockResult(True, mp_reason)

    offering_hit, offering_reason = _check_vendor_offering_body(post.text or "")
    if offering_hit:
        return BlockResult(True, offering_reason)

    return BlockResult(False, None)


def is_blocked(post: RawPost) -> bool:
    return bool(check_hardblock(post))


__all__ = [
    "AGGREGATOR_HOSTS",
    "BLOCKED_AUTHOR_PATTERNS",
    "HARD_PROMO_PATTERNS",
    "VENDOR_TITLE_PATTERNS",
    "MARKTPLAATS_SOURCES",
    "MARKTPLAATS_VENDOR_PATH_RE",
    "MARKTPLAATS_PROMO_TAG_RE",
    "VENDOR_OFFERING_BODY_PATTERNS",
    "BlockResult",
    "check_hardblock",
    "is_blocked",
]
