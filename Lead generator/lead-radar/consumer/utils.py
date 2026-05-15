"""Gedeelde HTTP/rate-limit/dedup helpers voor consumer sources.

Geen externe deps buiten requests. Alle netwerk-fouten worden opgevangen
zodat een falende source de pipeline niet sloopt.
"""
from __future__ import annotations

import json
import logging
import random
import threading
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
    timeout: float = 10.0
    request_delay: float = 2.0
    jitter: float = 0.6
    max_retries: int = 2
    backoff: float = 3.0
    # Max attempts (incl. first) voor Timeout-errors.  Lager dan max_retries+1
    # zodat slow hosts niet 3 × full-timeout opeten = 30s+ per call.
    timeout_max_attempts: int = 2


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
        # Lock om _last_call atomair te lezen/schrijven.  Single-threaded
        # gebruik blijft kostloos (lock is uncontended); voorkomt sleep-skip
        # of dubbele requests als sources ooit parallel runnen.
        self._lock = threading.Lock()

    def _sleep_polite(self):
        with self._lock:
            elapsed = time.monotonic() - self._last_call
        target = self.cfg.request_delay + random.uniform(-self.cfg.jitter, self.cfg.jitter)
        target = max(0.0, target)
        if elapsed < target:
            time.sleep(target - elapsed)

    def get(self, url: str, *, params: dict | None = None, accept_json: bool = False,
            lean_headers: bool = False) -> requests.Response | None:
        """HTTP GET met polite sleep + retry.

        lean_headers: bij True strippen we session-level Accept/Accept-Language/
        Accept-Encoding voor deze call (None-trick in requests).  Nodig voor
        hosts met aggressive anti-bot (Tweakers/DPG): die detecteren onze
        rijke header-set als 'unusual client' en redirecten naar consent-gate
        zelfs met geldige cookies.
        """
        self._sleep_polite()
        last_err: Exception | None = None
        max_attempts = self.cfg.max_retries + 1
        for attempt in range(max_attempts):
            try:
                headers: dict = {}
                if accept_json:
                    headers["Accept"] = "application/json"
                if lean_headers:
                    # None-value strip session-level header voor deze call
                    headers.setdefault("Accept-Language", None)
                    headers.setdefault("Accept-Encoding", None)
                    if not accept_json:
                        headers["Accept"] = None
                resp = self.session.get(url, params=params, timeout=self.cfg.timeout, headers=headers)
                with self._lock:
                    self._last_call = time.monotonic()
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (429, 502, 503, 504):
                    log.warning("Throttled %s on %s (attempt %d/%d)", resp.status_code, url, attempt + 1, max_attempts)
                    time.sleep(self.cfg.backoff * (attempt + 1))
                    continue
                log.info("Non-200 %s on %s — gaf op", resp.status_code, url)
                return None
            except requests.exceptions.SSLError as e:
                # SSL = config issue, niet recoverable: 0 retries
                log.error("SSL fout op %s: %s — geen retry", url, e)
                return None
            except requests.exceptions.Timeout as e:
                # Timeout: max `timeout_max_attempts` (default 2).  Bij 3 attempts
                # × 10s timeout zou 1 broken host 30s+ per call kosten.
                last_err = e
                if attempt + 1 >= self.cfg.timeout_max_attempts:
                    log.warning("Timeout op %s na %d attempt(s): %s — opgeven",
                                url, attempt + 1, e)
                    return None
                log.warning("Timeout op %s (attempt %d/%d): %s",
                            url, attempt + 1, self.cfg.timeout_max_attempts, e)
                time.sleep(self.cfg.backoff * (attempt + 1))
            except requests.exceptions.ConnectionError as e:
                # DNS, connection refused, etc. — niet recoverable in deze run
                log.warning("Connection fout op %s: %s — geen retry", url, e)
                return None
            except requests.RequestException as e:
                # Generic transient — keep retrying
                last_err = e
                log.warning("HTTP error op %s: %s", url, e)
                time.sleep(self.cfg.backoff * (attempt + 1))
        log.error("Opgegeven na %d pogingen op %s: %s", max_attempts, url, last_err)
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
