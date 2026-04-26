"""Google Sheets sync — pusht Lead-list naar een gedeelde spreadsheet.

Twee tabs:
  - ALL LEADS  : alle leads (dedup op `link`)
  - TOP LEADS  : score >= 70 only

Kolommen: score | status | stad | niche | samenvatting | actie | bron | link

Gebruikt service-account auth (gspread + google-auth) — geen OAuth flow,
geen browser pop-up.  Setup: zie consumer/README.md "Google Sheets sync".

Idempotent: bestaande rijen worden niet dubbel toegevoegd (sleutel = link).
Sorteert na append op score desc.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .. import Lead

log = logging.getLogger("consumer.output.sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = ["score", "status", "stad", "niche", "samenvatting", "actie", "bron", "link"]
ALL_TAB = "ALL LEADS"
TOP_TAB = "TOP LEADS"
TOP_THRESHOLD = 70


def status_from_score(score: int) -> str:
    if score >= 70:
        return "HOT"
    if score >= 40:
        return "WARM"
    return "COLD"


def action_from_status(status: str) -> str:
    return {"HOT": "CONTACT", "WARM": "LATER", "COLD": "SKIP"}.get(status, "SKIP")


def make_summary(lead: Lead, max_chars: int = 140) -> str:
    """Eén korte zin: pak de samenvatting (cleaner) of de titel + eerste woorden tekst."""
    base = (lead.summary or lead.title or "").strip()
    if not base and lead.text:
        base = lead.text.strip()
    base = " ".join(base.split())
    if len(base) <= max_chars:
        return base
    cut = base[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars * 0.6:
        cut = cut[:last_space]
    return cut.rstrip(" ,.;:") + "…"


def lead_to_row(lead: Lead) -> list:
    status = status_from_score(lead.score)
    return [
        int(lead.score),
        status,
        (lead.city or "").strip(),
        lead.niche,
        make_summary(lead),
        action_from_status(status),
        lead.source,
        lead.url,
    ]


def _resolve_credentials_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("LEAD_RADAR_GS_CREDENTIALS")
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parents[2] / ".credentials" / "google_sheets.json"


def _resolve_spreadsheet_id(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    return os.environ.get("LEAD_RADAR_SPREADSHEET_ID")


def _open_client(credentials_path: Path):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        raise RuntimeError(
            "gspread/google-auth niet geinstalleerd.  "
            "Run: pip install gspread google-auth"
        ) from e
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Service-account JSON niet gevonden: {credentials_path}.  "
            "Zie consumer/README.md sectie 'Google Sheets sync' voor setup."
        )
    creds = Credentials.from_service_account_file(str(credentials_path), scopes=SCOPES)
    return gspread.authorize(creds)


def _open_or_create_worksheet(spreadsheet, title: str, headers: list[str]):
    import gspread
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=2000, cols=max(10, len(headers)))
    current = ws.row_values(1)
    if current != headers:
        ws.update(values=[headers], range_name="A1")
        try:
            ws.format("A1:Z1", {"textFormat": {"bold": True}})
        except Exception:
            pass
    return ws


def _existing_links(ws) -> set[str]:
    headers = ws.row_values(1)
    if "link" not in headers:
        return set()
    col_idx = headers.index("link") + 1  # 1-based
    values = ws.col_values(col_idx)[1:]
    return {v.strip() for v in values if v and v.strip()}


def _sort_by_score_desc(ws) -> None:
    headers = ws.row_values(1)
    if "score" not in headers:
        return
    col_idx = headers.index("score") + 1
    rowcount = max(2, ws.row_count)
    try:
        ws.sort((col_idx, "des"), range=f"A2:H{rowcount}")
    except Exception as e:
        log.warning("Sorteren faalde (gaan door): %s", e)


def sync_to_sheets(
    leads: list[Lead],
    *,
    spreadsheet_id: str | None = None,
    credentials_path: str | Path | None = None,
) -> dict:
    """Push leads naar Google Sheets.  Idempotent (dedup op `link`).

    Returns: {'all_added', 'top_added', 'all_total', 'top_total', 'spreadsheet_url'}.
    Raises bij missende credentials / spreadsheet_id.
    """
    sid = _resolve_spreadsheet_id(spreadsheet_id)
    if not sid:
        raise RuntimeError(
            "Geen spreadsheet ID — geef --spreadsheet-id of zet "
            "LEAD_RADAR_SPREADSHEET_ID env var."
        )
    creds_path = _resolve_credentials_path(
        str(credentials_path) if credentials_path else None
    )

    client = _open_client(creds_path)
    try:
        ss = client.open_by_key(sid)
    except Exception as e:
        raise RuntimeError(
            f"Kon spreadsheet {sid!r} niet openen.  "
            f"Check (1) ID klopt, (2) service-account email is gedeeld als Editor.  "
            f"Origineel: {e}"
        ) from e

    all_ws = _open_or_create_worksheet(ss, ALL_TAB, HEADERS)
    top_ws = _open_or_create_worksheet(ss, TOP_TAB, HEADERS)

    seen_all = _existing_links(all_ws)
    seen_top = _existing_links(top_ws)

    sorted_leads = sorted(leads, key=lambda l: l.score, reverse=True)

    new_all = [
        lead_to_row(l) for l in sorted_leads
        if (l.url or "").strip() and l.url not in seen_all
    ]
    new_top = [
        lead_to_row(l) for l in sorted_leads
        if l.score >= TOP_THRESHOLD and (l.url or "").strip() and l.url not in seen_top
    ]

    if new_all:
        all_ws.append_rows(new_all, value_input_option="USER_ENTERED")
        log.info("Sheets: %d nieuwe leads toegevoegd aan '%s'", len(new_all), ALL_TAB)
    if new_top:
        top_ws.append_rows(new_top, value_input_option="USER_ENTERED")
        log.info("Sheets: %d nieuwe leads toegevoegd aan '%s'", len(new_top), TOP_TAB)

    _sort_by_score_desc(all_ws)
    _sort_by_score_desc(top_ws)

    url = f"https://docs.google.com/spreadsheets/d/{sid}/edit"
    return {
        "all_added": len(new_all),
        "top_added": len(new_top),
        "all_total": len(seen_all) + len(new_all),
        "top_total": len(seen_top) + len(new_top),
        "spreadsheet_url": url,
    }
