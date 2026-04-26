"""Google Sheets sync — pusht alleen score>=70 leads.

Tabs:
  - HOT LEADS  : score >= 80 (CONTACT NU)
  - ALL LEADS  : score >= 70 (HOT + WARM)

Kolommen: score | status | actie | stad | niche | samenvatting | bron |
          link | gevonden_op | notitie | prioriteit

Status mapping per spec:
  >= 80  -> HOT  + CONTACT  (priority 4-5)
  70-79  -> WARM + LATER    (priority 3)
  <  70  -> NIET geexporteerd

Idempotent: dedup op `link`, sortering op score desc.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from .. import Lead
from ..processor import smart_summary, has_urgency

log = logging.getLogger("consumer.output.sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "score", "status", "actie", "stad", "niche", "samenvatting",
    "bron", "link", "gevonden_op", "notitie", "prioriteit",
]
HOT_TAB = "HOT LEADS"
ALL_TAB = "ALL LEADS"

HOT_THRESHOLD = 80   # score >= 80 -> HOT
WARM_THRESHOLD = 70  # 70-79 -> WARM, <70 -> niet exporteren


def status_from_score(score: int) -> str:
    if score >= HOT_THRESHOLD:
        return "HOT"
    if score >= WARM_THRESHOLD:
        return "WARM"
    return "COLD"


def action_from_status(status: str) -> str:
    return {"HOT": "CONTACT", "WARM": "LATER", "COLD": "SKIP"}.get(status, "SKIP")


def priority_from_score(score: int, urgency: bool) -> int:
    """1-5, hoger = belangrijker. score >= 95 + urgency = 5."""
    if score >= 95 and urgency:
        return 5
    if score >= 90:
        return 5
    if score >= 80:
        return 4
    if score >= 75:
        return 3
    if score >= 70:
        return 2
    return 1


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def lead_to_row(lead: Lead) -> list:
    status = status_from_score(lead.score)
    urgency = has_urgency(f"{lead.title} {lead.text}")
    summary = smart_summary(
        text=lead.text or "",
        title=lead.title or "",
        city=lead.city,
        niche=lead.niche,
    )
    found_at = lead.captured_at or _now_str()
    # Voor leesbaarheid in de Sheet: kort de timestamp tot 'YYYY-MM-DD HH:MM'
    if "T" in found_at:
        found_at = found_at.replace("T", " ")[:16]
    return [
        int(lead.score),
        status,
        action_from_status(status),
        (lead.city or "").strip(),
        lead.niche,
        summary,
        lead.source,
        lead.url,
        found_at,
        "",  # notitie — leeg voor de gebruiker
        priority_from_score(lead.score, urgency),
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
            "gspread/google-auth niet geinstalleerd. "
            "Run: pip install gspread google-auth"
        ) from e
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Service-account JSON niet gevonden: {credentials_path}. "
            "Zie consumer/README.md → 'Google Sheets sync'."
        )
    creds = Credentials.from_service_account_file(str(credentials_path), scopes=SCOPES)
    return gspread.authorize(creds)


def _open_or_create_worksheet(spreadsheet, title: str, headers: list[str], *, index: int | None = None):
    import gspread
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        kwargs = {"title": title, "rows": 2000, "cols": max(15, len(headers))}
        if index is not None:
            kwargs["index"] = index
        ws = spreadsheet.add_worksheet(**kwargs)

    current = ws.row_values(1)
    if current != headers:
        ws.update(values=[headers], range_name="A1")
        try:
            last_col_letter = chr(ord("A") + len(headers) - 1)
            ws.format(f"A1:{last_col_letter}1", {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.94, "green": 0.94, "blue": 0.94},
            })
            ws.freeze(rows=1)
        except Exception:
            pass
    return ws


def _existing_links(ws) -> set[str]:
    headers = ws.row_values(1)
    if "link" not in headers:
        return set()
    col_idx = headers.index("link") + 1
    values = ws.col_values(col_idx)[1:]
    return {v.strip() for v in values if v and v.strip()}


def _sort_by_score_desc(ws) -> None:
    headers = ws.row_values(1)
    if "score" not in headers:
        return
    col_idx = headers.index("score") + 1
    rowcount = max(2, ws.row_count)
    last_col_letter = chr(ord("A") + len(headers) - 1)
    try:
        ws.sort((col_idx, "des"), range=f"A2:{last_col_letter}{rowcount}")
    except Exception as e:
        log.warning("Sorteren faalde (gaan door): %s", e)


def sync_to_sheets(
    leads: list[Lead],
    *,
    spreadsheet_id: str | None = None,
    credentials_path: str | Path | None = None,
) -> dict:
    """Push leads naar Google Sheets.  Filtert intern op score >= 70.

    Returns: {'all_added','hot_added','all_total','hot_total','spreadsheet_url'}.
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
            f"Kon spreadsheet {sid!r} niet openen. "
            f"Check (1) ID klopt, (2) service-account email is gedeeld als Editor. "
            f"Origineel: {e}"
        ) from e

    # HOT eerst (index 0), dan ALL — zo opent de Sheet standaard op HOT.
    hot_ws = _open_or_create_worksheet(ss, HOT_TAB, HEADERS, index=0)
    all_ws = _open_or_create_worksheet(ss, ALL_TAB, HEADERS, index=1)

    seen_all = _existing_links(all_ws)
    seen_hot = _existing_links(hot_ws)

    # Filter <70 weg + sorteer
    qualified = [l for l in leads if l.score >= WARM_THRESHOLD]
    qualified.sort(key=lambda l: l.score, reverse=True)

    new_all_rows = [
        lead_to_row(l) for l in qualified
        if (l.url or "").strip() and l.url not in seen_all
    ]
    new_hot_rows = [
        lead_to_row(l) for l in qualified
        if l.score >= HOT_THRESHOLD and (l.url or "").strip() and l.url not in seen_hot
    ]

    if new_all_rows:
        all_ws.append_rows(new_all_rows, value_input_option="USER_ENTERED")
        log.info("Sheets: +%d leads in '%s'", len(new_all_rows), ALL_TAB)
    if new_hot_rows:
        hot_ws.append_rows(new_hot_rows, value_input_option="USER_ENTERED")
        log.info("Sheets: +%d leads in '%s'", len(new_hot_rows), HOT_TAB)

    _sort_by_score_desc(all_ws)
    _sort_by_score_desc(hot_ws)

    url = f"https://docs.google.com/spreadsheets/d/{sid}/edit"
    return {
        "all_added": len(new_all_rows),
        "hot_added": len(new_hot_rows),
        "all_total": len(seen_all) + len(new_all_rows),
        "hot_total": len(seen_hot) + len(new_hot_rows),
        "qualified": len(qualified),
        "rejected_low_score": len(leads) - len(qualified),
        "spreadsheet_url": url,
    }
