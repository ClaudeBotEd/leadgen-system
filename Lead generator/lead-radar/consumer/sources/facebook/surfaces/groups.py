"""GroupsSurface -- DOM scraper for FB Groups feed.

The Playwright-driving ``scrape()`` method navigates to the group and grabs
``page.content()``, then delegates to the pure-Python ``parse_groups_feed_html``
function for the actual extraction.  Splitting it this way lets us unit-test
the parser on static fixtures without spinning up a browser.

GraphQL fallback (added in Task 10) attaches to the same scrape() flow.
"""
from __future__ import annotations

import hashlib
import logging
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from consumer import RawPost

from ..core.detector import ChallengeState, detect_state
from ..core.throttle import HumanPace
from ..targets import GroupTarget
from .base import ChallengeRaised, Surface
from . import _selectors as sel

if TYPE_CHECKING:
    from playwright.async_api import Page
    from ..core.accounts import Account

log = logging.getLogger("consumer.sources.facebook.surfaces.groups")


def _post_id(group_id: str, post_url: str, idx: int) -> str:
    h = hashlib.sha1(post_url.encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"facebook_groups:{group_id}-{h}-{idx}"


def parse_groups_feed_html(
    html: str,
    *,
    target: GroupTarget,
    niche: str,
    run_id: str,
) -> list[RawPost]:
    """Extract RawPosts from a Groups feed HTML snapshot.

    Pure function: no IO, no Playwright.  Returns at most ``target.max_posts``
    posts.  Articles missing a text body are skipped.
    """
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

        author_el = art.select_one('strong a[role=link]')
        author = author_el.get_text(strip=True) if author_el else None

        url_el = art.select_one('a[href*="/posts/"]') or art.select_one('a[href*="/permalink/"]')
        post_url = url_el.get("href", "") if url_el else ""
        if post_url.startswith("/"):
            post_url = "https://www.facebook.com" + post_url

        title = text.split("\n", 1)[0][:120]

        ts_el = art.select_one('a[href*="/posts/"] span') or art.select_one('a[href*="/permalink/"] span')
        ts_text = ts_el.get_text(strip=True) if ts_el else None

        out.append(RawPost(
            id=_post_id(target.id, post_url or f"idx-{idx}", idx),
            source="facebook_groups",
            url=post_url or f"https://www.facebook.com/groups/{target.id}/",
            title=title,
            text=text,
            author=author,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            metadata={
                "niche": niche,
                "group_id": target.id,
                "group_name": target.name,
                "surface": "groups",
                "run_id": run_id,
                "raw_timestamp": ts_text,
            },
        ))
    return out


class GroupsSurface(Surface):
    """Scrapes the top N posts from a single FB group's main feed."""

    name = "facebook_groups"

    def __init__(self, *, niche: str, run_id: str) -> None:
        self._niche = niche
        self._run_id = run_id

    async def scrape(self, account, target: GroupTarget, page) -> list[RawPost]:
        url = f"https://www.facebook.com/groups/{target.id}/"
        log.info("groups: navigate %s", url)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await HumanPace.read_dwell()

        state = await detect_state(page)
        if state != ChallengeState.OK:
            raise ChallengeRaised(state, surface=self.name, url=url)

        await page.wait_for_selector(sel.FEED_CONTAINER, timeout=15000)
        await self._scroll_burst(page)
        html = await page.content()
        return parse_groups_feed_html(html, target=target, niche=self._niche, run_id=self._run_id)

    async def _scroll_burst(self, page) -> None:
        for _ in range(random.randint(2, 4)):
            distance = random.randint(200, 600)
            await page.mouse.wheel(0, distance)
            await HumanPace.scroll_gap()
