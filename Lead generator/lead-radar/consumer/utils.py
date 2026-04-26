"""Gedeelde HTTP/rate-limit/dedup helpers voor consumer sources.

Geen externe deps buiten requests. Alle netwerk-fouten worden opgevangen
zodat een falende source de pipeline niet sloopt.
"""
from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

log = logging.getLogger("consumer.utils")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class HttpConfig:
    user_agent: str = DEFAULT_USER_AGENT
    timeout: float = 15.0
    request_delay: float = 2.0
    jitter: float = 0.6
    max_retries: int = 2
    backoff: float = 3.0


class PoliteSession:
    """Requests session met rate limiting, retry en jitter — minder kans op blocks."""

    def __init__(self, cfg: HttpConfig | None = None, headers: dict | None = None):
        self.cfg = cfg or HttpConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.cfg.user_agent,
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        })
        if headers:
            self.session.headers.update(headers)
        self._last_call: float = 0.0

    def _sleep_polite(self):
        elapsed = time.monotonic() - self._last_call
        target = self.cfg.request_delay + random.uniform(-self.cfg.jitter, self.cfg.jitter)
        target = max(0.0, target)
        if elapsed < target:
            time.sleep(target - elapsed)

    def get(self, url: str, *, params: dict | None = None, accept_json: bool = False) -> requests.Response | None:
        self._sleep_polite()
        last_err: Exception | None = None
        for attempt in range(self.cfg.max_retries + 1):
            try:
                headers = {}
                if accept_json:
                    headers["Accept"] = "application/json"
                resp = self.session.get(url, params=params, timeout=self.cfg.timeout, headers=headers)
                self._last_call = time.monotonic()
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (429, 502, 503, 504):
                    log.warning("Throttled %s on %s (attempt %d/%d)", resp.status_code, url, attempt + 1, self.cfg.max_retries + 1)
                    time.sleep(self.cfg.backoff * (attempt + 1))
                    continue
                log.info("Non-200 %s on %s — gaf op", resp.status_code, url)
                return None
            except requests.RequestException as e:
                last_err = e
                log.warning("HTTP error op %s: %s", url, e)
                time.sleep(self.cfg.backoff * (attempt + 1))
        log.error("Opgegeven na %d pogingen op %s: %s", self.cfg.max_retries + 1, url, last_err)
        return None


class SeenStore:
    """Simpele JSON-file dedup store. fingerprint -> ISO eerste-zien."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, str] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                log.warning("Kon seen store niet lezen: %s — start leeg", self.path)
                self._data = {}

    def has(self, fingerprint: str) -> bool:
        return fingerprint in self._data

    def add(self, fingerprint: str) -> None:
        self._data.setdefault(fingerprint, datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
        except Exception as e:
            log.warning("Kon seen store niet schrijven: %s — %s", self.path, e)

    def __len__(self) -> int:
        return len(self._data)


def safe_strip(s: str | None) -> str:
    return (s or "").strip()
