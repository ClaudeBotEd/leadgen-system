"""Unit tests for consumer.niche_relevance.

Covers the niche-anchor gate spec from the proof-sprint cross-niche
leakage fix: per-niche substring match on title+text, case-insensitive,
robust to None/empty inputs.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from consumer import niche_relevance


CONFIGURED_NICHES = [
    "warmtepomp",
    "airco",
    "zonnepanelen",
    "cv",
    "isolatie",
    "vloerverwarming",
    "ventilatie",
    "laadpaal",
    "renovatie",
    "dakwerk",
    "kozijnen",
]

WATERSCHADE_TITLE = "Sanibroyeur defect, waterschade in huurwoning"
WATERSCHADE_TEXT = (
    "Mijn sanibroyeur lekt al weken en de verhuurder weigert te "
    "repareren. Huurconflict gaande, schade aan de vloer. Wat zijn "
    "mijn rechten?"
)

UITBOUW_TITLE = "Vraag over uitbouw 8,5m diep"
UITBOUW_TEXT = (
    "We willen onze keuken uitbreiden met een uitbouw van 8.5 meter. "
    "Iemand ervaring met vergunning aanvragen?"
)


def test_load_anchors_returns_list_for_each_configured_niche() -> None:
    for niche in CONFIGURED_NICHES:
        anchors = niche_relevance.load_anchors(niche)
        assert isinstance(anchors, list), f"{niche}: expected list, got {type(anchors)}"
        assert len(anchors) >= 5, f"{niche}: expected >=5 anchors, got {len(anchors)}"
        assert len(anchors) <= 25, f"{niche}: anchor list too long ({len(anchors)})"
        for anchor in anchors:
            assert isinstance(anchor, str) and anchor.strip(), (
                f"{niche}: anchor must be non-empty string, got {anchor!r}"
            )


def test_load_anchors_unknown_niche_returns_empty_list() -> None:
    assert niche_relevance.load_anchors("not_a_real_niche") == []


def test_warmtepomp_true_positive_passes() -> None:
    title = "Welke warmtepomp adviseren jullie?"
    text = "Hybride warmtepomp of monoblock? Huis 1990, EPC 2.3."
    assert niche_relevance.is_niche_relevant(title, text, "warmtepomp") is True


def test_airco_true_positive_passes() -> None:
    title = "Multisplit airco offerte gevraagd"
    text = "Ik zoek een airco met 3 binnenunits voor woonkamer en slaapkamers."
    assert niche_relevance.is_niche_relevant(title, text, "airco") is True


def test_kozijnen_true_positive_passes() -> None:
    title = "Offerte plaatsen kozijnen achterkant"
    text = "Twee kunststof kozijnen vervangen, HR++ glas, achtergevel."
    assert niche_relevance.is_niche_relevant(title, text, "kozijnen") is True


def test_zonnepanelen_true_positive_passes() -> None:
    title = "Zonnepanelen verwijderen en terugplaatsen voor dakrenovatie"
    text = "12 panelen moeten eraf voor nieuw dak, daarna terug. Omvormer SolarEdge."
    assert niche_relevance.is_niche_relevant(title, text, "zonnepanelen") is True


def test_waterschade_sanibroyeur_fails_warmtepomp() -> None:
    assert (
        niche_relevance.is_niche_relevant(
            WATERSCHADE_TITLE, WATERSCHADE_TEXT, "warmtepomp"
        )
        is False
    )


def test_waterschade_sanibroyeur_fails_airco() -> None:
    assert (
        niche_relevance.is_niche_relevant(
            WATERSCHADE_TITLE, WATERSCHADE_TEXT, "airco"
        )
        is False
    )


def test_waterschade_sanibroyeur_fails_zonnepanelen() -> None:
    assert (
        niche_relevance.is_niche_relevant(
            WATERSCHADE_TITLE, WATERSCHADE_TEXT, "zonnepanelen"
        )
        is False
    )


def test_waterschade_sanibroyeur_fails_laadpaal() -> None:
    assert (
        niche_relevance.is_niche_relevant(
            WATERSCHADE_TITLE, WATERSCHADE_TEXT, "laadpaal"
        )
        is False
    )


def test_uitbouw_does_not_pass_warmtepomp_without_anchor() -> None:
    assert (
        niche_relevance.is_niche_relevant(UITBOUW_TITLE, UITBOUW_TEXT, "warmtepomp")
        is False
    )


def test_uitbouw_with_warmtepomp_anchor_does_pass_warmtepomp() -> None:
    text = UITBOUW_TEXT + " Daarbij willen we ook een warmtepomp laten plaatsen."
    assert (
        niche_relevance.is_niche_relevant(UITBOUW_TITLE, text, "warmtepomp") is True
    )


def test_case_insensitive_match() -> None:
    assert (
        niche_relevance.is_niche_relevant(
            "WARMTEPOMP HULP NODIG", "huis 1990", "warmtepomp"
        )
        is True
    )
    assert (
        niche_relevance.is_niche_relevant(
            "kleine vraag", "Multisplit AIRCO advies", "airco"
        )
        is True
    )


def test_empty_inputs_return_false() -> None:
    assert niche_relevance.is_niche_relevant("", "", "warmtepomp") is False
    assert niche_relevance.is_niche_relevant(None, None, "warmtepomp") is False
    assert niche_relevance.is_niche_relevant("hi", "", "warmtepomp") is False
    assert (
        niche_relevance.is_niche_relevant(None, "warmtepomp text", "warmtepomp")
        is True
    )


def test_unknown_niche_returns_false_even_with_matching_text() -> None:
    assert (
        niche_relevance.is_niche_relevant(
            "anything", "warmtepomp text", "ghost_niche"
        )
        is False
    )


def test_yaml_file_exists_and_has_all_configured_niches() -> None:
    yaml_path = (
        Path(niche_relevance.__file__).resolve().parent / "niche_anchors.yaml"
    )
    assert yaml_path.exists(), f"missing {yaml_path}"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    assert "niches" in data, "niche_anchors.yaml must have top-level 'niches' key"
    declared = set(data["niches"].keys())
    expected = set(CONFIGURED_NICHES)
    missing = expected - declared
    assert not missing, f"niche_anchors.yaml missing niches: {sorted(missing)}"
