"""Layer-2 cross-run persistent dedup using MinHash.

Stores compact MinHash signatures of all sellable leads. When a new
candidate lead is scored, we check it against the last 14 days of
signatures. A Jaccard similarity >= threshold is treated as a dup.

Store: data/dedup_store.jsonl (one JSON record per line, append-only,
pruned periodically).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
from datasketch import MinHash

NUM_PERM = 64  # 64-perm MinHash gives Jaccard estimate w/ ~12% std error, ~512B/line
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(text: str) -> Iterable[str]:
    return (t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2)


def _build_signature(text: str) -> MinHash:
    mh = MinHash(num_perm=NUM_PERM)
    for tok in _tokens(text):
        mh.update(tok.encode("utf-8"))
    return mh


def _serialize_signature(mh: MinHash) -> str:
    """Pack the hashvalues array into a hex string for compact JSONL storage."""
    return mh.hashvalues.tobytes().hex()


def _deserialize_signature(hex_str: str) -> MinHash:
    arr = np.frombuffer(bytes.fromhex(hex_str), dtype=np.uint64).copy()
    mh = MinHash(num_perm=NUM_PERM, hashvalues=arr)
    return mh


def record_lead_signature(
    *,
    lead_id: str,
    text: str,
    source: str,
    niche: str,
    store_path: Path,
    now: datetime,
) -> None:
    """Append a signature record to the store."""
    mh = _build_signature(text)
    rec = {
        "signature": _serialize_signature(mh),
        "lead_id": lead_id,
        "captured_at": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "niche": niche,
    }
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with store_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def is_cross_run_duplicate(
    *,
    text: str,
    store_path: Path,
    threshold: float = 0.70,
) -> bool:
    """Return True if any prior signature in the store is similar enough."""
    if not store_path.exists():
        return False
    candidate = _build_signature(text)
    with store_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                prior = _deserialize_signature(rec["signature"])
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
            if candidate.jaccard(prior) >= threshold:
                return True
    return False


def prune_store(*, store_path: Path, retain_days: int = 14) -> int:
    """Drop records older than retain_days. Returns count removed."""
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
                captured = datetime.fromisoformat(rec["captured_at"])
            except (json.JSONDecodeError, KeyError, ValueError):
                kept.append(line)  # keep malformed for debugging
                continue
            if captured >= cutoff:
                kept.append(line)
            else:
                removed += 1
    store_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return removed
