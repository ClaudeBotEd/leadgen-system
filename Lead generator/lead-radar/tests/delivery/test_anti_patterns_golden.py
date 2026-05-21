import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from delivery.model import Installer, ReviewedLead, RoutedLead
from delivery.render_html import render_html
from delivery.render_text import render_text
from delivery.vocab_lint import check_no_banned_terms

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def _installer():
    return Installer(
        installer_id="I-X",
        company_name="Visser",
        contact_name="Jeroen Visser",
        email="jeroen@x.nl",
        phone="",
        city="X",
        regions=["Amsterdam", "Utrecht", "Rotterdam"],
        niches=["warmtepomp", "airco", "zonnepanelen"],
        active=True,
        notes="",
    )


def _load_fixtures():
    fixture = Path(__file__).resolve().parents[2] / "delivery" / "fixtures" / "reviewed_sample.jsonl"
    leads = []
    with fixture.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            leads.append(ReviewedLead.from_dict(json.loads(line)))
    return leads


@pytest.fixture
def routed_samples():
    return [
        RoutedLead(reviewed_lead=rl, installer=_installer(), case_id=f"LR-2026-05-18-{i + 1:04d}")
        for i, rl in enumerate(_load_fixtures())
    ]


def test_fixture_loads_three_samples(routed_samples):
    assert len(routed_samples) == 3
    assert {r.reviewed_lead.confidence_band for r in routed_samples} == {"HOT", "WARM", "OPP"}


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_plain_text_passes_vocab_lint(routed_samples, idx):
    body = render_text(routed_samples[idx], now=NOW)
    violations = check_no_banned_terms(body)
    assert violations == [], f"violations: {violations}"


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_html_passes_vocab_lint(routed_samples, idx):
    html = render_html(routed_samples[idx], now=NOW)
    violations = check_no_banned_terms(html)
    assert violations == [], f"violations: {violations}"


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_five_canonical_fields_present(routed_samples, idx):
    routed = routed_samples[idx]
    body = render_text(routed, now=NOW)
    assert routed.reviewed_lead.snippet in body
    assert "vastgelegd vanuit" in body
    assert "open bron ↗" in body
    assert routed.reviewed_lead.confidence_band in body
    assert routed.reviewed_lead.band_reason in body
    assert routed.reviewed_lead.reviewer_name in body
    assert routed.reviewed_lead.reviewer_email in body
    assert "uitsluitend naar u verzonden" in body
    assert routed.case_id in body


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_html_has_no_style_or_tailwind(routed_samples, idx):
    html = render_html(routed_samples[idx], now=NOW)
    assert "<style" not in html.lower()
    assert "<script" not in html.lower()
    assert "<img" not in html.lower()
    assert not re.search(r'class="[^"]*\b(?:bg-|text-(?:sm|lg|xl)|p-\d|m-\d)\b', html)


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_brand_appears_exactly_once_in_plain_text(routed_samples, idx):
    body = render_text(routed_samples[idx], now=NOW)
    assert body.count("Lead Radar") == 1


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_sign_off_first_name_only(routed_samples, idx):
    body = render_text(routed_samples[idx], now=NOW)
    lines = [ln.rstrip() for ln in body.splitlines()]
    assert "Marieke" in lines
