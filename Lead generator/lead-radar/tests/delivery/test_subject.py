import pytest

from delivery.subject import build_subject


def test_canonical_template():
    assert build_subject(region="Amsterdam", niche="warmtepomp", band="HOT") == "Amsterdam · warmtepomp · HOT"


def test_postcode_region():
    assert build_subject(region="1015AA", niche="warmtepomp", band="HOT") == "1015AA · warmtepomp · HOT"


def test_band_uppercase_enforced():
    assert build_subject(region="Utrecht", niche="airco", band="warm") == "Utrecht · airco · WARM"


def test_niche_lowercase_enforced():
    assert build_subject(region="Utrecht", niche="WARMTEPOMP", band="HOT") == "Utrecht · warmtepomp · HOT"


def test_unknown_band_raises():
    with pytest.raises(ValueError, match="band must be one of"):
        build_subject(region="Amsterdam", niche="warmtepomp", band="WARMTE")


def test_unknown_niche_raises():
    with pytest.raises(ValueError, match="niche must be one of"):
        build_subject(region="Amsterdam", niche="onbekend", band="HOT")


def test_no_brand_prefix():
    subject = build_subject(region="Amsterdam", niche="warmtepomp", band="HOT")
    assert "Lead Radar" not in subject and "[" not in subject


def test_no_emoji():
    subject = build_subject(region="Amsterdam", niche="warmtepomp", band="HOT")
    for emoji in ["🔥", "⏰", "⚠️", "🚨"]:
        assert emoji not in subject
