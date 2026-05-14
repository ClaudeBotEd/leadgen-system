"""LLM-verifier — Claude Haiku second-opinion op borderline scores.

Doel: regex-scorer heeft hoge precision op extremen (HOT / clear-promo) maar
matige recall in de borderline 40-75 zone. Hier roepen we Claude Haiku aan
om elk borderline-geval te herclassificeren en eventueel te herwaarderen.

Kosten: ~€0.001/post bij Haiku. Cap via LEAD_RADAR_LLM_BUDGET_EUR per run.

Output is een strict JSON-object dat we als second-opinion naast de regex
breakdown opslaan. Bij ontbrekende API key of API-fout geeft de verifier
een "skipped" verdict en blijft de regex-score leidend.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MIN_SCORE = 40
DEFAULT_MAX_SCORE = 75
DEFAULT_TIMEOUT_S = 12

# Absoluut pad anchored op repo-root, niet cwd. Onder cron/systemd is cwd
# vaak / of /var/spool/cron, waardoor een relatief pad cache-misses geeft
# en elke borderline post een echte Anthropic API call kost.
# parents[0]=processor/, parents[1]=consumer/, parents[2]=lead-radar/
DEFAULT_CACHE_DIR = (Path(__file__).resolve().parents[2] / ".cache" / "llm_verifier")

# Per-run budget cap.  LEAD_RADAR_LLM_BUDGET_EUR env var = max EUR-spend per
# Python-proces (= per cron-run).  Reset bij start van een nieuwe loop via
# reset_run_counters().  ~€0.001/call bij Haiku is ruwe schatting; exacte
# tokens variëren, dus dit is een soft cap die runaway-loops afvangt, niet
# een precieze accountant.
_COST_PER_CALL_EUR = 0.001
_run_api_calls_made = 0
_run_cache_hits = 0
_run_cache_misses = 0


SYSTEM_PROMPT = """Je beoordeelt Nederlandse forumposts op koop-intentie voor installatie-diensten (warmtepomp, airco, zonnepanelen, cv-ketel, renovatie).

Geef ALLEEN een JSON-object terug met deze velden:
{
  "kind": "lead" | "info" | "promo" | "discussion",
  "confidence": 0.0-1.0,
  "refined_score": 0-100,
  "is_real_lead": true | false,
  "reason": "1 korte zin Nederlands"
}

Beslissingsregels:
- "lead": persoon wil offerte / installateur / monteur. Heeft concrete intentie.
- "info": persoon wil informatie / advies / oriëntatie. Geen koopintentie.
- "promo": bedrijf adverteert / verkoopt / werft.
- "discussion": forum-discussie over merken / ervaringen / meningen.

refined_score-richtlijnen (0-100):
- 80-100: duidelijke koop-intentie + urgentie + locatie + concreet probleem.
- 60-79: duidelijke koop-intentie maar minder urgentie of vager.
- 40-59: zwakke buy-signalen, mogelijk passant.
- 0-39: research / info / promo / discussion.

