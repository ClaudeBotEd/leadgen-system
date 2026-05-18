"""CLI: python -m delivery dispatch [--dry-run] [--limit N]."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .config import load_config
from .dispatcher import dispatch


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="delivery", description="Lead Radar receipt dispatcher")
    sub = parser.add_subparsers(dest="command", required=True)
    p_dispatch = sub.add_parser("dispatch", help="Dispatch one batch of approved receipts")
    p_dispatch.add_argument("--limit", type=int, default=None, help="Max receipts to send")
    p_dispatch.add_argument("--dry-run", action="store_true", help="Override DELIVERY_DRY_RUN")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "dispatch":
        config = load_config()
        if args.dry_run:
            config.dry_run = True
        summary = dispatch(config, limit=args.limit)
        print(
            f"total={summary.total} delivered={summary.delivered} "
            f"unrouted={summary.unrouted} vocab_violations={summary.vocab_violations} "
            f"errors={summary.errors} dry_run={config.dry_run}"
        )
        return 0 if summary.errors == 0 else 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
