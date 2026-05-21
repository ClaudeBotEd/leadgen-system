"""Opening-line builder per spec §7.4. First person singular, no smileys, no exclamation."""

from __future__ import annotations

from .subject import ALLOWED_BANDS

_TEMPLATE = (
    "Hallo {installer_first},\n"
    "\n"
    "Onderstaande post kwam binnen vanuit {platform}. Ik heb hem\n"
    "beoordeeld en band {band} toegekend. Reden staat onder de bron."
)


def build_opening(*, installer_first: str, platform: str, band: str) -> str:
    band_norm = band.strip().upper()
    if band_norm not in ALLOWED_BANDS:
        raise ValueError(f"band must be one of {sorted(ALLOWED_BANDS)}")
    return _TEMPLATE.format(
        installer_first=installer_first.strip(),
        platform=platform.strip().title(),
        band=band_norm,
    )
