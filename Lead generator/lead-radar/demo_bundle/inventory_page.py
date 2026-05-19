"""Render inventory snapshot HTML page.

Eén pagina, single-file (inline CSS in <style>), geen JS. Tabel met
huidige inventory + decay countdown + intent badge + source badge.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from html import escape
from pathlib import Path


_STYLE = """
body{font:15px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;
  background:#faf9f7;color:#1a1a1a;margin:0;padding:32px;}
h1{font-size:22px;margin:0 0 4px;}
.snapshot{color:#6e6e6e;font-size:13px;margin-bottom:24px;}
table{border-collapse:collapse;width:100%;background:#fff;
  border:1px solid #d4d4d0;border-radius:6px;overflow:hidden;}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #ebebe7;
  font-size:14px;vertical-align:top;}
th{background:#f3f1ed;font-weight:600;font-size:12px;
  text-transform:uppercase;letter-spacing:0.04em;color:#4a4a45;}
tr:last-child td{border-bottom:none;}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;
  font-size:12px;font-weight:600;}
.hot{background:#fde6df;color:#b04a2f;}
.warm{background:#f5ecdc;color:#8a6a3b;}
.src-public{background:#e6efe6;color:#3f6b3f;}
.src-closed{background:#ece6f4;color:#5b3f8a;}
.src-paste{background:#eee;color:#555;}
.empty{padding:48px;text-align:center;color:#6e6e6e;background:#fff;
  border:1px solid #d4d4d0;border-radius:6px;}
footer{margin-top:32px;color:#6e6e6e;font-size:12px;}
"""


def _intent_badge(intent: str) -> str:
    cls = "hot" if intent == "HOT" else "warm"
    return f'<span class="badge {cls}">{escape(intent)}</span>'


def _source_badge(source: str) -> str:
    cls = {
        "apify_public": "src-public",
        "burner_closed": "src-closed",
        "paste": "src-paste",
    }.get(source, "src-paste")
    label = {
        "apify_public": "publiek",
        "burner_closed": "besloten",
        "paste": "paste",
    }.get(source, source)
    return f'<span class="badge {cls}">{escape(label)}</span>'


def _humanize_relative(
    iso_str: str, snapshot_at: datetime, *, future: bool
) -> str:
    if not iso_str:
        return "—"
    try:
        when = datetime.fromisoformat(iso_str)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
    except ValueError:
        return iso_str
    delta = when - snapshot_at if future else snapshot_at - when
    secs = int(delta.total_seconds())
    if secs < 0:
        return "verlopen" if future else "—"
    days = secs // 86400
    if days >= 1:
        return f"over {days}d" if future else f"{days}d geleden"
    hours = secs // 3600
    if hours >= 1:
        return f"over {hours}u" if future else f"{hours}u geleden"
    return "nu" if future else "zojuist"


def render_inventory_html(
    *,
    inventory_path: str | Path,
    snapshot_at: datetime,
) -> str:
    inventory_path = Path(inventory_path)
    rows: list[dict] = []
    if inventory_path.exists():
        with inventory_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

    snapshot_label = snapshot_at.strftime("%d %B %Y, %H:%M UTC")
    header_html = (
        f'<h1>Lead-radar — huidige voorraad</h1>'
        f'<div class="snapshot">Snapshot: {escape(snapshot_label)}'
        f' &middot; {len(rows)} lead(s)</div>'
    )

    if not rows:
        body_html = '<div class="empty">Pool is leeg — Geen leads beschikbaar.</div>'
    else:
        cells_html = []
        for r in rows:
            cells_html.append(
                "<tr>"
                f"<td><code>{escape(r.get('lead_id', ''))}</code></td>"
                f"<td>{escape(r.get('niche', ''))}</td>"
                f"<td>{escape(r.get('region_nl', '').replace('|', ' / '))}</td>"
                f"<td>{_intent_badge(r.get('intent_strength', ''))}</td>"
                f"<td>{_humanize_relative(r.get('captured_at', ''), snapshot_at, future=False)}</td>"
                f"<td>{_humanize_relative(r.get('expires_at', ''), snapshot_at, future=True)}</td>"
                f"<td>{_source_badge(r.get('source_class', ''))}</td>"
                "</tr>"
            )
        body_html = (
            '<table>'
            '<thead><tr>'
            '<th>Lead-ID</th><th>Niche</th><th>Regio</th>'
            '<th>Intent</th><th>Gezien</th><th>Verloopt</th><th>Bron</th>'
            '</tr></thead><tbody>'
            + "".join(cells_html)
            + '</tbody></table>'
        )

    return (
        '<!doctype html><html lang="nl"><head>'
        '<meta charset="utf-8">'
        '<title>Lead-radar voorraad</title>'
        f'<style>{_STYLE}</style>'
        '</head><body>'
        + header_html
        + body_html
        + '<footer>Doctrine v0.2 &middot; provenance-gefilterd, decay-bewust.</footer>'
        '</body></html>'
    )
