"""Unit tests for lead-radar/utils/regions.py."""
from __future__ import annotations

import pytest

from utils.regions import normalize_region, UnknownPlaceError


class TestNormalizeRegion:
    def test_amersfoort_to_utrecht(self):
        assert normalize_region("Amersfoort") == ("utrecht", "amersfoort")

    def test_capitalization_irrelevant(self):
        assert normalize_region("AMERSFOORT") == ("utrecht", "amersfoort")
        assert normalize_region("amersfoort") == ("utrecht", "amersfoort")

    def test_whitespace_trimmed(self):
        assert normalize_region("  Amersfoort  ") == ("utrecht", "amersfoort")

    def test_den_haag_canonical(self):
        assert normalize_region("Den Haag") == ("zuid-holland", "den haag")
        assert normalize_region("'s-Gravenhage") == ("zuid-holland", "den haag")

    def test_groningen_city(self):
        assert normalize_region("Groningen") == ("groningen", "groningen")

    def test_unknown_place_raises(self):
        with pytest.raises(UnknownPlaceError):
            normalize_region("Atlantis")

    def test_empty_string_raises(self):
        with pytest.raises(UnknownPlaceError):
            normalize_region("")
