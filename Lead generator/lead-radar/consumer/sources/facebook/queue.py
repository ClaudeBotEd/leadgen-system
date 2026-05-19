"""JSONL queue for raw-post handoff from the FB runner to the main pipeline.

The runner writes one JSONL file per run into ``data/fb_queue/``.  At pipeline
start, ``run_consumer.py`` calls :func:`drain` which yields all RawPost records
and moves consumed files into ``data/fb_queue/processed/`` for inspection.

Format is one JSON-serialized RawPost per line, UTF-8.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Iterator

from consumer import RawPost

log = logging.getLogger("consumer.sources.facebook.queue")


def write_jsonl(path: Path, posts: Iterable[RawPost]) -> None:
    """Write a sequence of RawPost records as one JSON object per line.

    Creates parent directories if missing.  Empty input creates an empty file
    (the runner can distinguish "ran but caught nothing" from "didn't run").
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for post in posts:
            fh.write(json.dumps(asdict(post), ensure_ascii=False) + "\n")


def drain(queue_dir: Path) -> Iterator[RawPost]:
    """Yield every RawPost from every ``*.jsonl`` file directly under queue_dir.

    For each file we first read and parse ALL records into a local list, then
    move the file to ``processed/``, then yield from the list.  This makes
    early-exit iteration safe (the caller's break/return won't lose records
    that were already read into memory) and also means a single file's records
    are atomic — the caller sees all of them or none.

    Malformed lines are logged and skipped.  The ``processed/`` subdirectory
    is not scanned.
    """
    if not queue_dir.exists():
        return
    processed = queue_dir / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    for jsonl in sorted(queue_dir.glob("*.jsonl")):
        records: list[RawPost] = []
        with jsonl.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    log.warning("fb_queue: malformed line %s:%d (%s)", jsonl.name, lineno, exc)
                    continue
                try:
                    records.append(RawPost(**rec))
                except TypeError as exc:
                    log.warning("fb_queue: invalid RawPost shape %s:%d (%s)", jsonl.name, lineno, exc)
                    continue
        # Move file out of the queue dir BEFORE yielding so a caller break/early-return
        # doesn't leave the file in place to be re-drained next run.
        #
        # On rare same-name collisions (e.g. a previous drain produced the same filename)
        # we append a -N counter suffix instead of overwriting, so audit history in
        # processed/ is never silently destroyed.
        target = processed / jsonl.name
        if target.exists():
            stem, suffix = jsonl.stem, jsonl.suffix
            n = 1
            while (processed / f"{stem}-{n}{suffix}").exists():
                n += 1
            target = processed / f"{stem}-{n}{suffix}"
        jsonl.rename(target)
        yield from records
