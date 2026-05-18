from datetime import datetime, timedelta, timezone

from delivery.time_fmt import absolute_iso, relative_time

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def test_minutes_ago():
    assert relative_time(NOW - timedelta(minutes=12), now=NOW) == "12 minuten geleden"


def test_one_minute_ago_singular():
    assert relative_time(NOW - timedelta(minutes=1), now=NOW) == "1 minuut geleden"


def test_hours_ago():
    assert relative_time(NOW - timedelta(hours=4, minutes=30), now=NOW) == "4 uur geleden"


def test_one_hour_ago_singular():
    assert relative_time(NOW - timedelta(hours=1), now=NOW) == "1 uur geleden"


def test_days_ago():
    assert relative_time(NOW - timedelta(days=2), now=NOW) == "2 dagen geleden"


def test_one_day_ago_singular():
    assert relative_time(NOW - timedelta(days=1), now=NOW) == "1 dag geleden"


def test_one_week_label():
    assert relative_time(NOW - timedelta(days=7), now=NOW) == "vorige week"


def test_two_weeks_ago_falls_back_to_days():
    assert relative_time(NOW - timedelta(days=14), now=NOW) == "14 dagen geleden"


def test_under_one_minute_never_says_now():
    assert relative_time(NOW - timedelta(seconds=30), now=NOW) == "1 minuut geleden"


def test_absolute_iso_format():
    assert absolute_iso(datetime(2026, 5, 18, 14, 21, 0, tzinfo=UTC)) == "2026-05-18 14:21 UTC"
