"""Pytest conftest — voegt lead-radar/ aan sys.path zodat `consumer.*` direct importeerbaar is."""
from __future__ import annotations

import sys
from pathlib import Path

LEAD_RADAR_ROOT = Path(__file__).resolve().parent.parent
if str(LEAD_RADAR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEAD_RADAR_ROOT))
