import pytest

from delivery.preheader import build_preheader, reviewer_first_name


def test_canonical_template():
    line = build_preheader(reviewer_first="Marieke", platform="Tweakers", region="Amsterdam")
    assert line == "Marieke reviewde een Tweakers-post uit regio Amsterdam."


def test_platform_titlecase_enforced():
    line = build_preheader(reviewer_first="Marieke", platform="reddit", region="Utrecht")
    assert line == "Marieke reviewde een Reddit-post uit regio Utrecht."


def test_postcode_region_preserved():
    line = build_preheader(reviewer_first="Marieke", platform="Facebook", region="1015AA")
    assert line == "Marieke reviewde een Facebook-post uit regio 1015AA."


def test_no_marketing_phrases():
    line = build_preheader(reviewer_first="Marieke", platform="Tweakers", region="Amsterdam")
    assert "Open snel" not in line
    assert "nieuwe lead" not in line


def test_reviewer_first_name_helper():
    assert reviewer_first_name("Marieke de Vries") == "Marieke"
    assert reviewer_first_name("Jan-Willem ter Hoeven") == "Jan-Willem"
    assert reviewer_first_name("Anne") == "Anne"


def test_reviewer_first_name_empty_raises():
    with pytest.raises(ValueError):
        reviewer_first_name("")
