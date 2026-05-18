"""Lead Radar delivery layer (Receipt Artifact v0).

Turns one APPROVED reviewed-lead into one email receipt per doctrine v0.1
and spec docs/superpowers/specs/2026-05-18-receipt-artifact-v0-design.md.

Founder-decisions (frozen 2026-05-18):
    Q1 = A   email-only V0, no web permalink, no Telegram mirror
    Q2 = A   reviewer surface: name + reply-email only (no photo, no handle)
    Q3 = A   case-id visible in footer as LR-YYYY-MM-DD-NNNN
    Q4 = A   explicit operational exclusivity sentence in footer
"""

from .config import DeliveryConfig, load_config
from .dispatcher import DispatchSummary, dispatch
from .model import Installer, Receipt, ReviewedLead, RoutedLead

__all__ = [
    "DeliveryConfig",
    "DispatchSummary",
    "Installer",
    "Receipt",
    "ReviewedLead",
    "RoutedLead",
    "dispatch",
    "load_config",
]
