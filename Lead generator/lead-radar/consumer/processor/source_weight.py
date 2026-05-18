"""Per-source credibility weight applied before threshold gating.

Weights live in config.yaml:source_weights. The processor strips any
source_id subcontext (':r/duurzaam') so the weight maps on the base
source registry name.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

import yaml


def _base_source(source_or_source_id: str) -> str:
    return source_or_source_id.split(":", 1)[0] if ":" in source_or_source_id else source_or_source_id


def apply_source_weight(
    *,
    score: int,
    source: str,
    weights: Mapping[str, float],
) -> int:
    """Apply weight multiplier and clamp to [0, 100]."""
    base = _base_source(source)
    multiplier = float(weights.get(base, 1.0))
    weighted = round(score * multiplier)
    return max(0, min(100, int(weighted)))


def load_source_weights(*, config_path: Path) -> dict[str, float]:
    if not config_path.exists():
        return {}
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    raw = cfg.get("source_weights") or {}
    return {str(k): float(v) for k, v in raw.items()}
