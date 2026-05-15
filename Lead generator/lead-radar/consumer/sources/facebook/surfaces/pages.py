"""PagesSurface -- public-page feed scraper.

Pages share the same DOM structure as Groups, so we reuse the same selectors
and only differ in URL pattern (facebook.com/<slug>) and source/metadata tags.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from consumer import RawPost

from ..core.detector import ChallengeState, detect_state
from ..core.throttle import HumanPace
from ..targets import PageTarget
from .base import ChallengeRaised, Surface
from . import _selectors as sel

if TYPE_CHECKING:
    from playwright.async_api import Page
    from ..core.accounts import Account

log = logging.getLogger("consumer.sources.facebook.surfaces.pages")


def _post_id(slug: str, url: str, idx: int) -> str:
    h = hashlib.sha1(url.encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"facebook_pages:{slug}-{h}-{idx}"


def parse_pages_feed_html(
    html: str,
    *,
    target: PageTarget,
    niche: str,
    run_id: str,
) -> list[RawPost]:
    """Pure parser for a Page's main feed HTML."""
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select(sel.POST_ARTICLE)
    out: list[RawPost] = []
    for idx, art in enumerate(articles):
        if len(out) >= target.max_posts:
            break
        text_el = art.select_one(sel.POST_TEXT_PRIMARY) or art.select_one(sel.POST_TEXT_FALLBACK)
        if not text_el:
            continue
        text = text_el.get_text(separator=" ", strip=True)
        if not text:
            continue
        url_el = art.select_one(f'a[href*="/{target.slug}/posts/"]') or art.select_one('a[href*="/posts/"]')
        post_url = url_el.get("href", "") if url_el else ""
        if post_url.startswith("/"):
            post_url = "https://www.facebook.com" + post_url
        title = text.split("\n", 1)[0][:120]
        out.append(RawPost(
            id=_post_id(target.slug, post_url or f"idx-{idx}", idx),
            source="facebook_pages",
            url=post_url or f"https://www.facebook.com/{target.slug}/",
            title=title,
            text=text,
            author=target.name or target.slug,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            metadata={
                "niche": niche,
                "page_slug": target.slug,
                "page_name": target.name,
                "surface": "pages",
                "run_id": run_id,
            },
        ))
    return out


class PagesSurface(Surface):
    name = "facebook_pages"

    def __init__(self, *, niche: str, run_id: str) -> None:
        self._niche = niche
        self._run_id = run_id

    async def scrape(self, account, target: PageTarget, page) -> list[RawPost]:
        url = f"https://www.facebook.com/{target.slug}/"
        log.info("pages: %s", url)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await HumanPace.read_dwell()
        state = await detect_state(page)
        if state != ChallengeState.OK:
            raise ChallengeRaised(state, surface=self.name, url=url)
        await page.wait_for_selector(sel.FEED_CONTAINER, timeout=15000)
        html = await page.content()
        return parse_pages_feed_html(html, target=target, niche=self._niche, run_id=self._run_id)
