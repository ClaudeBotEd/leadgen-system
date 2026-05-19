"""Dataclass models for the delivery layer.

ReviewedLead   - input from operator console / approved.jsonl
Installer      - installer registry row (from data/installers.csv)
RoutedLead     - reviewed_lead + installer + case_id
Receipt        - fully rendered payload ready for SMTP
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .subject import ALLOWED_BANDS, ALLOWED_NICHES

_URL_RE = re.compile(r"^https?://[^\s]+$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ALLOWED_PLATFORMS = frozenset(
    {
        "tweakers",
        "reddit",
        "facebook",
        "bouwinfo",
        "klusidee",
        "ouders",
        "other",
    }
)


def _require(value, name: str):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{name} must be non-empty")


@dataclass
class ReviewedLead:
    lead_id: str
    snippet: str
    source_url: str
    source_platform: str
    captured_at: datetime
    region: str
    niche: str
    confidence_band: str
    band_reason: str
    reviewer_name: str
    reviewer_email: str
    reviewed_at: datetime
    archive_url: Optional[str] = None
    subject_override: Optional[str] = None
    opening_override: Optional[str] = None

    def __post_init__(self):
        for name in (
            "lead_id",
            "snippet",
            "source_url",
            "source_platform",
            "region",
            "niche",
            "confidence_band",
            "band_reason",
            "reviewer_name",
            "reviewer_email",
        ):
            _require(getattr(self, name), name)
        # Header-safety guard for reviewer_name — flows into the From: header
        # (delivery/send.py:29). RFC 5322 injection via CRLF / <>: doctrine
        # §00.4 — humans are accountable, so the name field must be safe.
        forbidden = {"\n", "\r", "\x00", "<", ">"}
        if any(ch in self.reviewer_name for ch in forbidden):
            raise ValueError(
                f"reviewer_name contains forbidden characters (CRLF/null/<>): "
                f"{self.reviewer_name!r}"
            )
        if not _URL_RE.match(self.source_url):
            raise ValueError(f"source_url must be http(s) URL, got {self.source_url!r}")
        if not _EMAIL_RE.match(self.reviewer_email):
            raise ValueError(f"reviewer_email must be valid email, got {self.reviewer_email!r}")
        self.source_platform = self.source_platform.strip().lower()
        if self.source_platform not in _ALLOWED_PLATFORMS:
            raise ValueError(f"source_platform {self.source_platform!r} not in {sorted(_ALLOWED_PLATFORMS)}")
        self.niche = self.niche.strip().lower()
        if self.niche not in ALLOWED_NICHES:
            raise ValueError(f"niche {self.niche!r} not in {sorted(ALLOWED_NICHES)}")
        self.confidence_band = self.confidence_band.strip().upper()
        if self.confidence_band not in ALLOWED_BANDS:
            raise ValueError(f"confidence_band {self.confidence_band!r} not in {sorted(ALLOWED_BANDS)}")
        if self.archive_url is not None and not _URL_RE.match(self.archive_url):
            raise ValueError(f"archive_url must be http(s) URL, got {self.archive_url!r}")

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "ReviewedLead":
        captured = raw["captured_at"]
        reviewed = raw["reviewed_at"]
        return cls(
            lead_id=str(raw["lead_id"]),
            snippet=str(raw["snippet"]),
            source_url=str(raw["source_url"]),
            source_platform=str(raw["source_platform"]),
            captured_at=captured if isinstance(captured, datetime) else datetime.fromisoformat(str(captured)),
            region=str(raw["region"]),
            niche=str(raw["niche"]),
            confidence_band=str(raw["confidence_band"]),
            band_reason=str(raw["band_reason"]),
            reviewer_name=str(raw["reviewer_name"]),
            reviewer_email=str(raw["reviewer_email"]),
            reviewed_at=reviewed if isinstance(reviewed, datetime) else datetime.fromisoformat(str(reviewed)),
            archive_url=str(raw["archive_url"]) if raw.get("archive_url") else None,
            subject_override=str(raw["subject_override"]) if raw.get("subject_override") else None,
            opening_override=str(raw["opening_override"]) if raw.get("opening_override") else None,
        )


@dataclass
class Installer:
    installer_id: str
    company_name: str
    contact_name: str
    email: str
    phone: str
    city: str
    regions: List[str]
    niches: List[str]
    active: bool
    notes: str = ""

    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> "Installer":
        def split(value: str) -> List[str]:
            v = (value or "").strip()
            if not v:
                return []
            for sep in ("|", ","):
                if sep in v:
                    return [part.strip() for part in v.split(sep) if part.strip()]
            return [v]

        active_raw = (row.get("active") or "").strip().lower()
        return cls(
            installer_id=row["installer_id"].strip(),
            company_name=row.get("company_name", "").strip(),
            contact_name=row.get("contact_name", "").strip(),
            email=row.get("email", "").strip(),
            phone=row.get("phone", "").strip(),
            city=row.get("city", "").strip(),
            regions=split(row.get("regions", "")),
            niches=split(row.get("niches", "")),
            active=active_raw in {"1", "true", "yes", "y"},
            notes=row.get("notes", "").strip(),
        )


@dataclass
class RoutedLead:
    reviewed_lead: ReviewedLead
    installer: Installer
    case_id: str


@dataclass
class Receipt:
    case_id: str
    subject: str
    preheader: str
    from_display: str
    from_address: str
    to_display: str
    to_address: str
    body_text: str
    body_html: str
