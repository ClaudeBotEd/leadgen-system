"""PlaywrightSession — async context manager around a stealth Chromium.

Reuses the account's persistent profile directory so cookies/localStorage
survive across runs.  Applies tf-playwright-stealth patches to every new
page, PLUS additional CDP-leak patches that stealth alone does not cover.

CDP-leak patches (critical — FB uses these vectors):

* ``window.__playwright__`` and related Playwright-injected globals are deleted
  before any page script runs.  Stealth plugin patches the most common ones
  but the namespace varies between Playwright versions; this is a belt-and-
  suspenders nuke.
* ``navigator.permissions.query`` for ``notifications`` is overridden to return
  ``"default"`` (real Chrome) instead of ``"denied"`` (Playwright's CDP leaks
  this).
* ``chrome.runtime`` is shimmed so a deep probe returns plausible values
  instead of throwing.
"""
from __future__ import annotations

import logging
import random
from pathlib import Path

from playwright.async_api import BrowserContext, Page, async_playwright
from playwright_stealth import stealth_async  # tf-playwright-stealth ships as `playwright_stealth`

from .accounts import Account
from .proxy import HTTPProxy, NoProxy
from .state_io import cleanup_chromium_singletons


# Script injected into every new page BEFORE any page-side JS runs.
# Hides Playwright/CDP fingerprints FB checks for.
_CDP_PATCH_SCRIPT = r"""
(() => {
  // Nuke any Playwright-injected globals
  for (const k of Object.keys(window)) {
    if (k.startsWith('__playwright') || k.startsWith('__pw_')) {
      try { delete window[k]; } catch (e) {}
    }
  }

  // navigator.permissions.query for 'notifications' returns 'denied' under
  // Playwright CDP — real Chrome returns 'default' unless the user explicitly
  // chose.
  if (navigator.permissions && navigator.permissions.query) {
    const original = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (params) => {
      if (params && params.name === 'notifications') {
        return Promise.resolve({state: 'default', onchange: null});
      }
      return original(params);
    };
  }

  // Make chrome.runtime present-but-shallow so the deep-probe heuristic
  // doesn't fingerprint headless/Playwright
  if (!window.chrome) {
    window.chrome = {};
  }
  if (!window.chrome.runtime) {
    window.chrome.runtime = {
      connect: () => ({ disconnect: () => {} }),
      sendMessage: () => {},
      onMessage: { addListener: () => {} },
    };
  }
})();
"""

log = logging.getLogger("consumer.sources.facebook.session")

_BASE_VIEWPORT: tuple[int, int] = (1920, 1080)
_VIEWPORT_JITTER: int = 50


def _jittered_viewport() -> dict[str, int]:
    w, h = _BASE_VIEWPORT
    return {
        "width": w + random.randint(-_VIEWPORT_JITTER, _VIEWPORT_JITTER),
        "height": h + random.randint(-_VIEWPORT_JITTER, _VIEWPORT_JITTER),
    }


class PlaywrightSession:
    """Async context manager that yields a logged-in BrowserContext.

    Usage::

        async with PlaywrightSession(account, state_dir=Path("data/fb_state")) as ctx:
            page = await new_stealth_page(ctx)
            ...
    """

    def __init__(
        self,
        account: Account,
        state_dir: Path,
        proxy: HTTPProxy | None = None,
        headless: bool = False,
    ) -> None:
        self._account = account
        self._state_dir = state_dir
        self._proxy = proxy or NoProxy()
        self._headless = headless
        self._playwright = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> BrowserContext:
        user_data_dir = self._state_dir / self._account.id / "profile"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        # Sweep stale Chromium singleton files left by a previous non-clean exit.
        # Without this, launch_persistent_context will hang on the SingletonLock.
        cleanup_chromium_singletons(user_data_dir)

        self._playwright = await async_playwright().start()
        launch_kwargs: dict = {
            "headless": self._headless,
            "viewport": _jittered_viewport(),
        }
        proxy_cfg = self._proxy.playwright_proxy_config()
        if proxy_cfg:
            launch_kwargs["proxy"] = proxy_cfg
        log.info(
            "FB session launch: account=%s headless=%s viewport=%sx%s proxy=%s",
            self._account.id, self._headless,
            launch_kwargs["viewport"]["width"], launch_kwargs["viewport"]["height"],
            bool(proxy_cfg),
        )
        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                **launch_kwargs,
            )
        except Exception:
            # If launch fails, stop playwright so we don't leak the subprocess
            await self._playwright.stop()
            self._playwright = None
            raise

        # Apply the CDP-leak patches to every new page in this context.
        # add_init_script runs the JS BEFORE any page-side script executes,
        # which is the only way to hide globals from FB's fingerprinting code.
        await self._context.add_init_script(_CDP_PATCH_SCRIPT)
        return self._context

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # Guarantee cleanup of both context and playwright even if one fails.
        try:
            if self._context is not None:
                await self._context.close()
        finally:
            if self._playwright is not None:
                await self._playwright.stop()


async def new_stealth_page(context: BrowserContext) -> Page:
    """Open a new page and apply the stealth patches before navigation."""
    page = await context.new_page()
    await stealth_async(page)
    return page
