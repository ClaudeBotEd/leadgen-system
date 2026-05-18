from datetime import datetime, timedelta, timezone

from delivery.decay import DEFAULT_DECAY_DAYS, is_decayed

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def test_default_window_is_eight_days():
    assert DEFAULT_DECAY_DAYS == 8


def test_fresh_lead_not_decayed():
    assert is_decayed(NOW - timedelta(hours=2), now=NOW) is False


def test_seven_days_not_decayed():
    assert is_decayed(NOW - timedelta(days=7, hours=23), now=NOW) is False


def test_eight_days_exactly_decayed():
    assert is_decayed(NOW - timedelta(days=8), now=NOW) is True


def test_well_past_window_decayed():
    assert is_decayed(NOW - timedelta(days=30), now=NOW) is True


def test_custom_window_override():
    captured = NOW - timedelta(days=3)
    assert is_decayed(captured, now=NOW, decay_days=2) is True
    assert is_decayed(captured, now=NOW, decay_days=4) is False
