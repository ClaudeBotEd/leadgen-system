"""HTML alternative renderer.

Inline styles only (email-client safety). Three colour roles:
  background:    tinted near-white
  accent (HOT):  warm operational red-orange
  muted (OPP):   neutral gray

No images, no scripts, no <style> block, no Tailwind classnames.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from .decay import is_decayed
from .model import RoutedLead
from .opening import build_opening
from .preheader import reviewer_first_name
from .time_fmt import relative_time

_BAND_GLYPH = {"HOT": "●", "WARM": "○", "OPP": "·"}
_BAND_COLOR = {
    "HOT": "#b04a2f",
    "WARM": "#8a6a3b",
    "OPP": "#6e6e6e",
}

_BG = "#faf9f7"
_INK = "#1a1a1a"
_DIM = "#6e6e6e"
_RULE = "#d4d4d0"
_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif"
_MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def _style(rules: dict) -> str:
    return ";".join(f"{k}:{v}" for k, v in rules.items())


def _installer_first(full: str) -> str:
    parts = full.strip().split()
    return parts[0] if parts else "installateur"


def render_html(routed: RoutedLead, *, now: datetime) -> str:
    rl = routed.reviewed_lead
    inst = routed.installer
    band = rl.confidence_band
    band_color = _BAND_COLOR[band]
    glyph = _BAND_GLYPH[band]

    captured_rel = relative_time(rl.captured_at, now=now)
    reviewed_rel = relative_time(rl.reviewed_at, now=now)
    platform_titled = rl.source_platform.title()
    reviewer_first = reviewer_first_name(rl.reviewer_name)
    installer_first = _installer_first(inst.contact_name)
    host = rl.source_url.split("://", 1)[-1].split("/", 1)[0]

    decayed = is_decayed(rl.captured_at, now=now) and rl.archive_url
    if decayed:
        source_href = rl.archive_url
        source_label = "open snapshot (gearchiveerd)"
        source_extra = f" <span style=\"{_style({'color': _DIM, 'margin-left': '8px'})}\">DECAYED</span>"
    else:
        source_href = rl.source_url
        source_label = "open bron"
        source_extra = ""

    opening = rl.opening_override or build_opening(
        installer_first=installer_first,
        platform=rl.source_platform,
        band=band,
    )

    body_style = _style(
        {
            "font-family": _SANS,
            "background": _BG,
            "color": _INK,
            "line-height": "1.55",
            "margin": "0",
            "padding": "32px 24px",
        }
    )
    wrapper = _style({"max-width": "640px", "margin": "0 auto"})
    rule = _style({"border": "0", "border-top": f"1px solid {_RULE}", "margin": "24px 0"})
    quote = _style(
        {
            "font-size": "17px",
            "line-height": "1.6",
            "padding": "0 8px",
            "margin": "0 0 16px 0",
        }
    )
    meta = _style({"font-size": "14px", "color": _DIM, "margin": "0"})
    band_row = _style({"font-size": "15px", "margin": "16px 0 0 0"})
    band_mark = _style({"color": band_color, "font-size": "16px", "margin-right": "8px"})
    sig = _style({"font-size": "14px", "color": _INK, "margin": "0"})
    case_style = _style({"font-family": _MONO, "font-size": "13px", "color": _DIM})
    link = _style({"color": _INK, "text-decoration": "underline"})

    snippet_html = escape(rl.snippet)
    reason_html = escape(rl.band_reason)
    opening_html = escape(opening).replace("\n", "<br>")

    return (
        "<!doctype html>"
        '<html lang="nl"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Lead Radar receipt</title>"
        "</head>"
        f'<body style="{body_style}">'
        f'<div style="{wrapper}">'
        f'<p style="{_style({"margin": "0 0 16px 0"})}">{opening_html}</p>'
        f'<hr style="{rule}">'
        f'<blockquote style="{quote}">&ldquo;{snippet_html}&rdquo;</blockquote>'
        f'<p style="{meta}">vastgelegd vanuit {escape(platform_titled)}, {escape(captured_rel)}<br>'
        f'<a href="{escape(source_href)}" target="_blank" rel="noopener" style="{link}">{escape(source_label)} ↗</a> '
        f'<span style="{_style({"color": _DIM})}">({escape(host)})</span>{source_extra}</p>'
        f'<p style="{band_row}">band: <span style="{band_mark}">{glyph}</span>{escape(band)}<br>'
        f'<span style="{_style({"color": _DIM})}">reden:</span> {reason_html}</p>'
        f'<hr style="{rule}">'
        f'<p style="{sig}">gereviewd door <strong>{escape(rl.reviewer_name)}</strong> &middot; {escape(reviewed_rel)}<br>'
        f'<a href="mailto:{escape(rl.reviewer_email)}" style="{link}">{escape(rl.reviewer_email)}</a></p>'
        f'<hr style="{rule}">'
        f'<p style="{meta}">Deze lead is uitsluitend naar u verzonden. De casus blijft toegewezen zolang u reageert; bij geen reactie binnen 5 werkdagen vervalt het toegewezen-zijn.</p>'
        f'<p style="{_style({"margin": "16px 0", "font-size": "14px"})}">Onjuist iets aan deze lead? Antwoord op deze e-mail. {escape(reviewer_first)} beoordeelt persoonlijk binnen één werkdag. Bij gegrond dispuut: credit op uw account.</p>'
        f'<p style="{_style({"margin": "24px 0 0 0", "font-size": "14px"})}">{escape(reviewer_first)}</p>'
        f'<hr style="{rule}">'
        f'<p style="{case_style}">Lead Radar &middot; case {escape(routed.case_id)}</p>'
        "</div></body></html>"
    )
