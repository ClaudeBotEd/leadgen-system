"""MarketplaceSurface -- DOM scraper for Marketplace search results."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from consumer import RawPost

from ..core.detector import ChallengeState, detect_state
from ..core.throttle import HumanPace
from ..targets import MarketplaceTarget
from .base import BackoffRaised, ChallengeRaised, Surface
from . import _selectors as sel

if TYPE_CHECKING:
    from playwright.async_api import Page
    from ..core.accounts import Account

log = logging.getLogger("consumer.sources.facebook.surfaces.marketplace")


def _post_id(query: str, url: str, idx: int) -> str:
    h = hashlib.sha1((url or query).encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"facebook_marketplace:{h}-{idx}"


def parse_marketplace_html(
    html: str,
    *,
    target: MarketplaceTarget,
    niche: str,
    run_id: str,
) -> list[RawPost]:
    """Pure parser for a Marketplace search-results page."""
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(sel.MARKETPLACE_CARD)
    out: list[RawPost] = []
    for idx, card in enumerate(cards):
        if len(out) >= target.max_results:
            break
        spans = [s.get_text(strip=True) for s in card.find_all("span") if s.get_text(strip=True)]
        if not spans:
            continue
        title = spans[0]
        href = card.get("href", "")
        if href.startswith("/"):
            href = "https://www.facebook.com" + href
        out.append(RawPost(
            id=_post_id(target.query, href, idx),
            source="facebook_marketplace",
            source_id=f"facebook:marketplace/{niche}",
            url=href or f"https://www.facebook.com/marketplace/{target.location_slug}/search?query={quote_plus(target.query)}",
            title=title[:120],
            text=" | ".join(spans),
            author=None,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            metadata={
                "niche": niche,
                "surface": "marketplace",
                "query": target.query,
                "run_id": run_id,
            },
        ))
    return out


class MarketplaceSurface(Surface):
    name = "facebook_marketplace"

    def __init__(self, *, niche: str, run_id: str) -> None:
        self._niche = niche
        self._run_id = run_id

    async def scrape(self, account, target: MarketplaceTarget, page) -> list[RawPost]:
        # Build the search URL with listing_type filter.  Default is "wanted"
        # which is what lead-radar needs (people seeking installers).  FB's
        # exact param name for filtering wanted-vs-sale changes -- verify the
        # generated URL returns the right kind of post before relying on it.
        base = f"https://www.facebook.com/marketplace/{target.location_slug}/search"
        params: list[str] = [f"query={quote_plus(target.query)}"]
        if target.radius_km:
            params.append(f"radius={target.radius_km}")
        # FB Marketplace filter for "Looking for / Wanted" -- current param
        # name as of 2026-05.  Operator must verify against live FB; if the
        # param is renamed, update the mapping here, NOT the per-target config.
        listing_type_param = {
            "wanted": "availability=looking_for_items",
            "sale": "availability=in_stock",
            "all": "",
        }.get(target.listing_type, "")
        if listing_type_param:
            params.append(listing_type_param)
        url = f"{base}?{'&'.join(params)}"
        log.info("marketplace: %s", url)
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await HumanPace.read_dwell()

        state = await detect_state(page)
        # Hard states (CHALLENGED, LOGIN_WALL) abort the run and flip account state.
        # Soft states (RATE_LIMITED) signal back-off without losing the account.
        if state in (ChallengeState.CHALLENGED, ChallengeState.LOGIN_WALL):
            raise ChallengeRaised(state, surface=self.name, url=url)
        if state == ChallengeState.RATE_LIMITED:
            raise BackoffRaised(state, surface=self.name, url=url)

        # Marketplace cards mount via JS after navigation; networkidle isn't
        # enough on a slow run.  Wait explicitly for at least one item-link
        # before reading content.
        try:
            await page.wait_for_selector('a[href^="/marketplace/item/"]',
                                          timeout=15000, state="attached")
        except Exception:
            log.warning("marketplace: no item-cards loaded in 15s -- capturing anyway")

        html = await page.content()
        return parse_marketplace_html(html, target=target, niche=self._niche, run_id=self._run_id)
