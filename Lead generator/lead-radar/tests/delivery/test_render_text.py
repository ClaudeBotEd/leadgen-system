from datetime import datetime, timedelta, timezone

from delivery.model import Installer, ReviewedLead, RoutedLead
from delivery.render_text import render_text

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def _routed(**lead_overrides):
    base = dict(
        lead_id="L-001",
        snippet=(
            "Ik zoek een installateur in regio Amsterdam voor een "
            "lucht/water warmtepomp + buffervat. Budget rond 12-15k, "
            "wil deze zomer plaatsen."
        ),
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
    rl = ReviewedLead(**base)
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
    return RoutedLead(reviewed_lead=rl, installer=inst, case_id="LR-2026-05-18-0042")


def test_opening_uses_installer_first_name():
    assert "Hallo Jeroen," in render_text(_routed(), now=NOW)


def test_snippet_is_verbatim_quoted():
    out = render_text(_routed(), now=NOW)
    assert "Ik zoek een installateur in regio Amsterdam" in out


def test_source_platform_titlecased():
    out = render_text(_routed(), now=NOW)
    assert "vastgelegd vanuit Tweakers" in out


def test_relative_time_visible():
    out = render_text(_routed(), now=NOW)
    assert "4 uur geleden" in out


def test_open_bron_with_host():
    out = render_text(_routed(), now=NOW)
    assert "open bron ↗" in out
    assert "(tweakers.net)" in out


def test_band_glyph_hot():
    out = render_text(_routed(), now=NOW)
    assert "band:  ●  HOT" in out


def test_band_glyph_warm():
    out = render_text(_routed(confidence_band="WARM"), now=NOW)
    assert "band:  ○  WARM" in out


def test_band_glyph_opp():
    out = render_text(_routed(confidence_band="OPP"), now=NOW)
    assert "band:  ·  OPP" in out


def test_reason_visible():
    out = render_text(_routed(), now=NOW)
    assert "Expliciet budget en tijdshorizon (deze zomer)." in out


def test_signature_row():
    out = render_text(_routed(), now=NOW)
    assert "Marieke de Vries" in out
    assert "marieke@lead-radar.nl" in out
    assert "2 uur geleden" in out


def test_exclusivity_sentence():
    out = render_text(_routed(), now=NOW)
    assert "uitsluitend naar u verzonden" in out
    assert "5 werkdagen" in out


def test_dispute_strip_names_reviewer():
    out = render_text(_routed(), now=NOW)
    assert "Marieke beoordeelt persoonlijk binnen één werkdag." in out


def test_sign_off_first_name_only():
    lines = [ln.strip() for ln in render_text(_routed(), now=NOW).splitlines() if ln.strip()]
    assert "Marieke" in lines


def test_case_id_in_footer():
    assert "LR-2026-05-18-0042" in render_text(_routed(), now=NOW)


def test_brand_footer_appears_once():
    assert render_text(_routed(), now=NOW).count("Lead Radar") == 1


def test_decayed_source_shows_archive():
    routed = _routed(
        captured_at=NOW - timedelta(days=10),
        archive_url="https://archive.org/snapshot/abc",
    )
    out = render_text(routed, now=NOW)
    assert "open snapshot (gearchiveerd)" in out
    assert "DECAYED" in out
