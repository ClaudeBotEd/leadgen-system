from datetime import datetime, timezone

import pytest

from delivery.model import Installer, Receipt, ReviewedLead, RoutedLead

UTC = timezone.utc


def make_rl(**overrides):
    base = dict(
        lead_id="L-001",
        snippet="Ik zoek een installateur voor een warmtepomp.",
        source_url="https://tweakers.net/threads/12345",
        source_platform="tweakers",
        captured_at=datetime(2026, 5, 18, 10, 0, 0, tzinfo=UTC),
        region="Amsterdam",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Expliciet budget en tijdshorizon.",
        reviewer_name="Marieke de Vries",
        reviewer_email="marieke@lead-radar.nl",
        reviewed_at=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
    )
    base.update(overrides)
    return ReviewedLead(**base)


def test_reviewed_lead_constructs_with_required_fields():
    rl = make_rl()
    assert rl.lead_id == "L-001"
    assert rl.confidence_band == "HOT"
    assert rl.archive_url is None


def test_reviewed_lead_uppercases_band():
    rl = make_rl(confidence_band="hot")
    assert rl.confidence_band == "HOT"


def test_reviewed_lead_rejects_invalid_band():
    with pytest.raises(ValueError, match="confidence_band"):
        make_rl(confidence_band="WARMTE")


def test_reviewed_lead_rejects_empty_snippet():
    with pytest.raises(ValueError, match="snippet"):
        make_rl(snippet="")


def test_reviewed_lead_rejects_invalid_source_url():
    with pytest.raises(ValueError, match="source_url"):
        make_rl(source_url="not-a-url")


def test_reviewed_lead_rejects_invalid_reviewer_email():
    with pytest.raises(ValueError, match="reviewer_email"):
        make_rl(reviewer_email="not-an-email")


def test_installer_from_csv_row():
    inst = Installer.from_csv_row(
        {
            "installer_id": "I-001",
            "company_name": "Visser Installaties",
            "contact_name": "Jeroen Visser",
            "email": "jeroen@visserinstallaties.nl",
            "phone": "+31 20 1234567",
            "city": "Amsterdam",
            "regions": "Amsterdam|Amstelveen|Haarlem",
            "niches": "warmtepomp|zonnepanelen",
            "active": "true",
            "notes": "",
        }
    )
    assert inst.installer_id == "I-001"
    assert "Amsterdam" in inst.regions
    assert "warmtepomp" in inst.niches
    assert inst.active is True


def test_installer_inactive_when_active_field_false():
    inst = Installer.from_csv_row(
        {
            "installer_id": "I-002",
            "company_name": "X",
            "contact_name": "Y",
            "email": "y@x.nl",
            "phone": "",
            "city": "",
            "regions": "",
            "niches": "",
            "active": "false",
            "notes": "",
        }
    )
    assert inst.active is False


def test_routed_lead_combines_reviewed_and_installer():
    rl = make_rl()
    inst = Installer(
        installer_id="I-001",
        company_name="Visser",
        contact_name="Jeroen Visser",
        email="jeroen@visserinstallaties.nl",
        phone="",
        city="Amsterdam",
        regions=["Amsterdam"],
        niches=["warmtepomp"],
        active=True,
        notes="",
    )
    routed = RoutedLead(reviewed_lead=rl, installer=inst, case_id="LR-2026-05-18-0042")
    assert routed.case_id == "LR-2026-05-18-0042"


def test_receipt_holds_rendered_payloads():
    receipt = Receipt(
        case_id="LR-2026-05-18-0042",
        subject="Amsterdam · warmtepomp · HOT",
        preheader="Marieke reviewde een Tweakers-post uit regio Amsterdam.",
        from_display="Marieke de Vries — Lead Radar",
        from_address="marieke@lead-radar.nl",
        to_display="Jeroen Visser",
        to_address="jeroen@visserinstallaties.nl",
        body_text="(plain text)",
        body_html="<p>(html)</p>",
    )
    assert receipt.subject.startswith("Amsterdam")
    assert receipt.from_address == "marieke@lead-radar.nl"
