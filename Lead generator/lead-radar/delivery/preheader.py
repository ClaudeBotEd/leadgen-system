"""Pre-header builder per spec §7.3 + reviewer_first_name helper."""

from __future__ import annotations


def reviewer_first_name(full_name: str) -> str:
    cleaned = full_name.strip()
    if not cleaned:
        raise ValueError("reviewer name must be non-empty")
    return cleaned.split()[0]


def build_preheader(*, reviewer_first: str, platform: str, region: str) -> str:
    platform_norm = platform.strip().title()
    region_norm = region.strip()
    return f"{reviewer_first} reviewde een {platform_norm}-post uit regio {region_norm}."
