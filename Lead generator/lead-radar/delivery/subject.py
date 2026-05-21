"""Subject-line builder per spec §7.2."""

from __future__ import annotations

ALLOWED_BANDS = frozenset({"HOT", "WARM", "OPP"})
ALLOWED_NICHES = frozenset({"warmtepomp", "airco", "zonnepanelen", "laadpaal", "verduurzaming"})


def build_subject(*, region: str, niche: str, band: str) -> str:
    niche_norm = niche.strip().lower()
    band_norm = band.strip().upper()
    if niche_norm not in ALLOWED_NICHES:
        raise ValueError(f"niche must be one of {sorted(ALLOWED_NICHES)}, got {niche!r}")
    if band_norm not in ALLOWED_BANDS:
        raise ValueError(f"band must be one of {sorted(ALLOWED_BANDS)}, got {band!r}")
    region_norm = region.strip()
    if not region_norm:
        raise ValueError("region must be non-empty")
    return f"{region_norm} · {niche_norm} · {band_norm}"
