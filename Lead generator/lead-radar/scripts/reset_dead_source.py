#!/usr/bin/env python3
"""Reset the dead-source health counter for one or all sources.

Usage:
    python scripts/reset_dead_source.py reddit
    python scripts/reset_dead_source.py marktplaats bouwinfo_forum
    python scripts/reset_dead_source.py --all

After 3 consecutive 0-yield runs, the dispatcher in consumer/sources/__init__.py
marks a source as dead and skips it for the rest of the current process. This
CLI clears the in-process flag — but since each launchd run starts a fresh
process, this CLI is most useful for manual --daily invocations or when
diagnosing why a source isn't producing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from consumer.sources import REGISTRY, reset_source_health  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", help="Source names to reset")
    parser.add_argument("--all", action="store_true", help="Reset all sources")
    args = parser.parse_args()

    if not args.all and not args.sources:
        parser.error("specify one or more source names, or --all")

    targets = list(REGISTRY) if args.all else args.sources

    unknown = [s for s in targets if s not in REGISTRY]
    if unknown:
        print(
            f"ERROR: unknown source(s): {', '.join(unknown)}\n"
            f"Known sources in REGISTRY: {', '.join(sorted(REGISTRY))}",
            file=sys.stderr,
        )
        return 2

    for source in targets:
        reset_source_health(source)
        print(f"reset: {source}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
