"""Minimal source-page archive at approval time.

Doctrine §01.3: every approved lead carries an offline snapshot of the
source page. capture_evidence is internal-only by default; the delivery
layer exposes the archive URL only when delivery_condition is DECAYED
or EDITED.

v0 limitation: this captures at approval time, not at scrape time.
v0.2 should move to scrape-time capture; the post may mutate between
scrape and approval, but for v0 we accept that trade.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger("moderation.archive")

ARCHIVE_TIMEOUT_SECONDS = 10
ARCHIVE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB cap per page

# Defensive whitelist: candidate_id must be a single path-safe segment.
# Rejects empty, "None"/"null" sentinels, path-traversal, slashes, dots.
_SAFE_CANDIDATE_ID = re.compile(r"^[A-Za-z0-9_\-]+$")
_REJECTED_CANDIDATE_IDS = frozenset({"None", "null", "undefined", "NaN"})


def _is_safe_candidate_id(cid: object) -> bool:
    if not isinstance(cid, str):
        return False
    if cid in _REJECTED_CANDIDATE_IDS:
        return False
    return bool(_SAFE_CANDIDATE_ID.match(cid))


@dataclass
class ArchiveRecord:
    candidate_id: str
    source_url: str
    archived_at: str            # ISO-8601 UTC, second precision
    status: str                 # "ok" | "failed"
    http_status: Optional[int]
    sha256: Optional[str]
    bytes: Optional[int]
    path: Optional[str]
    error: Optional[str]


def archive_source(
    candidate_id: str,
    source_url: str,
    output_dir: Path,
) -> ArchiveRecord:
    """Fetch source HTML; write {output_dir}/{candidate_id}/{source.html, meta.json}.

    Non-blocking on failure — caller MUST persist the record either way,
    so the auditor sees the gap.
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not _is_safe_candidate_id(candidate_id):
        log.warning("archive refused: invalid candidate_id %r", candidate_id)
        return ArchiveRecord(
            candidate_id=str(candidate_id),
            source_url=source_url,
            archived_at=now,
            status="failed",
            http_status=None,
            sha256=None,
            bytes=None,
            path=None,
            error=f"invalid candidate_id: {candidate_id!r}",
        )

    case_dir = output_dir / candidate_id
    case_dir.mkdir(parents=True, exist_ok=True)
    record: ArchiveRecord
    try:
        resp = requests.get(
            source_url,
            timeout=ARCHIVE_TIMEOUT_SECONDS,
            stream=True,
        )
        resp.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=8192):
            if not chunk:
                continue
            total += len(chunk)
            if total > ARCHIVE_MAX_BYTES:
                raise ValueError(
                    f"archive content exceeds {ARCHIVE_MAX_BYTES} bytes "
                    f"for {source_url!r}"
                )
            chunks.append(chunk)
        content = b"".join(chunks)
        sha = hashlib.sha256(content).hexdigest()
        html_path = case_dir / "source.html"
        html_path.write_bytes(content)
        record = ArchiveRecord(
            candidate_id=candidate_id,
            source_url=source_url,
            archived_at=now,
            status="ok",
            http_status=resp.status_code,
            sha256=sha,
            bytes=len(content),
            path=str(html_path),
            error=None,
        )
    except Exception as exc:
        log.warning("archive failed for %s: %s", candidate_id, exc)
        record = ArchiveRecord(
            candidate_id=candidate_id,
            source_url=source_url,
            archived_at=now,
            status="failed",
            http_status=None,
            sha256=None,
            bytes=None,
            path=None,
            error=str(exc),
        )

    meta_path = case_dir / "meta.json"
    meta_path.write_text(
        json.dumps(asdict(record), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return record
