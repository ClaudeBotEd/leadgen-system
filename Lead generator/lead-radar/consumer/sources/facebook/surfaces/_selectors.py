"""Centralized CSS selectors for the FB UI.

FB rewrites class names constantly but role/aria attributes are much more
stable.  Keeping every selector here means a single-file edit when FB
breaks something.
"""
from __future__ import annotations

# ── Groups & Pages share the same feed UI ───────────────────────────────
FEED_CONTAINER = '[role=feed]'
POST_ARTICLE = '[role=article]'
POST_TEXT_PRIMARY = '[data-ad-preview="message"]'
POST_TEXT_FALLBACK = '[data-ad-comet-preview="message"]'
POST_AUTHOR_LINK = '[role=article] strong a[role=link]'
POST_URL_PRIMARY = '[role=article] a[href*="/posts/"]'
POST_URL_FALLBACK = '[role=article] a[href*="/permalink/"]'
POST_TIMESTAMP = '[role=article] a[href*="/posts/"] span'

# ── Marketplace ─────────────────────────────────────────────────────────
MARKETPLACE_CARD = '[aria-label*="Marketplace"] a[role=link]'
MARKETPLACE_CARD_TITLE = 'span'  # first non-empty text span inside card
