"""Installer routing.

V0 algorithm:
  1. Filter installers by active=True
  2. Filter by region (case-insensitive exact match against installer.regions)
  3. Filter by niche (exact match against installer.niches)
  4. Pick first remaining in CSV order
  5. Before returning: confirm lead_id has no prior DELIVERED transition
     in data/lead_log.csv - exclusivity (doctrine 04.3).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional, Union

from .model import Installer, ReviewedLead

DEFAULT_LOG_PATH = Path("data/lead_log.csv")


def load_installers(path: Union[str, Path]) -> List[Installer]:
    installers: List[Installer] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("installer_id"):
                continue
            installers.append(Installer.from_csv_row(row))
    return installers


def _already_delivered(lead_id: str, log_path: Path) -> bool:
    if not log_path.exists():
        return False
    with log_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("lead_id") == lead_id and row.get("to_state") == "DELIVERED":
                return True
    return False


def pick_installer(
    reviewed_lead: ReviewedLead,
    installers: List[Installer],
    *,
    log_path: Union[str, Path] = DEFAULT_LOG_PATH,
) -> Optional[Installer]:
    log_path = Path(log_path)
    if _already_delivered(reviewed_lead.lead_id, log_path):
        return None

    region_norm = reviewed_lead.region.strip().lower()
    niche_norm = reviewed_lead.niche.strip().lower()

    for inst in installers:
        if not inst.active:
            continue
        regions = [r.strip().lower() for r in inst.regions]
        niches = [n.strip().lower() for n in inst.niches]
        if region_norm not in regions:
            continue
        if niche_norm not in niches:
            continue
        return inst
    return None
