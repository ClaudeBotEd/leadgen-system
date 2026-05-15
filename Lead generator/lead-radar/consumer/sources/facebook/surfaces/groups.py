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

        # Sync handler -- just stash the Response object.  We'll await .json() after nav.
        # IMPORTANT: do not register an async function here -- Playwright won't await it.
        graphql_responses: list = []
        def _on_response(resp) -> None:
            try:
                if "/api/graphql/" not in resp.url:
                    return
                # Check operation-name in BOTH header (x-fb-friendly-name) and body --
                # FB sometimes only puts it in one or the other.
                req = resp.request
                friendly_name = (req.headers or {}).get("x-fb-friendly-name", "") or ""
                post_data = req.post_data or ""
                # Permissive match -- FB renames Comet-prefixed operations every few
                # months; match substring "GroupsFeed" / "GroupsComet" / "CometGroup"
                # to catch the rename family.
                wanted = any(
                    needle in haystack
                    for haystack in (friendly_name, post_data)
                    for needle in ("GroupsFeed", "GroupsComet", "CometGroup")
                )
                if wanted:
                    graphql_responses.append(resp)
            except Exception:
                pass  # never let a capture error break the scrape

        page.on("response", _on_response)

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await HumanPace.read_dwell()

        state = await detect_state(page)
        if state != ChallengeState.OK:
            raise ChallengeRaised(state, surface=self.name, url=url)

        await page.wait_for_selector(sel.FEED_CONTAINER, timeout=15000)
        await self._scroll_burst(page)
        # Give late GraphQL responses a moment to arrive
        await HumanPace.read_dwell()
        html = await page.content()
        dom_posts = parse_groups_feed_html(html, target=target, niche=self._niche, run_id=self._run_id)

        if len(dom_posts) >= target.max_posts // 2:
            return dom_posts

        log.warning(
            "groups: DOM extraction underperformed (%d/%d) -- trying GraphQL fallback (%d captured)",
            len(dom_posts), target.max_posts, len(graphql_responses),
        )
        for resp in graphql_responses:
            try:
                body = await resp.json()
            except Exception as exc:
                log.debug("groups: GraphQL body parse failed: %s", exc)
                continue
            gql_posts = parse_groups_graphql_response(body, target=target, niche=self._niche, run_id=self._run_id)
            if gql_posts:
                return gql_posts
        return dom_posts

    async def _scroll_burst(self, page) -> None:
        for _ in range(random.randint(2, 4)):
            distance = random.randint(200, 600)
            await page.mouse.wheel(0, distance)
            await HumanPace.scroll_gap()


def _walk_for_stories(node, out: list[dict]) -> None:
    """Recursive walk over a GraphQL response collecting story-like dicts.

    FB's GraphQL shape changes between operations (GroupsFeedPaginationQuery,
    CometGroupDiscussionRootSuccessQuery, GroupsCometFeedRegularStoriesPagination,
    ...) so we don't lock to a fixed path.  Instead we walk the tree and pick up
    any dict that has BOTH a 'message.text' (possibly via attached_story) AND a
    way to identify the post (wwwURL, url, or post_id).
    """
    if isinstance(node, dict):
        message = node.get("message")
        text = None
        if isinstance(message, dict):
            text = message.get("text")
        # Some renderings put the text under attached_story.message.text
        if not text:
            attached = node.get("attached_story")
            if isinstance(attached, dict):
                attached_msg = attached.get("message")
                if isinstance(attached_msg, dict):
                    text = attached_msg.get("text")
        if text and (node.get("wwwURL") or node.get("url") or node.get("post_id")):
            out.append({
                "text": text,
                "url": node.get("wwwURL") or node.get("url") or "",
                "actors": node.get("actors") or [],
                "creation_time": node.get("creation_time"),
            })
            # Don't recurse into a node we already captured -- avoids double-counting
            # nested reshared posts.
            return
        for value in node.values():
            _walk_for_stories(value, out)
    elif isinstance(node, list):
        for item in node:
            _walk_for_stories(item, out)


def parse_groups_graphql_response(
    response: dict,
    *,
    target: GroupTarget,
    niche: str,
    run_id: str,
) -> list[RawPost]:
    """Parse an intercepted FB Groups GraphQL response.

    Permissive: recursive walk over the response tree collecting any dict
    that has a ``message.text`` AND a post identifier.  Tolerates FB's
    frequent operation renames and payload-shape changes -- we don't lock
    to ``data.node.group_feed.edges[].node.story``.
    """
    if not isinstance(response, dict):
        return []
    stories: list[dict] = []
    _walk_for_stories(response, stories)

    out: list[RawPost] = []
    for idx, story in enumerate(stories):
        if len(out) >= target.max_posts:
            break
        text = story["text"]
        url = story["url"] or f"https://www.facebook.com/groups/{target.id}/"
        if url.startswith("/"):
            url = "https://www.facebook.com" + url
        actors = story.get("actors") or []
        author = (
            actors[0].get("name")
            if actors and isinstance(actors[0], dict) and actors[0].get("name")
            else None
        )
        created_ts = story.get("creation_time")
        created_at = (
            datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat(timespec="seconds")
            if isinstance(created_ts, (int, float)) else None
        )
        title = text.split("\n", 1)[0][:120]
        out.append(RawPost(
            id=_post_id(target.id, url, idx),
            source="facebook_groups",
            url=url,
            title=title,
            text=text,
            author=author,
            created_at=created_at,
            metadata={
                "niche": niche,
                "group_id": target.id,
                "group_name": target.name,
                "surface": "groups",
                "run_id": run_id,
                "extraction": "graphql",
            },
        ))
    return out
