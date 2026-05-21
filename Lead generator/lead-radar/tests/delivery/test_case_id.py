from datetime import date
from pathlib import Path

import pytest

from delivery.case_id import generate_case_id, next_sequence_for_date


def test_format_pattern():
    cid = generate_case_id(date(2026, 5, 18), 42)
    assert cid == "LR-2026-05-18-0042"


def test_pads_sequence_to_four_digits():
    assert generate_case_id(date(2026, 5, 18), 1).endswith("-0001")
    assert generate_case_id(date(2026, 5, 18), 9999).endswith("-9999")


def test_sequence_overflow_raises():
    with pytest.raises(ValueError, match="exceeds 9999"):
        generate_case_id(date(2026, 5, 18), 10000)


def test_sequence_negative_raises():
    with pytest.raises(ValueError, match="must be >= 1"):
        generate_case_id(date(2026, 5, 18), 0)


def test_next_sequence_empty_log(tmp_path: Path):
    log = tmp_path / "lead_log.csv"
    log.write_text("at,lead_id,from_state,to_state,actor,reason\n", encoding="utf-8")
    assert next_sequence_for_date(date(2026, 5, 18), log_path=log) == 1


def test_next_sequence_counts_same_day_deliveries(tmp_path: Path):
    log = tmp_path / "lead_log.csv"
    log.write_text(
        "at,lead_id,from_state,to_state,actor,reason\n"
        "2026-05-18T08:00:00+00:00,L1,APPROVED,DELIVERED,m@x,case=LR-2026-05-18-0001\n"
        "2026-05-18T09:15:00+00:00,L2,APPROVED,DELIVERED,m@x,case=LR-2026-05-18-0002\n"
        "2026-05-17T22:00:00+00:00,L0,APPROVED,DELIVERED,m@x,case=LR-2026-05-17-0007\n",
        encoding="utf-8",
    )
    assert next_sequence_for_date(date(2026, 5, 18), log_path=log) == 3


def test_next_sequence_ignores_non_delivered(tmp_path: Path):
    log = tmp_path / "lead_log.csv"
    log.write_text(
        "at,lead_id,from_state,to_state,actor,reason\n"
        "2026-05-18T08:00:00+00:00,L1,NEW,APPROVED,m@x,reviewed\n"
        "2026-05-18T08:30:00+00:00,L2,APPROVED,REJECTED,m@x,off-topic\n",
        encoding="utf-8",
    )
    assert next_sequence_for_date(date(2026, 5, 18), log_path=log) == 1


def test_next_sequence_missing_log_returns_one(tmp_path: Path):
    assert next_sequence_for_date(date(2026, 5, 18), log_path=tmp_path / "missing.csv") == 1
