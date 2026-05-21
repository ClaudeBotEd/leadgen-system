"""Tests for the FB targets-config Pydantic schema + YAML loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer.sources.facebook.targets import (
    FacebookTargetsConfig,
    GroupTarget,
    MarketplaceTarget,
    NicheTargets,
    PageTarget,
    load_targets,
)


def test_group_target_defaults() -> None:
    g = GroupTarget(id="123", name="Test Group")
    assert g.max_posts == 20


def test_page_target_defaults() -> None:
    p = PageTarget(slug="testpage")
    assert p.name == ""
    assert p.max_posts == 20


def test_marketplace_target_defaults() -> None:
    m = MarketplaceTarget(query="warmtepomp installateur gezocht")
    assert m.from_city == "Tilburg"
    assert m.location_slug == "tilburg"
    assert m.radius_km == 50
    assert m.max_results == 30
    assert m.listing_type == "wanted"


def test_marketplace_target_listing_type_validated() -> None:
    with pytest.raises(Exception):  # pydantic.ValidationError
        MarketplaceTarget(query="x", listing_type="invalid")


def test_niche_targets_all_surfaces_optional() -> None:
    n = NicheTargets()
    assert n.groups == []
    assert n.pages == []
    assert n.marketplace == []


def test_load_targets_minimal_yaml(tmp_path: Path) -> None:
    yaml_text = """
defaults:
  max_posts_per_target: 20
  max_age_days: 7
niches:
  warmtepomp:
    groups:
      - id: "123456789"
        name: "Warmtepomp NL Ervaringen"
        max_posts: 30
"""
    f = tmp_path / "targets.yaml"
    f.write_text(yaml_text, encoding="utf-8")
    cfg = load_targets(f)
    assert isinstance(cfg, FacebookTargetsConfig)
    assert "warmtepomp" in cfg.niches
    assert cfg.niches["warmtepomp"].groups[0].id == "123456789"
    assert cfg.niches["warmtepomp"].groups[0].max_posts == 30


def test_load_targets_full_yaml(tmp_path: Path) -> None:
    yaml_text = """
defaults:
  max_posts_per_target: 20
  max_age_days: 7
niches:
  warmtepomp:
    groups:
      - id: "111"
        name: "G1"
    pages:
      - slug: "page1"
        name: "P1"
    marketplace:
      - query: "warmtepomp gezocht"
        from_city: "Tilburg"
        location_slug: "tilburg"
        radius_km: 50
  airco:
    marketplace:
      - query: "airco installatie hulp"
"""
    f = tmp_path / "targets.yaml"
    f.write_text(yaml_text, encoding="utf-8")
    cfg = load_targets(f)
    assert len(cfg.niches) == 2
    wp = cfg.niches["warmtepomp"]
    assert wp.groups[0].id == "111"
    assert wp.pages[0].slug == "page1"
    assert wp.marketplace[0].radius_km == 50
    airco = cfg.niches["airco"]
    assert airco.groups == []
    assert airco.marketplace[0].query == "airco installatie hulp"


def test_load_targets_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_targets(tmp_path / "nope.yaml")


def test_load_targets_invalid_yaml_raises(tmp_path: Path) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text("niches:\n  warmtepomp:\n    groups:\n      - {id: 1}\n", encoding="utf-8")
    with pytest.raises(Exception):  # ValidationError from Pydantic
        load_targets(f)
