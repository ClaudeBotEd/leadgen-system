"""Facebook helper — NIET scrapen.

Per spec: Facebook niet automatisch scrapen.  In plaats daarvan kopieer
je posts handmatig (uit een groep, marketplace listing, etc.) en laat
ze analyseren met dezelfde scoring-pipeline.

Gebruik:
    from consumer.sources.facebook import analyze_manual_posts
    leads = analyze_manual_posts(["Wie heeft tip voor warmtepomp installateur Utrecht?", ...])

Of vanaf de CLI:
    python run_consumer.py --niche warmtepomp --facebook-file fb_posts.txt
(posts gescheiden door lege regel of `---`).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from .. import RawPost, Lead, intent_from_score
from ..processor import clean_post, classify_post_kind, score_post

log = logging.getLogger("consumer.sources.facebook")


def _short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:12]


def _to_raw(text: str, idx: int) -> RawPost:
    text = text.strip()
    rid = f"facebook:{_short_hash(text)}-{idx}"
    return RawPost(
        id=rid,
        source="facebook",
        url="(handmatig — geen URL)",
        title=text.split("\n", 1)[0][:120],
        text=text,
        author=None,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        metadata={"manual_input": True},
    )


def analyze_manual_posts(posts: list[str], *, niche: str = "manual",
                         niche_keywords: list[str] | None = None,
                         min_score: int = 0) -> list[Lead]:
    """Analyseer een lijst losse FB-posts en geef Lead-objecten terug.

    Geeft *alle* posts terug (geen automatische filter) zodat jij ziet
    welke wel/niet als lead scoorden.  `min_score` filtert optioneel weg.
    """
    out: list[Lead] = []
    for idx, text in enumerate(posts):
        if not text or not text.strip():
            continue
        raw = _to_raw(text, idx)
        cleaned = clean_post(raw)
        kind = classify_post_kind(cleaned["full"])
        score, breakdown = score_post(cleaned, niche_keywords)
        intent = intent_from_score(score)
        breakdown["kind"] = {"lead": 1, "promo": -1, "info": 0, "unknown": 0}.get(kind, 0)
        if score < min_score:
            continue
        out.append(Lead(
            id=raw.id,
            source=raw.source,
            title=cleaned["title"] or raw.title,
            text=cleaned["text"],
            summary=cleaned["summary"],
            url=raw.url,
            city=cleaned["city"],
            score=score,
            intent=intent,
            breakdown=breakdown,
            niche=niche,
            author=raw.author,
            created_at=raw.created_at,
        ))
    log.info("Facebook handmatig: %d posts -> %d leads", len(posts), len(out))
    return out


def load_posts_from_file(path: str | Path) -> list[str]:
    """Lees posts uit een tekstbestand. Posts gescheiden door lege regel of `---`."""
    p = Path(path)
    if not p.exists():
        log.warning("FB file niet gevonden: %s", p)
        return []
    raw = p.read_text(encoding="utf-8", errors="replace")
    chunks: list[str] = []
    for block in raw.split("---"):
        for sub in block.split("\n\n"):
            sub = sub.strip()
            if sub:
                chunks.append(sub)
    return chunks
