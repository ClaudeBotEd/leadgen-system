"""Apify-driven Facebook Groups collector.

Reads ``config/facebook_targets.yaml``, invokes the
``apify/facebook-groups-scraper`` actor per configured group, maps the
returned dataset items to ``RawPost`` records, and drops a JSONL file
into ``data/fb_queue/`` for the existing pipeline drain to pick up.

Design choices:

* Same on-disk handoff as the self-hosted scraper (``queue.write_jsonl``),
  so ``run_consumer.py`` doesn't need to know whether Apify or the
  self-hosted Playwright runner produced the posts.
* One Apify run per group target.  Per-group budget visibility beats
  batched runs where one bad group can poison the dataset.
* Item parsing is permissive — the Apify actor's output schema has
  changed several times; we read several plausible field names and
  skip items that don't yield enough text to be useful.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from consumer import RawPost

from .apify_client import (
    ActorRunResult,
    ApifyBudgetExceeded,
    ApifyRunner,
)
from .queue import write_jsonl
from .targets import FacebookTargetsConfig, GroupTarget

log = logging.getLogger("consumer.sources.facebook.apify_groups")

ACTOR_ID = "apify/facebook-groups-scraper"


def _post_id(group_id: str, post_url: str, fallback_idx: int) -> str:
    """Stable per-group post id — mirrors surfaces/groups.py for dedup compat."""
    seed = post_url or f"idx-{fallback_idx}"
    h = hashlib.sha1(seed.encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"facebook_groups:{group_id}-{h}-{fallback_idx}"


def _first(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return d[k] for the first present key with a truthy value, else default."""
    for k in keys:
        if k in d and d[k]:
            return d[k]
    return default


def _coerce_iso(value: Any) -> str | None:
    """Coerce Apify's mixed-format timestamps to ISO-8601 UTC, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat(timespec="seconds")
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
            except ValueError:
                continue
        return s
    return None


def map_item_to_rawpost(
    item: dict[str, Any],
    *,
    target: GroupTarget,
    niche: str,
    run_id: str,
    idx: int,
) -> RawPost | None:
    """Convert one Apify dataset item to a RawPost, or None to skip.

    Pure function — unit-tested without network.  Items missing a text
    body are dropped.
    """
    text = (
        _first(item, "text", "message", "content", "postText", "rawText", default="")
        or ""
    ).strip()
    if not text:
        return None

    post_url = (
        _first(item, "postUrl", "url", "permalink", "facebookUrl", default="") or ""
    ).strip()
    if post_url.startswith("/"):
        post_url = "https://www.facebook.com" + post_url

    author_raw: Any = _first(item, "user", "author", "owner", "profile", default=None)
    if isinstance(author_raw, dict):
        author = author_raw.get("name") or author_raw.get("username") or author_raw.get("id")
    else:
        author = author_raw or _first(item, "userName", "authorName", default=None)
    if isinstance(author, str):
        author = author.strip() or None
    elif author is not None and not isinstance(author, str):
        author = None

    created_at = _coerce_iso(
        _first(item, "time", "timestamp", "publishedAt", "createdAt", default=None)
    )

    title = text.split("\n", 1)[0][:120]

    return RawPost(
        id=_post_id(target.id, post_url, idx),
        source="facebook_groups",
        source_id=f"facebook:{target.id}",
        url=post_url or f"https://www.facebook.com/groups/{target.id}/",
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
            "collector": "apify",
            "apify_actor": ACTOR_ID,
            "raw_timestamp": item.get("time") or item.get("timestamp"),
        },
    )


def items_to_rawposts(
    items: Iterable[dict[str, Any]],
    *,
    target: GroupTarget,
    niche: str,
    run_id: str,
) -> list[RawPost]:
    out: list[RawPost] = []
    for idx, item in enumerate(items):
        if len(out) >= target.max_posts:
            break
        rp = map_item_to_rawpost(item, target=target, niche=niche, run_id=run_id, idx=idx)
        if rp is not None:
            out.append(rp)
    return out


def _build_run_input(target: GroupTarget) -> dict[str, Any]:
    """Construct the actor's run input for a single group target.

    Both ``startUrls`` and ``resultsLimit`` are the primary knobs; the
    rest are belt-and-braces aliases the actor has historically accepted
    or renamed.  ``commentsMode=NONE`` keeps the run cheap and focused on
    the post itself — comments would multiply compute units 5-10×.
    """
    group_url = f"https://www.facebook.com/groups/{target.id}/"
    return {
        "startUrls": [{"url": group_url}],
        "resultsLimit": target.max_posts,
        "maxPosts": target.max_posts,
        "maxPostsPerStartUrl": target.max_posts,
        "commentsMode": "NONE",
    }


def collect_groups(
    *,
    runner: ApifyRunner,
    config: FacebookTargetsConfig,
    queue_dir: Path,
    niche_filter: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run the Apify actor for each configured group and queue the posts.

    ``niche_filter`` of ``None`` / ``"all"`` processes every niche.
    Returns a summary dict for logging/CLI output.
    """
    run_id = run_id or datetime.now(timezone.utc).strftime("apify-groups-%Y%m%dT%H%M%SZ")
    queue_dir.mkdir(parents=True, exist_ok=True)

    all_posts: list[RawPost] = []
    per_group: list[dict[str, Any]] = []
    total_cost = 0.0
    stopped_early = False

    for niche, bundle in config.niches.items():
        if niche_filter and niche_filter not in ("all", "") and niche != niche_filter:
            continue
        for target in bundle.groups:
            try:
                result: ActorRunResult = runner.run_actor(
                    ACTOR_ID,
                    _build_run_input(target),
                    timeout_secs=600,
                )
            except ApifyBudgetExceeded as exc:
                log.warning("apify_groups: budget hit at %s/%s — %s", niche, target.id, exc)
                stopped_early = True
                break
            except Exception as exc:  # noqa: BLE001 — one bad group must not kill the rest
                log.error("apify_groups: %s/%s failed: %s", niche, target.id, exc)
                per_group.append({
                    "niche": niche, "group_id": target.id, "ok": False,
                    "error": str(exc), "posts": 0, "cost_usd": 0.0,
                })
                continue

            posts = items_to_rawposts(result.items, target=target, niche=niche, run_id=run_id)
            all_posts.extend(posts)
            total_cost += result.cost_usd
            per_group.append({
                "niche": niche, "group_id": target.id, "group_name": target.name,
                "ok": True, "posts": len(posts),
                "raw_items": len(result.items), "cost_usd": result.cost_usd,
                "apify_run_id": result.run_id,
            })
            log.info("apify_groups: %s/%s — %d posts ($%.4f)",
                     niche, target.id, len(posts), result.cost_usd)

        if stopped_early:
            break

    out_path = queue_dir / f"{run_id}.jsonl"
    write_jsonl(out_path, all_posts)
    log.info("apify_groups: wrote %d posts to %s (total $%.4f)",
             len(all_posts), out_path, total_cost)

    return {
        "run_id": run_id,
        "queue_file": str(out_path),
        "total_posts": len(all_posts),
        "total_cost_usd": round(total_cost, 4),
        "stopped_early": stopped_early,
        "per_group": per_group,
    }


__all__ = [
    "ACTOR_ID",
    "collect_groups",
    "items_to_rawposts",
    "map_item_to_rawpost",
]
