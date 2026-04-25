"""Simple per-host rate limiter — voorkomt dat scrapers te agressief gaan.

Gebruik:
    from utils.rate_limiter import RateLimiter
    limiter = RateLimiter(min_delay=2.0)
    limiter.wait("duckduckgo.com")  # blokkeert tot 2s na laatste call op deze host
"""

import time
import threading
from urllib.parse import urlparse


class RateLimiter:
    """Token-bucket per hostname met minimum delay tussen requests."""

    def __init__(self, min_delay: float = 2.0):
        self.min_delay = min_delay
        self._last_call: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, url_or_host: str) -> None:
        """Blokkeer tot er weer een request mag op deze host."""
        host = self._extract_host(url_or_host)
        with self._lock:
            last = self._last_call.get(host, 0.0)
            elapsed = time.time() - last
            sleep_for = max(0.0, self.min_delay - elapsed)
        if sleep_for > 0:
            time.sleep(sleep_for)
        with self._lock:
            self._last_call[host] = time.time()

    def reset(self, host: str | None = None) -> None:
        with self._lock:
            if host is None:
                self._last_call.clear()
            else:
                self._last_call.pop(self._extract_host(host), None)

    @staticmethod
    def _extract_host(url_or_host: str) -> str:
        if "://" in url_or_host:
            parsed = urlparse(url_or_host)
            return parsed.netloc.lower()
        return url_or_host.lower()
