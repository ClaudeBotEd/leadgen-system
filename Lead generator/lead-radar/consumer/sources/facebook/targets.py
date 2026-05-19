"""Pydantic-validated YAML loader for the FB targets config.

The operator edits ``config/facebook_targets.yaml`` to tell the scraper which
groups, pages, and marketplace queries to hit per niche.  Schema validation
catches typos and missing required fields at load time rather than mid-run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class GroupTarget(BaseModel):
    """A single FB group to scrape."""
    id: str
    name: str
    max_posts: int = 20


class PageTarget(BaseModel):
    """A single FB public page to scrape."""
    slug: str
    name: str = ""
    max_posts: int = 20


class MarketplaceTarget(BaseModel):
    """A Marketplace search query.

    `listing_type="wanted"` is the default because lead-radar wants posts from
    PEOPLE SEEKING installers (consumer intent), not vendors offering equipment.
    `listing_type="sale"` is what FB defaults to in its UI and will surface
    exactly the opposite of what we want — keep this in mind when reviewing
    targets.

    `location_slug` MUST be a real FB-recognized city slug (e.g. "tilburg",
    "amsterdam", "eindhoven").  "nederland" returns a Marketplace landing
    page with 0 search results — do not use it.
    """
    query: str
    from_city: str = "Tilburg"
    location_slug: str = "tilburg"
    radius_km: int = 50
    max_results: int = 30
    listing_type: Literal["wanted", "sale", "all"] = "wanted"


class NicheTargets(BaseModel):
    """Per-niche bundle of surface targets — any surface may be empty."""
    groups: list[GroupTarget] = Field(default_factory=list)
    pages: list[PageTarget] = Field(default_factory=list)
    marketplace: list[MarketplaceTarget] = Field(default_factory=list)


class FacebookTargetsConfig(BaseModel):
    """Top-level config: operator-tunable defaults + per-niche surface targets."""
    defaults: dict[str, Any] = Field(default_factory=dict)
    niches: dict[str, NicheTargets] = Field(default_factory=dict)


def load_targets(path: Path) -> FacebookTargetsConfig:
    """Load and validate the targets YAML.

    Raises FileNotFoundError if the file is missing, pydantic.ValidationError
    if the schema is wrong.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return FacebookTargetsConfig.model_validate(raw)