Output ALLEEN het JSON-object, geen extra tekst."""


# Fingerprint van SYSTEM_PROMPT — wordt meegehasht in de cache-key zodat
# een wijziging in de prompt automatisch alle gecachte verdicts invalideert.
# Bij module-load berekend zodat één wijziging in de string genoeg is.
_SYSTEM_PROMPT_FINGERPRINT = hashlib.sha256(
    SYSTEM_PROMPT.encode("utf-8"),
).hexdigest()[:8]


@dataclass
class LlmVerdict:
    available: bool
    kind: str | None
    confidence: float
    refined_score: int | None
    is_real_lead: bool | None
    reason: str
    model: str
    skipped_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _skipped(reason: str, model: str = DEFAULT_MODEL) -> LlmVerdict:
    return LlmVerdict(
        available=False, kind=None, confidence=0.0, refined_score=None,
        is_real_lead=None, reason="", model=model, skipped_reason=reason,
    )


def _post_hash(text: str, model: str) -> str:
    # SYSTEM_PROMPT-fingerprint zit in de cache-key zodat een wijziging in
    # de prompt automatisch de cache invalideert.  Anders blijven oude
    # verdicts geserveerd worden van de vorige prompt-versie en heeft een
    # prompt-update geen effect tot iemand handmatig .cache/ leegmaakt.
    raw = f"{_SYSTEM_PROMPT_FINGERPRINT}|{model}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _cache_load(cache_dir: Path, key: str) -> dict | None:
    if not cache_dir:
        return None
    f = cache_dir / f"{key}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _cache_save(cache_dir: Path, key: str, payload: dict) -> None:
    if not cache_dir:
        return
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{key}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8",
        )
    except OSError as e:
        log.debug("LLM cache write failed: %s", e)


def _parse_response(text: str) -> dict | None:
    # Brace-counting parser: vindt het eerste gebalanceerde JSON-object.
    # Oude greedy regex r"\{.*\}" matchte van eerste { tot LAATSTE }; bij
    # trailing tekst met een tweede { (uitleg, voorbeelden) werd dat
    # invalid JSON en de hele verdict werd silently gedropt.
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _build_user_prompt(*, title: str, text: str, city: str | None,
                       niche: str, regex_score: int,
                       regex_breakdown: dict) -> str:
    parts = [
        f"NICHE: {niche}",
        f"STAD (gedetecteerd): {city or '—'}",
        f"REGEX-SCORE: {regex_score}",
        f"REGEX-BREAKDOWN: {regex_breakdown}",
        f"TITEL: {title}",
        f"TEKST:\n{text}",
    ]
    return "\n\n".join(parts)


def _budget_exhausted() -> bool:
    """True als de per-run budget cap is bereikt; False als geen cap is gezet
    of de env var ongeldig is (defensief: nooit crashen op config-fout)."""
    cap_str = os.environ.get("LEAD_RADAR_LLM_BUDGET_EUR")
    if not cap_str:
        return False
    try:
        cap_eur = float(cap_str)
    except ValueError:
        log.warning(
            "LEAD_RADAR_LLM_BUDGET_EUR=%r is geen geldig getal; cap genegeerd",
            cap_str,
        )
        return False
    spent_eur = _run_api_calls_made * _COST_PER_CALL_EUR
    return spent_eur >= cap_eur


def reset_run_counters() -> None:
    """Reset per-run counters (budget cap + cache stats).  Roep aan bij start
    van een nieuwe pipeline-run als je de cap per-run wilt resetten (anders
    blijft het cumulatief binnen hetzelfde Python-proces)."""
    global _run_api_calls_made, _run_cache_hits, _run_cache_misses
    _run_api_calls_made = 0
    _run_cache_hits = 0
    _run_cache_misses = 0


def get_run_stats() -> dict[str, int]:
    """Snapshot van per-run counters voor observability.  Caller logt
    deze waardes in de eindsamenvatting zodat operator cache-effectiviteit
    en API-spend kan zien zonder Anthropic dashboard te openen."""
    return {
        "api_calls": _run_api_calls_made,
        "cache_hits": _run_cache_hits,
        "cache_misses": _run_cache_misses,
        "estimated_cost_eur": round(_run_api_calls_made * _COST_PER_CALL_EUR, 4),
    }


def should_verify(score: int, *, min_score: int = DEFAULT_MIN_SCORE,
                  max_score: int = DEFAULT_MAX_SCORE) -> bool:
    """True als deze score in de borderline-zone valt."""
    return min_score <= score <= max_score


def verify_post(
    *,
    title: str,
    text: str,
    city: str | None,
    niche: str,
    regex_score: int,
    regex_breakdown: dict,
    model: str = DEFAULT_MODEL,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    cache_dir: Path | None = DEFAULT_CACHE_DIR,
    api_key: str | None = None,
) -> LlmVerdict:
    """Roep Claude aan om deze borderline post te herclassificeren.

    Veilig: bij ontbrekende key / netwerk-fout / parse-fout geeft een
    `skipped` verdict terug. De regex-score blijft dan leidend.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _skipped("no_api_key", model=model)

    try:
        from anthropic import Anthropic  # type: ignore[import-not-found]
    except ImportError:
        return _skipped("anthropic_sdk_missing", model=model)

    user_prompt = _build_user_prompt(
        title=title, text=text, city=city, niche=niche,
        regex_score=regex_score, regex_breakdown=regex_breakdown,
    )

    cache_key = _post_hash(user_prompt, model)
    global _run_cache_hits, _run_cache_misses
    if cache_dir is not None:
        cached = _cache_load(cache_dir, cache_key)
        if cached:
            _run_cache_hits += 1
            return LlmVerdict(**cached)
        _run_cache_misses += 1

    # Budget cap: na cache-check, vóór API call.  Cached hits kosten niets en
    # tellen niet mee — alleen daadwerkelijke API-calls.
    if _budget_exhausted():
        return _skipped("budget_exhausted", model=model)

    try:
        client = Anthropic(api_key=api_key, timeout=timeout_s)
        resp = client.messages.create(
            model=model,
            max_tokens=300,
            system=[{
                "type": "text", "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        log.warning("LLM verifier API call failed: %s", e)
        return _skipped(f"api_error:{type(e).__name__}", model=model)

    global _run_api_calls_made
    _run_api_calls_made += 1

    raw_text = ""
    try:
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                raw_text += block.text
    except (AttributeError, TypeError):
        pass

    parsed = _parse_response(raw_text)
    if not parsed:
        return _skipped("parse_error", model=model)

    kind = parsed.get("kind")
    if kind not in {"lead", "info", "promo", "discussion"}:
        return _skipped(f"bad_kind:{kind}", model=model)

    try:
        confidence = float(parsed.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    refined_score: int | None
    try:
        refined_score = int(parsed.get("refined_score", 0))
        refined_score = max(0, min(100, refined_score))
    except (TypeError, ValueError):
        refined_score = None

    is_real_lead = parsed.get("is_real_lead")
    if not isinstance(is_real_lead, bool):
        is_real_lead = (kind == "lead") if kind else None

    verdict = LlmVerdict(
        available=True,
        kind=kind,
        confidence=confidence,
        refined_score=refined_score,
        is_real_lead=is_real_lead,
        reason=str(parsed.get("reason", ""))[:200],
        model=model,
        skipped_reason=None,
    )
    if cache_dir is not None:
        _cache_save(cache_dir, cache_key, verdict.to_dict())
    return verdict


def combine_score(regex_score: int, verdict: LlmVerdict) -> int:
    """Weeg regex-score + LLM-verdict tot één eindscore.

    Strategie:
    - LLM skipped → regex-score onveranderd.
    - LLM zegt promo/discussion + confidence ≥0.7 → drop naar 0.
    - LLM zegt info + confidence ≥0.6 → min(regex/2, refined).
    - LLM zegt lead + refined > regex → gemiddelde.
    - LLM zegt lead + refined < regex → minimum (kwaliteits-bias).
    """
    if not verdict.available or verdict.refined_score is None:
        return regex_score

    if verdict.kind in ("promo", "discussion") and verdict.confidence >= 0.7:
        return 0

    if verdict.kind == "info" and verdict.confidence >= 0.6:
        return min(regex_score // 2, verdict.refined_score)

    if verdict.kind == "lead":
        if verdict.refined_score > regex_score:
            return (regex_score + verdict.refined_score) // 2
        return min(regex_score, verdict.refined_score)

    return regex_score


__all__ = [
    "DEFAULT_MIN_SCORE", "DEFAULT_MAX_SCORE", "DEFAULT_MODEL",
    "LlmVerdict",
    "should_verify", "verify_post", "combine_score",
    "reset_run_counters", "get_run_stats",
]
