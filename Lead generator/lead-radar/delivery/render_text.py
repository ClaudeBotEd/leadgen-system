"""Plain-text canonical renderer per spec §7.5 + §7.9.

Element order is doctrine (02.1 + 04.5). Spacing matches the spec example.
"""

from __future__ import annotations

from datetime import datetime

from .decay import is_decayed
from .model import RoutedLead
from .opening import build_opening
from .preheader import reviewer_first_name
from .time_fmt import relative_time

BAND_GLYPH = {"HOT": "●", "WARM": "○", "OPP": "·"}

_SEPARATOR = "─" * 57

_EXCLUSIVITY_PARAGRAPH = (
    "Deze lead is uitsluitend naar u verzonden. De casus blijft\n"
    "toegewezen zolang u reageert; bij geen reactie binnen 5 werkdagen\n"
    "vervalt het toegewezen-zijn."
)

_DISPUTE_TEMPLATE = (
    "Onjuist iets aan deze lead? Antwoord op deze e-mail.\n"
    "{first} beoordeelt persoonlijk binnen één werkdag.\n"
    "Bij gegrond dispuut: credit op uw account."
)

_BRAND_FOOTER = "Lead Radar  ·  case {case_id}"


def _installer_first_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return parts[0] if parts else "installateur"


def _bron_line(routed: RoutedLead, *, now: datetime) -> str:
    rl = routed.reviewed_lead
    if is_decayed(rl.captured_at, now=now) and rl.archive_url:
        return "open snapshot (gearchiveerd) ↗  · DECAYED"
    host = rl.source_url.split("://", 1)[-1].split("/", 1)[0]
    return f"open bron ↗  ({host})"


def render_text(routed: RoutedLead, *, now: datetime) -> str:
    rl = routed.reviewed_lead
    inst = routed.installer

    reviewer_first = reviewer_first_name(rl.reviewer_name)
    installer_first = _installer_first_name(inst.contact_name)
    platform_titled = rl.source_platform.title()
    captured_rel = relative_time(rl.captured_at, now=now)
    reviewed_rel = relative_time(rl.reviewed_at, now=now)
    band = rl.confidence_band
    glyph = BAND_GLYPH[band]
    bron = _bron_line(routed, now=now)

    opening = rl.opening_override or build_opening(
        installer_first=installer_first,
        platform=rl.source_platform,
        band=band,
    )

    return (
        f"{opening}\n"
        "\n"
        f"{_SEPARATOR}\n"
        "\n"
        f'  "{rl.snippet}"\n'
        "\n"
        f"  vastgelegd vanuit {platform_titled}, {captured_rel}\n"
        f"  {bron}\n"
        "\n"
        f"  band:  {glyph}  {band}\n"
        f"  reden: {rl.band_reason}\n"
        "\n"
        f"{_SEPARATOR}\n"
        "\n"
        f"gereviewd door  {rl.reviewer_name}  ·  {reviewed_rel}\n"
        f"                {rl.reviewer_email}\n"
        "\n"
        f"{_SEPARATOR}\n"
        "\n"
        f"{_EXCLUSIVITY_PARAGRAPH}\n"
        "\n"
        f"{_DISPUTE_TEMPLATE.format(first=reviewer_first)}\n"
        "\n"
        f"{reviewer_first}\n"
        "\n"
        f"{_SEPARATOR}\n"
        "\n"
        f"{_BRAND_FOOTER.format(case_id=routed.case_id)}\n"
    )
