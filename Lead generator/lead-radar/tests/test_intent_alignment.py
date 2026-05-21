"""Verifies intent_from_score uses the same bands as Sheets HOT/ALL/OPP tabs.

Bands after alignment:
  >=80  hot
  60-79 warm
  40-59 opp
  <40   cold
"""

from consumer import intent_from_score


def test_intent_hot_at_or_above_80():
    assert intent_from_score(80) == "hot"
    assert intent_from_score(85) == "hot"
    assert intent_from_score(100) == "hot"


def test_intent_warm_at_60_to_79():
    assert intent_from_score(60) == "warm"
    assert intent_from_score(70) == "warm"
    assert intent_from_score(79) == "warm"


def test_intent_opp_at_40_to_59():
    assert intent_from_score(40) == "opp"
    assert intent_from_score(50) == "opp"
    assert intent_from_score(59) == "opp"


def test_intent_cold_below_40():
    assert intent_from_score(0) == "cold"
    assert intent_from_score(20) == "cold"
    assert intent_from_score(39) == "cold"


def test_intent_boundary_consistency():
    """Boundaries match Sheets thresholds in consumer/output/sheets.py."""
    from consumer.output import sheets

    assert intent_from_score(sheets.HOT_THRESHOLD) == "hot"
    assert intent_from_score(70) == "warm"
