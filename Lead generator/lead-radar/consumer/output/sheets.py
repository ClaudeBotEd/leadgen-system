"""Google Sheets sync — drie tabs voor ALL/HOT/OPPORTUNITIES.

Tabs:
  - HOT LEADS      : score >= 80   (CONTACT NU)
  - ALL LEADS      : score >= 70   (HOT + WARM)
  - OPPORTUNITIES  : score 60-69   (WARM + CHECK)

Kolommen (in deze volgorde — nieuwe velden zijn appended om
backwards-compatibel te blijven met al gevulde sheets):

  score | status | actie | stad | niche | samenvatting | bron |
  link | gevonden_op | notitie | prioriteit |
  provincie | bericht_voorstel | contacted_at | installateur

Mapping per score (user-spec workflow status, lowercase):
  >= 80  -> status=new, actie='contact nu'   (HOT + ALL tabs)
  70-79  -> status=new, actie='later'        (ALL tab)
  60-69  -> status=new, actie='skip'         (OPPORTUNITIES tab)
  <  60  -> NIET geexporteerd

`status` houdt de workflow van de user bij:
  new -> contacted -> replied -> qualified -> sold
Nieuwe leads krijgen 'new'.  Bestaande rijen (ook met legacy
HOT/WARM/COLD-waardes) worden niet aangeraakt.

Idempotent:
  - dedup op `link` cross-tab (een lead staat hooguit 1 tab in)
  - bij re-find met hogere score: update score + prioriteit +
    bericht_voorstel in dezelfde tab.  User-velden (status,
    contacted_at, notitie, installateur) blijven onaangetast.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .. import Lead
from ..processor import (
    smart_summary,
    has_urgency,
    detect_province,
    generate_message,
)

# Tijd in Sheets-cellen schrijven we als NL-lokaal — operator denkt in CET,
# niet in UTC. Naive datetime.now() gaf UTC-tijd → rond middernacht NL
# kwam de verkeerde datum in de 'gevonden_op' kolom.
_NL_TZ = ZoneInfo("Europe/Amsterdam")

log = logging.getLogger("consumer.output.sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Bestaande 11 kolommen + 4 nieuwe (appended om backwards-compatibel te zijn
# met al gevulde sheets — niet reordering, geen data-shift voor bestaande
# rijen).
HEADERS = [
    "score", "status", "actie", "stad", "niche", "samenvatting",
    "bron", "link", "gevonden_op", "notitie", "prioriteit",
    # --- v2 workflow fields ---
    "provincie", "bericht_voorstel", "contacted_at", "installateur",
]
HOT_TAB = "HOT LEADS"
ALL_TAB = "ALL LEADS"
OPP_TAB = "OPPORTUNITIES"

HOT_THRESHOLD = 80   # >= 80  -> 'contact nu'
WARM_THRESHOLD = 70  # 70-79  -> 'later'
OPP_THRESHOLD = 60   # 60-69  -> 'skip' (zichtbaar in OPPORTUNITIES)
# < 60: niet exporteren

DEFAULT_WORKFLOW_STATUS = "new"


def status_from_score(score: int) -> str:
    """LEGACY tier-label.  Niet meer gebruikt voor nieuwe rijen — daar
    schrijven we DEFAULT_WORKFLOW_STATUS ('new').  Behouden voor callers
    die de oude functie nog importeren.
    """
    if score >= HOT_THRESHOLD:
        return "HOT"
    if score >= OPP_THRESHOLD:
        return "WARM"
    return "COLD"


def action_from_score(score: int) -> str:
    """User-spec: 'contact nu' | 'later' | 'skip'."""
    if score >= HOT_THRESHOLD:
        return "contact nu"
    if score >= WARM_THRESHOLD:
        return "later"
    return "skip"


def action_from_status(status: str) -> str:
    """Backwards-compat helper voor oude callers (HOT/WARM/COLD input)."""
    return {
        "HOT": "contact nu",
        "WARM": "later",
        "COLD": "skip",
        "new": "later",
    }.get(status, "skip")


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
    return datetime.now(_NL_TZ).strftime("%Y-%m-%d %H:%M")


def lead_to_row(lead: Lead) -> list:
    """Bouwt een rij in HEADERS-volgorde (15 kolommen)."""
    urgency = has_urgency(f"{lead.title} {lead.text}")
    summary = smart_summary(
        text=lead.text or "",
        title=lead.title or "",
        city=lead.city,
        niche=lead.niche,
    )
    bericht = generate_message(
        niche=lead.niche,
        city=lead.city,
        text=lead.text or "",
        title=lead.title or "",
    )
    provincie = detect_province(lead.city) or ""
    found_at = lead.captured_at or _now_str()
    if "T" in found_at:
        found_at = found_at.replace("T", " ")[:16]
    return [
        int(lead.score),                           # score
        DEFAULT_WORKFLOW_STATUS,                   # status — workflow
        action_from_score(lead.score),             # actie
        (lead.city or "").strip(),                 # stad
        lead.niche,                                # niche
        summary,                                   # samenvatting
        lead.source,                               # bron
        lead.url,                                  # link
        found_at,                                  # gevonden_op
        "",                                        # notitie  (user)
        priority_from_score(lead.score, urgency),  # prioriteit
        provincie,                                 # provincie
        bericht,                                   # bericht_voorstel
        "",                                        # contacted_at  (user)
        "",                                        # installateur  (user)
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
    """Open of maak tab aan + migreer header-row idempotent.

    Migratie-regels:
      - Te smal (col_count < len(headers))? -> resize_columns.
      - Header-row klopt niet? -> overschrijf met `headers`.  Bestaande
        data-rijen blijven staan; nieuwe kolommen aan de rechterkant zijn
        gewoon leeg voor oude rijen — geen data-shift.
    """
    import gspread
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        kwargs = {"title": title, "rows": 2000, "cols": max(15, len(headers))}
        if index is not None:
            kwargs["index"] = index
        ws = spreadsheet.add_worksheet(**kwargs)

    # Zorg dat er genoeg kolommen zijn voor de huidige HEADERS (migratie
    # van 11 → 15 kolommen op bestaande sheets).
    if ws.col_count < len(headers):
        try:
            ws.resize(cols=len(headers))
        except Exception as e:
            log.warning("Resize naar %d kolommen faalde: %s", len(headers), e)

    current = ws.row_values(1)
    if current != headers:
        last_col_letter = _col_letter(len(headers) - 1)
        ws.update(values=[headers], range_name=f"A1:{last_col_letter}1")
        try:
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


def _existing_index(ws) -> dict[str, tuple[int, int]]:
    """Return {link: (row_index_1based, current_score)} voor in-place updates.

    Slaat lege regels en regels zonder link over.  Score wordt geparsed als
    int; niet-numeriek → 0 (zodat een nieuwe geldige score altijd wint).
    """
    headers = ws.row_values(1)
    if "link" not in headers or "score" not in headers:
        return {}
    link_idx = headers.index("link")
    score_idx = headers.index("score")
    rows = ws.get_all_values()
    out: dict[str, tuple[int, int]] = {}
    for i, row in enumerate(rows[1:], start=2):  # row 1 = header
        if len(row) <= max(link_idx, score_idx):
            continue
        link = (row[link_idx] or "").strip()
        if not link:
            continue
        try:
            score = int(row[score_idx])
        except (ValueError, TypeError):
            score = 0
        out[link] = (i, score)
    return out


def _col_letter(col_index_0based: int) -> str:
    """0 → A, 1 → B, …, 26 → AA."""
    n = col_index_0based
    s = ""
    while True:
        s = chr(ord("A") + (n % 26)) + s
        n = n // 26 - 1
        if n < 0:
            break
    return s


def _update_existing_cells(ws, row_idx: int, lead: Lead) -> None:
    """Update alleen de SYSTEEM-velden (score, prioriteit, bericht_voorstel,
    samenvatting, gevonden_op).  Laat user-velden (status, contacted_at,
    notitie, installateur) met rust.
    """
    headers = ws.row_values(1)
    urgency = has_urgency(f"{lead.title} {lead.text}")
    summary = smart_summary(
        text=lead.text or "",
        title=lead.title or "",
        city=lead.city,
        niche=lead.niche,
    )
    bericht = generate_message(
        niche=lead.niche,
        city=lead.city,
        text=lead.text or "",
        title=lead.title or "",
    )
    found_at = _now_str()
    updates: dict[str, object] = {
        "score": int(lead.score),
        "actie": action_from_score(lead.score),
        "samenvatting": summary,
        "prioriteit": priority_from_score(lead.score, urgency),
        "bericht_voorstel": bericht,
        "gevonden_op": found_at,
    }
    batch = []
    for col_name, value in updates.items():
        if col_name not in headers:
            continue
        letter = _col_letter(headers.index(col_name))
        batch.append({"range": f"{letter}{row_idx}", "values": [[value]]})
    if batch:
        try:
            ws.batch_update(batch, value_input_option="USER_ENTERED")
        except Exception as e:
            log.warning("Update bestaande rij %d faalde: %s", row_idx, e)


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
    """Push leads naar Google Sheets.

    Verdeelt leads over 3 tabs:
      HOT LEADS    : score >= 80   (CONTACT NU)
      ALL LEADS    : score >= 70   (HOT + WARM)
      OPPORTUNITIES: score 60-69   (WARM + CHECK)
    Leads < 60 worden niet gesynced.

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

    print(f"Opening spreadsheet ID: {sid}", flush=True)
    print(f"Credentials path: {creds_path}", flush=True)
    client = _open_client(creds_path)
    try:
        ss = client.open_by_key(sid)
    except Exception as e:
        raise RuntimeError(
            f"Kon spreadsheet {sid!r} niet openen. "
            f"Check (1) ID klopt, (2) service-account email is gedeeld als Editor. "
            f"Origineel: {e}"
        ) from e

    # HOT eerst (index 0), ALL als 2de, OPPORTUNITIES als 3de.
    hot_ws = _open_or_create_worksheet(ss, HOT_TAB, HEADERS, index=0)
    all_ws = _open_or_create_worksheet(ss, ALL_TAB, HEADERS, index=1)
    opp_ws = _open_or_create_worksheet(ss, OPP_TAB, HEADERS, index=2)

    # Bouw indices PER TAB + cross-tab set zodat 1 lead nooit in twee tabs
    # tegelijk komt en we score-updates kunnen doen.
    idx_all = _existing_index(all_ws)
    idx_hot = _existing_index(hot_ws)
    idx_opp = _existing_index(opp_ws)
    cross_tab = set(idx_all.keys()) | set(idx_hot.keys()) | set(idx_opp.keys())

    # Filter <60 weg + sorteer
    qualified = [l for l in leads if l.score >= OPP_THRESHOLD]
    qualified.sort(key=lambda l: l.score, reverse=True)

    new_all_rows: list[list] = []
    new_hot_rows: list[list] = []
    new_opp_rows: list[list] = []
    updated_count = 0

    for l in qualified:
        url_key = (l.url or "").strip()
        if not url_key:
            continue

        target = (
            HOT_TAB if l.score >= HOT_THRESHOLD
            else ALL_TAB if l.score >= WARM_THRESHOLD
            else OPP_TAB
        )
        target_idx = (
            idx_hot if target == HOT_TAB
            else idx_all if target == ALL_TAB
            else idx_opp
        )
        target_ws = (
            hot_ws if target == HOT_TAB
            else all_ws if target == ALL_TAB
            else opp_ws
        )

        # 1) Same-tab match → eventueel score+bericht updaten, geen duplicaat
        if url_key in target_idx:
            row_i, old_score = target_idx[url_key]
            if l.score > old_score:
                _update_existing_cells(target_ws, row_i, l)
                updated_count += 1
            continue

        # 2) Cross-tab match → niet dupliceren, niet verplaatsen.
        # (Score-shift naar andere tier wordt aan de user overgelaten.)
        if url_key in cross_tab:
            continue

        # 3) Echte nieuwe lead
        row = lead_to_row(l)
        if target == HOT_TAB:
            new_hot_rows.append(row)
            # HOT-leads horen ook in ALL als ALL nog niet bekend (zodat
            # ALL het overzicht blijft).  Idempotent: alleen 1x via cross_tab
            # check hierboven.
            if url_key not in idx_all:
                new_all_rows.append(row)
        elif target == ALL_TAB:
            new_all_rows.append(row)
        else:
            new_opp_rows.append(row)
        cross_tab.add(url_key)

    if new_all_rows:
        all_ws.append_rows(new_all_rows, value_input_option="USER_ENTERED")
        log.info("Sheets: +%d leads in '%s'", len(new_all_rows), ALL_TAB)
    if new_hot_rows:
        hot_ws.append_rows(new_hot_rows, value_input_option="USER_ENTERED")
        log.info("Sheets: +%d leads in '%s'", len(new_hot_rows), HOT_TAB)
    if new_opp_rows:
        opp_ws.append_rows(new_opp_rows, value_input_option="USER_ENTERED")
        log.info("Sheets: +%d leads in '%s'", len(new_opp_rows), OPP_TAB)
    if updated_count:
        log.info("Sheets: %d bestaande leads geupdate (hogere score)", updated_count)

    _sort_by_score_desc(all_ws)
    _sort_by_score_desc(hot_ws)
    _sort_by_score_desc(opp_ws)

    url = f"https://docs.google.com/spreadsheets/d/{sid}/edit"
    return {
        "all_added": len(new_all_rows),
        "hot_added": len(new_hot_rows),
        "opp_added": len(new_opp_rows),
        "updated": updated_count,
        "all_total": len(idx_all) + len(new_all_rows),
        "hot_total": len(idx_hot) + len(new_hot_rows),
        "opp_total": len(idx_opp) + len(new_opp_rows),
        "qualified": len(qualified),
        "rejected_low_score": len(leads) - len(qualified),
        "spreadsheet_url": url,
    }
