import pytest

from delivery.opening import build_opening


def test_canonical_opening():
    out = build_opening(installer_first="Jeroen", platform="Tweakers", band="HOT")
    expected = (
        "Hallo Jeroen,\n"
        "\n"
        "Onderstaande post kwam binnen vanuit Tweakers. Ik heb hem\n"
        "beoordeeld en band HOT toegekend. Reden staat onder de bron."
    )
    assert out == expected


def test_platform_titlecase():
    out = build_opening(installer_first="Jeroen", platform="reddit", band="WARM")
    assert "vanuit Reddit." in out
    assert "band WARM toegekend" in out


def test_no_smileys():
    out = build_opening(installer_first="Jeroen", platform="Tweakers", band="HOT")
    for ch in [":)", ":(", "😊", "🙂"]:
        assert ch not in out


def test_first_person_singular():
    out = build_opening(installer_first="Jeroen", platform="Tweakers", band="HOT")
    assert "Ik heb hem" in out
    assert "Ons team" not in out


def test_invalid_band_raises():
    with pytest.raises(ValueError):
        build_opening(installer_first="Jeroen", platform="Tweakers", band="WARMTE")
