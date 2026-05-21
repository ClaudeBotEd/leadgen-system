"""Render sample-receipt HTML voor outreach-demo.

Reuse delivery.render_html — geen nieuwe renderer. Constructie van
één synthetische ReviewedLead + Installer + RoutedLead met fictieve
gegevens (geen echte naam/post/url).
"""
from __future__ import annotations

from datetime import datetime, timezone

from delivery.model import Installer, ReviewedLead, RoutedLead
from delivery.render_html import render_html


def _build_synthetic_routed_lead() -> RoutedLead:
    captured = datetime(2026, 5, 19, 8, 15, 0, tzinfo=timezone.utc)
    reviewed = ReviewedLead(
        lead_id="demo-receipt-sample",
        snippet=(
            "Zoek installateur voor warmtepomp; vrijstaande woning '98, "
            "Amersfoort. Vergelijking 2-3 offertes."
        ),
        source_url="https://www.facebook.com/groups/example/posts/000",
        source_platform="facebook",
        captured_at=captured,
        region="utrecht|amersfoort",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Concrete RFQ + regio-match + niche-fit.",
        reviewer_name="Sem Vijn",
        reviewer_email="sem@lead-radar.nl",
        reviewed_at=captured,
    )
    installer = Installer(
        installer_id="demo-installer",
        company_name="Voorbeeld Installatie BV",
        contact_name="Voorbeeld",
        email="voorbeeld@example.nl",
        phone="",
        city="Amersfoort",
        regions=["utrecht|amersfoort"],
        niches=["warmtepomp"],
        active=True,
        notes="",
    )
    return RoutedLead(
        reviewed_lead=reviewed,
        installer=installer,
        case_id="LR-DEMO-001",
    )


def render_sample_receipt_html() -> str:
    routed = _build_synthetic_routed_lead()
    now = datetime(2026, 5, 19, 9, 30, 0, tzinfo=timezone.utc)
    return render_html(routed, now=now)
