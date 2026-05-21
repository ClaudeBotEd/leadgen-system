import re
from datetime import datetime, timedelta, timezone

from delivery.model import Installer, ReviewedLead, RoutedLead
from delivery.render_html import render_html

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def _routed(**lead_overrides):
    base = dict(
        lead_id="L-001",
        snippet="Ik zoek een installateur in regio Amsterdam voor een warmtepomp.",
        source_url="https://tweakers.net/threads/12345",
        source_platform="tweakers",
        captured_at=NOW - timedelta(hours=4),
        region="Amsterdam",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Expliciet budget en tijdshorizon (deze zomer).",
        reviewer_name="Marieke de Vries",
        reviewer_email="marieke@lead-radar.nl",
        reviewed_at=NOW - timedelta(hours=2),
    )
    base.update(lead_overrides)
    inst = Installer(
        installer_id="I-001",
        company_name="Visser Installaties",
        contact_name="Jeroen Visser",
        email="jeroen@visserinstallaties.nl",
        phone="",
        city="Amsterdam",
        regions=["Amsterdam"],
        niches=["warmtepomp"],
        active=True,
        notes="",
    )
    return RoutedLead(reviewed_lead=ReviewedLead(**base), installer=inst, case_id="LR-2026-05-18-0042")


def test_returns_well_formed_html_document():
    html = render_html(_routed(), now=NOW).lstrip()
    assert html.startswith("<!doctype html>") or html.startswith("<!DOCTYPE html>")
    assert "<html" in html and "</html>" in html


def test_no_style_or_script_tags():
    html = render_html(_routed(), now=NOW)
    assert "<style" not in html.lower()
    assert "stylesheet" not in html.lower()
    assert "<script" not in html.lower()


def test_no_tailwind_classnames():
    html = render_html(_routed(), now=NOW)
    assert not re.search(r'class="[^"]*\b(?:bg-|text-(?:sm|lg|xl)|p-\d|m-\d)\b', html)


def test_snippet_appears_verbatim():
    html = render_html(_routed(), now=NOW)
    assert "Ik zoek een installateur in regio Amsterdam voor een warmtepomp." in html


def test_source_link_target_blank_noopener():
    html = render_html(_routed(), now=NOW)
    assert 'href="https://tweakers.net/threads/12345"' in html
    assert 'target="_blank"' in html
    assert 'rel="noopener"' in html


def test_no_tracking_pixel_no_images():
    html = render_html(_routed(), now=NOW)
    assert "<img" not in html.lower()
    assert "open=" not in html


def test_band_label_and_glyph():
    html = render_html(_routed(), now=NOW)
    assert "●" in html and "HOT" in html


def test_reviewer_signature_present():
    html = render_html(_routed(), now=NOW)
    assert "Marieke de Vries" in html
    assert "marieke@lead-radar.nl" in html


def test_case_id_in_footer():
    html = render_html(_routed(), now=NOW)
    assert "LR-2026-05-18-0042" in html


def test_exclusivity_paragraph_present():
    html = render_html(_routed(), now=NOW)
    assert "uitsluitend naar u verzonden" in html


def test_one_case_id_per_email():
    html = render_html(_routed(), now=NOW)
    assert html.count("LR-2026-05-18-0042") == 1
