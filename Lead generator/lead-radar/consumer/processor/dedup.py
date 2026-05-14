"""Fuzzy cross-platform dedup — Jaccard over shingles.

SeenStore in utils.py dedupliceert al op (source, id, url) tuple maar mist
de "zelfde persoon op Reddit + Marktplaats" case.  Hier doen we tekst-niveau
fuzzy match zodat dezelfde lead niet 2x verkocht wordt.

Aanpak:
- Tokenize titel + tekst → 3-gram woord-shingles
- Hash elke shingle naar int32 (md5-prefix)
- Persist set-per-post in JSON store
- Bij nieuwe post: bereken set, vergelijk met alle eerder gesignaleerde sets
- Jaccard ≥ THRESHOLD = duplicaat

Voor 10K+ posts kan dit naar MinHash+LSH evolueren; voor MVP voldoende.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.70
DEFAULT_SHINGLE_SIZE = 3
DEFAULT_MIN_SHINGLES = 5

_RE_NON_ALNUM = re.compile(r"[^a-z0-9\s]+")
_RE_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    flat = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
    flat = _RE_NON_ALNUM.sub(" ", flat)
    return _RE_WHITESPACE.sub(" ", flat).strip()


def _shingle_hash(words: tuple[str, ...]) -> int:
    joined = " ".join(words).encode("utf-8")
    return int.from_bytes(hashlib.md5(joined).digest()[:4], "big")


def shingles(text: str, k: int = DEFAULT_SHINGLE_SIZE) -> frozenset[int]:
    """Return frozenset of int-hashes voor alle k-word-shingles in text."""
    norm = _normalize(text)
    if not norm:
        return frozenset()
    words = norm.split()
    if len(words) < k:
        return frozenset()
    return frozenset(_shingle_hash(tuple(words[i:i + k]))
                     for i in range(len(words) - k + 1))


def jaccard(a: frozenset[int], b: frozenset[int]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass
class TextSignatureStore:
    """JSON-backed persistent map van post_id -> shingle-set.

    Keys: stabiele post-fingerprint (uit RawPost.fingerprint()).
    """
    path: Path | None = None
    threshold: float = DEFAULT_THRESHOLD
    k: int = DEFAULT_SHINGLE_SIZE
    min_shingles: int = DEFAULT_MIN_SHINGLES
    _signatures: dict[str, frozenset[int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.path and self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self._signatures = {
                    k: frozenset(v) for k, v in raw.items()
                    if isinstance(v, list)
                }
            except (OSError, json.JSONDecodeError) as e:
                log.warning("Kon dedup-store niet lezen: %s — start leeg", e)
                self._signatures = {}

    def __len__(self) -> int:
        return len(self._signatures)

    def find_duplicate(self, text: str) -> tuple[str, float] | None:
        """Geeft (post_id, jaccard) terug van best-match met sim ≥ threshold."""
        sig = shingles(text, k=self.k)
        if len(sig) < self.min_shingles:
            return None
        best: tuple[str, float] | None = None
        for other_id, other_sig in self._signatures.items():
            sim = jaccard(sig, other_sig)
            if sim >= self.threshold and (best is None or sim > best[1]):
                best = (other_id, sim)
        return best

    def add(self, post_id: str, text: str) -> bool:
        """Voeg signature toe.  True als toegevoegd, False als te kort."""
        sig = shingles(text, k=self.k)
        if len(sig) < self.min_shingles:
            return False
        self._signatures[post_id] = sig
        return True

    def has(self, post_id: str) -> bool:
        return post_id in self._signatures

    def save(self) -> None:
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(
                    {k: sorted(v) for k, v in self._signatures.items()},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError as e:
            log.warning("Kon dedup-store niet schrijven: %s", e)


__all__ = [
    "DEFAULT_THRESHOLD", "DEFAULT_SHINGLE_SIZE", "DEFAULT_MIN_SHINGLES",
    "TextSignatureStore",
    "shingles", "jaccard",
]
