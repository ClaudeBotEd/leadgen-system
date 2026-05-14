"""Tests voor manuele ingest-pipeline voor high-risk platforms.

Spec: facebook/linkedin/instagram worden NIET automatisch gescraped
(ToS-risico, account-bans, captcha walls). In plaats daarvan kopieert
een operator posts handmatig en analyseert ze via dezelfde scoring-
pipeline als de gescrapete sources.

Originele implementatie was facebook-only.  Deze tests dwingen af dat
de pipeline platform-agnostisch is — operator kan dezelfde flow
gebruiken voor LinkedIn-posts, Instagram-DMs, TikTok-comments, etc.
"""
from __future__ import annotations

import pytest

from consumer.sources.facebook import analyze_manual_posts, load_posts_from_file


SAMPLE_POSTS = [
    # 1 sterke lead, 1 vendor-promo, 1 lege regel
    "Wie kent een goede warmtepomp installateur in Antwerpen? "
    "Mijn ketel is kapot en ik wil duurzaam vervangen. Spoed gevraagd.",
    "Vaillant Belgium - de beste warmtepompen voor uw woning. Bekijk onze catalogus.",
    "",
]


def test_default_platform_is_facebook_backward_compat() -> None:
    """Zonder platform-arg blijft source 'facebook' (bestaande pipeline behouden)."""
    leads = analyze_manual_posts(SAMPLE_POSTS, niche="warmtepomp")
    for lead in leads:
        assert lead.source == "facebook", (
            f"Default platform moet 'facebook' zijn voor backward compat, kreeg {lead.source!r}"
        )
        assert lead.id.startswith("facebook:"), (
            f"Lead id moet platform-prefixed zijn: {lead.id!r}"
        )


def test_platform_param_changes_source_name() -> None:
    """Met platform='linkedin' → source='linkedin' en id-prefix 'linkedin:'."""
    leads = analyze_manual_posts(
        SAMPLE_POSTS, platform="linkedin", niche="warmtepomp",
    )
    for lead in leads:
        assert lead.source == "linkedin", (
            f"platform='linkedin' moet source='linkedin' opleveren, kreeg {lead.source!r}"
        )
        assert lead.id.startswith("linkedin:")


@pytest.mark.parametrize("platform", ["linkedin", "instagram", "tiktok", "whatsapp", "telegram"])
def test_arbitrary_platform_names_supported(platform: str) -> None:
    """Operator kan elk platform-label gebruiken (geen whitelist).
    High-risk platforms krijgen via deze pipeline een instap zonder scraping."""
    leads = analyze_manual_posts(
        ["Wie kent een airco installateur in Gent? Spoed."],
        platform=platform, niche="airco",
    )
    assert leads, f"Platform {platform!r} leverde geen leads"
    assert leads[0].source == platform


def test_platform_param_does_not_affect_scoring() -> None:
    """Score moet identiek zijn ongeacht platform — dezelfde scoring-pipeline."""
    fb_leads = analyze_manual_posts(SAMPLE_POSTS, platform="facebook", niche="warmtepomp")
    li_leads = analyze_manual_posts(SAMPLE_POSTS, platform="linkedin", niche="warmtepomp")
    assert len(fb_leads) == len(li_leads)
    for a, b in zip(fb_leads, li_leads):
        assert a.score == b.score
        assert a.intent == b.intent


def test_load_posts_from_file_separates_on_blank_lines_or_dashes(tmp_path) -> None:
    """Format is platform-agnostisch: lege regel of '---' = post-separator."""
    f = tmp_path / "posts.txt"
    f.write_text(
        "Post 1 hier\nmet meerdere regels\n"
        "\n"
        "Post 2 hier\n"
        "---\n"
        "Post 3 hier\n",
        encoding="utf-8",
    )
    posts = load_posts_from_file(f)
    assert len(posts) == 3
    assert posts[0].startswith("Post 1")
    assert posts[1].startswith("Post 2")
    assert posts[2].startswith("Post 3")
