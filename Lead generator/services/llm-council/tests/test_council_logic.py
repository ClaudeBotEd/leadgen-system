"""Pure-function tests for council parsing + aggregation."""

from __future__ import annotations

from backend.services.council import (
    calculate_aggregate_rankings,
    parse_ranking_from_text,
)


def test_parse_ranking_numbered_format():
    text = (
        "Some analysis here.\n\n"
        "FINAL RANKING:\n"
        "1. Response B\n"
        "2. Response A\n"
        "3. Response C\n"
    )
    assert parse_ranking_from_text(text) == [
        "Response B",
        "Response A",
        "Response C",
    ]


def test_parse_ranking_handles_missing_header():
    text = "Response B beats Response A, and Response C is last."
    parsed = parse_ranking_from_text(text)
    assert parsed[0] == "Response B"
    assert set(parsed) == {"Response A", "Response B", "Response C"}


def test_aggregate_rankings_orders_by_average():
    label_to_model = {
        "Response A": "model-a",
        "Response B": "model-b",
        "Response C": "model-c",
    }
    stage2 = [
        {"model": "model-a", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C"},
        {"model": "model-b", "ranking": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C"},
        {"model": "model-c", "ranking": "FINAL RANKING:\n1. Response A\n2. Response C\n3. Response B"},
    ]
    agg = calculate_aggregate_rankings(stage2, label_to_model)
    assert agg[0]["model"] == "model-a"
    assert agg[0]["average_rank"] < agg[-1]["average_rank"]
    for row in agg:
        assert row["rankings_count"] == 3
