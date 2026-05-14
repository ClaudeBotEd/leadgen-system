"""Scorer — geeft 0-100 lead-score volgens spec:

  +20  locatie aanwezig  (stad of postcode)
  +25  urgentie (zsm, deze maand, asap, dringend, …)
  +25  vraagt expliciet installateur/monteur/aannemer
  +15  woning/situatie genoemd (huis, m2, bouwjaar, dak, …)
  +15  budget/offerte genoemd (euro, prijs, offerte, …)

>=70 hot, 40-69 warm, <40 cold.  Cap op 100.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

# HARD urgency: spoed/asap/zsm — koopklaar, +35
# "haast" stond hier eerder maar werd door "geen haast" als positief
# urgentie-signaal gepakt. Te zwak/ambigu om hard urgency te zijn.
_RE_URGENCY_HARD = re.compile(
    r"\b(z\.?s\.?m\.?|asap|spoed|dringend|"
    r"met spoed|snel mogelijk|spoed nodig|zo snel mogelijk)\b",
    re.IGNORECASE,
)
# SOFT urgency: deze maand / binnenkort / vandaag — meer ruimte, +20
_RE_URGENCY_SOFT = re.compile(
    r"\b(deze week|deze maand|binnenkort|vandaag|morgen|volgende week|"
    r"liefst snel|liefst nog deze|haast|"
    r"binnen \d+ (?:weken|dagen|maanden)|"
    r"binnen (?:een paar|een aantal|enkele|paar|wat) (?:weken|dagen|maanden)|"
    r"deze winter|voor de winter)\b",
    re.IGNORECASE,
)
# Behouden voor backwards-compat (callers buiten dit module).
_RE_URGENCY = re.compile(
    _RE_URGENCY_HARD.pattern + "|" + _RE_URGENCY_SOFT.pattern,
    re.IGNORECASE,
)
_RE_INSTALLER = re.compile(
    r"\b(installateur|installatiebedrijf|monteur|vakman|aannemer|specialist|"
    r"technieker|techneut|cv\-?monteur|verwarmingsmonteur|hvac\-?bedrijf)\b",
    re.IGNORECASE,
)
_RE_HOME = re.compile(
    r"\b(huis|woning|appartement|rijtjeshuis|tussenwoning|hoekwoning|"
    r"vrijstaand|twee[\s\-]?onder[\s\-]?een[\s\-]?kap|geschakelde woning|"
    r"m2|m²|m\^2|vierkante meter|bouwjaar|gebouw|dak|verdieping|"
    r"kruipruimte|kelder|badkamer|keuken|woonkamer|slaapkamer|cv\-ruimte|"
    r"meterkast|zolder|garage)\b",
    re.IGNORECASE,
)
# Hard budget: bedrag in euro / klare kostenvragen.
_RE_BUDGET = re.compile(
    r"(\beuro\b|€|\bEUR\b|"
    r"\b(?:budget|prijs|prijzen|kosten|bedrag|kostenraming|prijsopgave|"
    r"investering|tarief)\b|"
    r"\b\d{1,3}(?:[\.\,\s]\d{3})*\s?(?:k|euro|€))",
    re.IGNORECASE,
)
# Soft budget: "offerte"-woord telt als er een koop-context omheen staat.
# Pure "had een offerte"/"offerte gehad" valt hier níét onder — dat dekt
# `_RE_OFFER_RECEIVED` al apart en geeft daar +20 bonus.
_RE_BUDGET_OFFERTE = re.compile(
    r"(?:"
    # offerte gevolgd door buy-verb (direct of tot 2 woorden ertussen)
    r"\b(?:offerte|offertes|aanbieding|aanbod|prijsopgave|kostenraming)\s+"
    r"(?:\w+\s+){0,2}"
    r"(?:nodig|gevraagd|zoek\w*|graag|opvragen|aanvragen|"
    r"maken|maakt|krijgen|gewenst|wil)\b"
    r"|"
    # buy-verb gevolgd door offerte
    r"\b(?:wie\s+(?:kan|maakt)|kan\s+iemand|wil|zoek\w*|graag)\s+"
    r"(?:\w+\s+){0,3}"
    r"(?:offerte|offertes|aanbieding|prijsopgave|kostenraming)"
    r")",
    re.IGNORECASE,
)

# +10 bonus: zeer expliciete koop/lead intent
_RE_STRONG_BUY = re.compile(
    r"\b(installateur gezocht|monteur gezocht|aannemer gezocht|vakman gezocht|"
    r"laten plaatsen|laten installeren|wie kan plaatsen|wie kan installeren|"
    r"prijsopgave|kostenraming|wat kost het|wat zou kosten|"
    r"met spoed|spoed nodig|zsm starten|asap|dringend|"
    r"deze week|deze maand|binnen \d+ weken|binnen \d+ dagen|"
    r"offerte nodig|offerte gevraagd|"
    r"aan vervanging|moet vervangen|toe aan vervang\w*|"
    r"wie kan offerte|wie maakt offerte|offerte maken)\b",
    re.IGNORECASE,
)

# -25 penalty: informatie/research/orientatie zonder echte aankoopsignalen
# "vergelijk(en|ing)" + "review" verwijderd — "offertes vergelijken" en
# "review van mijn offerte" zijn bottom-of-funnel, geen research.
_RE_RESEARCH_ONLY = re.compile(
    # 'is .{1,40} de moeite' en 'is .{1,40} het beste' verwijderd:
    # vingen 'prijs is niet de moeite waard' / 'dit is niet het beste'
    # als research, terwijl het lead-klachten zijn (-25 penalty op
    # legitime leads). De overige patterns dekken echte research af.
    r"\b(ervaring met|hoe werkt|overweeg|overwegen|aan het orienteren|"
    r"benieuwd naar|nieuwsgierig|informatie over|info over|"
    r"ben aan het orienteren|wil gaan onderzoeken|verschil tussen|"
    r"voor- en nadelen|wat is het verschil|nog niet zeker|"
    r"wat raden jullie|welke kiezen|welk merk|welk model|"
    r"twijfel tussen|advies welke|"
    r"hulp bij keuze|hulp keuze|tips voor keuze)\b",
    re.IGNORECASE,
)

# -20 penalty: discussie-/meningsvragen.  Forum-gebruikers die meningen
# willen, geen monteur.
_RE_DISCUSSION = re.compile(
    r"\b(jullie ervaring(en)?|ervaringen met|iemand ervaring met|"
    r"wat vinden jullie|wat denken jullie|wie heeft ervaring|"
    r"meningen over|opinie over|hoe ervaren jullie)\b",
    re.IGNORECASE,
)

# +30 bonus: stuk/defect apparatuur — hoogste urgentie ("cv kapot", "storing")
# "Harde" signalen vuren op zichzelf; "zachte" signalen alleen samen met apparatuur.
_RE_BROKEN_HARD = re.compile(
    # Bare f\d{1,3} verwijderd: matchte 'F1 race', 'F12 toets', 'F-150 truck'.
    # HVAC-codes hebben in praktijk altijd 'foutmelding'/'error code' prefix.
    r"\b(storing|lekkage|lekt water|"
    r"foutmelding|error\s?code|"
    r"geen warm water|geen verwarming|cv valt uit|"
    r"valt steeds uit|reset zichzelf)\b",
    re.IGNORECASE,
)
_RE_EQUIPMENT = re.compile(
    r"\b(cv|cv\-?ketel|ketel|hr\-?ketel|warmtepomp|airco|verwarming|"
    r"boiler|radiator|combiketel|condensketel)\b",
    re.IGNORECASE,
)
_RE_BROKEN_STATE = re.compile(
    r"\b(kapot|stuk|defect|werkt niet|werkt niet meer|doet het niet|doet niks)\b",
    re.IGNORECASE,
)


def _is_broken(text: str) -> bool:
    if _RE_BROKEN_HARD.search(text):
        return True
    return bool(_RE_EQUIPMENT.search(text) and _RE_BROKEN_STATE.search(text))


# +25 bonus: scherpe deadline ("binnen 2 weken", "voor maart")
# Apart van _RE_URGENCY zodat een concrete deadline bovenop algemene urgentie telt.
_RE_DEADLINE = re.compile(
    r"\b(binnen \d+\s*(week|weken|dag|dagen|maand|maanden)|"
    r"voor (volgende|de) (maand|week)|"
    r"voor (januari|februari|maart|april|mei|juni|juli|"
    r"augustus|september|oktober|november|december)|"
    r"voor (\d{1,2}|begin|eind) (januari|februari|maart|april|mei|juni|juli|"
    r"augustus|september|oktober|november|december)|"
    r"deadline|uiterlijk|voor (kerst|de feestdagen|de zomer|de winter)|"
    r"deze week nog|deze maand nog)\b",
    re.IGNORECASE,
)

# +20 bonus: heeft al een offerte gehad / vergelijkt — koopklaar
_RE_OFFER_RECEIVED = re.compile(
    r"\b(offerte\s*(gehad|ontvangen|gekregen|binnen)|"
    r"al een offerte|al offertes|andere offertes|tweede offerte|"
    r"second opinion|tweede mening|"
    r"prijzen vergelijken|offertes vergelijken|"
    r"ik heb een offerte|gisteren een offerte|vorige week offerte)\b",
    re.IGNORECASE,
)


def _score_location(city: str | None, lower: str) -> int:
    if city:
        return 20
    if re.search(r"\b\d{4}\s?[a-zA-Z]{2}\b", lower):
        return 20
    return 0


def _score_urgency(text: str) -> int:
    """+35 voor harde urgentie (spoed/asap/zsm), anders +20 voor zachte
    urgentie (deze maand / binnenkort).  Geen stacking."""
    if _RE_URGENCY_HARD.search(text):
        return 35
    if _RE_URGENCY_SOFT.search(text):
        return 20
    return 0


def _score_installer(text: str) -> int:
    return 25 if _RE_INSTALLER.search(text) else 0


def _score_home(text: str) -> int:
    return 15 if _RE_HOME.search(text) else 0


def _score_budget(text: str) -> int:
    """+15 voor hard budget (€/bedrag/budget/kosten).  +15 voor 'offerte'
    alleen als er een koop-werkwoord bij staat ('offerte nodig').  Pure
    'had een offerte' valt onder _RE_OFFER_RECEIVED en niet hier."""
    if _RE_BUDGET.search(text):
        return 15
    if _RE_BUDGET_OFFERTE.search(text):
        return 15
    return 0


def _time_decay_factor(created_at: str | None, now: datetime | None = None) -> float:
    """Vermenigvuldigingsfactor op de eindscore op basis van post-leeftijd.

    - ≤14 dagen: ×1.0 (vol gewicht)
    - 15-30 dagen: ×0.7
    - 31-60 dagen: ×0.4
    - >60 dagen: ×0.1

    Onparseerbare/ontbrekende timestamp = geen decay (1.0).
    """
    if not created_at:
        return 1.0
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError, TypeError):
        return 1.0
    ref = now or datetime.now(timezone.utc)
    age_days = (ref - dt).total_seconds() / 86400.0
    if age_days <= 14:
        return 1.0
    if age_days <= 30:
        return 0.7
    if age_days <= 60:
        return 0.4
    return 0.1


def score_post(
    cleaned: dict,
    niche_keywords: list[str] | None = None,
    *,
    created_at: str | None = None,
    now: datetime | None = None,
) -> tuple[int, dict[str, int]]:
    """Bereken score + breakdown.

    `cleaned` is output van processor.cleaner.clean_post().
    `niche_keywords` is optioneel — als geen enkel keyword voorkomt drukken
    we 30 punten af om totaal off-topic posts uit de top te houden.
    `created_at` (ISO-8601) activeert time-decay; `now` is voor testbaarheid.
    """
    text = cleaned.get("full_no_url", "") or cleaned.get("full", "")
    lower = cleaned.get("lower", text.lower())
    city = cleaned.get("city")

    breakdown = {
        "location": _score_location(city, lower),
        "urgency": _score_urgency(text),
        "installer": _score_installer(text),
        "situation": _score_home(text),
        "budget": _score_budget(text),
    }

    # Bonus voor expliciete koopsignalen ("installateur gezocht", "met spoed", etc.)
    if _RE_STRONG_BUY.search(text):
        breakdown["intent_bonus"] = 10

    # +40 — stuk/defect apparatuur ("cv kapot", "storing") — sterkste single signal
    if _is_broken(text):
        breakdown["broken_bonus"] = 40

    # +25 — concrete deadline ("binnen 2 weken")
    if _RE_DEADLINE.search(text):
        breakdown["deadline_bonus"] = 25

    # +20 — heeft al offerte gehad / vergelijkt
    if _RE_OFFER_RECEIVED.search(text):
        breakdown["offer_received_bonus"] = 20

    # -25 — research/orientatie taal ("ervaring met", "hoe werkt", "vergelijk",
    # "welke kiezen", "is X de moeite")
    if _RE_RESEARCH_ONLY.search(text):
        breakdown["research_penalty"] = -25

    # -20 — discussie-/meningsvragen ("jullie ervaring", "wat vinden jullie")
    if _RE_DISCUSSION.search(text):
        breakdown["discussion_penalty"] = -20

    total = sum(breakdown.values())

    if niche_keywords:
        if not any(kw.lower() in lower for kw in niche_keywords):
            total -= 30
            breakdown["off_topic_penalty"] = -30

    total = max(0, min(100, total))

    factor = _time_decay_factor(created_at, now)
    if factor < 1.0:
        decayed = int(round(total * factor))
        breakdown["time_decay_penalty"] = decayed - total
        total = decayed

    return total, breakdown
