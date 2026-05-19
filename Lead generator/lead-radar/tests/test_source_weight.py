"""Source-credibility weight applied before threshold gate."""
from __future__ import annotations

from pathlib import Path

from consumer.processor.source_weight import apply_source_weight, load_source_weights


def test_weight_above_one_boosts_score():
    assert apply_source_weight(score=75, source="bouwinfo_forum", weights={"bouwinfo_forum": 1.10}) == 82


def test_weight_below_one_drops_score():
    assert apply_source_weight(score=78, source="google", weights={"google": 0.85}) == 66


def test_unknown_source_uses_default_weight_one():
    assert apply_source_weight(score=80, source="some-new-source", weights={}) == 80


def test_score_clamped_to_100():
    assert apply_source_weight(score=95, source="x", weights={"x": 1.20}) == 100


def test_score_clamped_to_0():
    assert apply_source_weight(score=5, source="x", weights={"x": -0.10}) == 0


def test_load_source_weights_from_config(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "source_weights:\n"
        "  marktplaats: 1.05\n"
        "  google: 0.85\n",
        encoding="utf-8",
    )
    weights = load_source_weights(config_path=cfg)
    assert weights["marktplaats"] == 1.05
    assert weights["google"] == 0.85


def test_load_returns_empty_when_config_missing(tmp_path: Path):
    missing = tmp_path / "nope.yaml"
    assert load_source_weights(config_path=missing) == {}


def test_load_returns_empty_when_no_source_weights_key(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("other_key: value\n", encoding="utf-8")
    assert load_source_weights(config_path=cfg) == {}


def test_source_id_with_subcontext_uses_source_prefix():
    """source_id like 'reddit:r/duurzaam' — strip subcontext, weight applies on 'reddit'."""
    assert apply_source_weight(score=70, source="reddit:r/duurzaam", weights={"reddit": 1.00}) == 70
    assert apply_source_weight(score=80, source="marktplaats:diensten/gent", weights={"marktplaats": 1.05}) == 84
