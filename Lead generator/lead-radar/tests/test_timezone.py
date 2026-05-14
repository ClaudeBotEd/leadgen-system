"""Tests dat timestamps in Sheets/CSV in Europe/Amsterdam tijd zijn.

Bug: naive datetime.now() schreef UTC-tijd in Sheets-cellen en filename-dates.
Rond middernacht NL-tijd gaf dat de verkeerde datum (UTC is 1-2u terug).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest


def test_now_str_uses_europe_amsterdam_tz(monkeypatch: pytest.MonkeyPatch) -> None:
    """_now_str() moet NL-tijd retourneren, niet UTC."""
    from consumer.output import sheets

    # 14 mei 2026 23:30 UTC = 15 mei 01:30 CEST (DST actief in mei).
    fixed_utc = datetime(2026, 5, 14, 23, 30, 0, tzinfo=timezone.utc)

    class FakeDatetime:
        @staticmethod
        def now(tz=None):
            if tz is None:
                return fixed_utc.replace(tzinfo=None)
            return fixed_utc.astimezone(tz)

    monkeypatch.setattr(sheets, "datetime", FakeDatetime)
    out = sheets._now_str()
    assert out == "2026-05-15 01:30", f"expected '2026-05-15 01:30' (NL tijd), got {out!r}"


def test_today_uses_europe_amsterdam_tz(monkeypatch: pytest.MonkeyPatch) -> None:
    """_today() in exporter.py moet NL-datum retourneren."""
    from consumer.output import exporter

    fixed_utc = datetime(2026, 5, 14, 22, 30, 0, tzinfo=timezone.utc)  # 00:30 NL volgende dag

    class FakeDatetime:
        @staticmethod
        def now(tz=None):
            if tz is None:
                return fixed_utc.replace(tzinfo=None)
            return fixed_utc.astimezone(tz)

    monkeypatch.setattr(exporter, "datetime", FakeDatetime)
    out = exporter._today()
    assert out == "2026-05-15", f"expected '2026-05-15' (NL), got {out!r}"
