"""Layer-3 author-signature dedup for sources with reliable author identity.

A user who posts about warmtepomp in r/Amsterdam on Monday and reposts in
r/Klussers on Wednesday is one lead, not two. Skip for sources where the
"author" field is just a listing-poster (Marktplaats, DDG hits).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Sources where the author field represents a stable identity.
# DDG hits and Marktplaats sellers are excluded — those identities aren't
# reliable signals for "this is the same person asking again."
SOURCES_WITH_AUTHOR: frozenset[str] = frozenset({
    "reddit", "reddit_new",
    "tweakers",
    "bouwinfo", "bouwinfo_forum",
    "klusidee_forum",
    "ouders_forum",
    "facebook",
})


def _author_hash(author: str, niche: str) -> str:
    h = hashlib.sha256()
    h.update(f"{author.strip().lower()}|{niche.strip().lower()}".encode("utf-8"))
    return h.hexdigest()


def is_author_repeat(
    *,
    author: str,
    niche: str,
    store_path: Path,
    retain_days: int = 30,
) -> bool:
    if not store_path.exists():
        return False
    target = _author_hash(author, niche)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retain_days)
    with store_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("author_hash") != target:
                continue
            try:
                last_seen = datetime.fromisoformat(rec["last_seen"])
            except (KeyError, ValueError):
                continue
            if last_seen >= cutoff:
                return True
    return False


def record_author_post(
    *,
    author: str,
    niche: str,
    store_path: Path,
    now: datetime,
) -> None:
    """Append-or-update author-signature record."""
    target = _author_hash(author, niche)
    now_iso = now.astimezone(timezone.utc).isoformat(timespec="seconds")
    store_path.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if store_path.exists():
        with store_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    found = False
    for rec in existing:
        if rec.get("author_hash") == target:
            rec["last_seen"] = now_iso
            rec["post_count"] = int(rec.get("post_count", 0)) + 1
            found = True
            break

    if not found:
        existing.append({
            "author_hash": target,
            "niche": niche,
            "first_seen": now_iso,
            "last_seen": now_iso,
            "post_count": 1,
        })

    with store_path.open("w", encoding="utf-8") as f:
        for rec in existing:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def prune_author_store(*, store_path: Path, retain_days: int = 30) -> int:
    if not store_path.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retain_days)
    kept: list[str] = []
    removed = 0
    with store_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                last_seen = datetime.fromisoformat(rec["last_seen"])
            except (json.JSONDecodeError, KeyError, ValueError):
                kept.append(line)
                continue
            if last_seen >= cutoff:
                kept.append(line)
            else:
                removed += 1
    store_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return removed
