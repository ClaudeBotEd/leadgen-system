"""Structured logging + optionele Sentry init.

JSON-lines naar stderr zodat Grafana Loki / Datadog / Hetzner journalctl
ze direct kunnen parsen.  Per run-ID worden alle logs aan elkaar geknoopt.

Bij ontbreken van SENTRY_DSN env: Sentry wordt niet geïnitialiseerd.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any


class JsonFormatter(logging.Formatter):
    """Eén JSON-record per logregel — stabiel veldformaat voor log-aggregator."""

    def __init__(self, *, run_id: str | None = None) -> None:
        super().__init__()
        self.run_id = run_id or str(uuid.uuid4())[:12]

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": int(time.time() * 1000),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "run_id": self.run_id,
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, val in record.__dict__.items():
            if key in payload or key.startswith("_"):
                continue
            if key in {"args", "asctime", "created", "exc_info", "exc_text",
                       "filename", "funcName", "levelname", "levelno", "lineno",
                       "module", "msecs", "message", "msg", "name", "pathname",
                       "process", "processName", "relativeCreated", "stack_info",
                       "thread", "threadName", "taskName"}:
                continue
            try:
                json.dumps(val)
                payload[key] = val
            except (TypeError, ValueError):
                payload[key] = str(val)
        return json.dumps(payload, ensure_ascii=False)


class _RunIdFilter(logging.Filter):
    def __init__(self, run_id: str) -> None:
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id
        return True


def setup_logging(
    *,
    verbose: bool = False,
    json_format: bool | None = None,
    run_id: str | None = None,
    sentry_dsn: str | None = None,
) -> str:
    """Configure root logger.  Returns het gebruikte run_id."""
    if json_format is None:
        json_format = os.environ.get("LEAD_RADAR_LOG_FORMAT", "").lower() == "json"

    level = logging.DEBUG if verbose else logging.INFO
    run_id = run_id or str(uuid.uuid4())[:12]

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stderr)
    if json_format:
        handler.setFormatter(JsonFormatter(run_id=run_id))
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s [run=%(run_id)s]: %(message)s",
            datefmt="%H:%M:%S",
        ))
        handler.addFilter(_RunIdFilter(run_id))

    root.setLevel(level)
    root.addHandler(handler)

    sentry_dsn = sentry_dsn or os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        _init_sentry(sentry_dsn, run_id=run_id, verbose=verbose)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return run_id


def _init_sentry(dsn: str, *, run_id: str, verbose: bool) -> None:
    """Initialize Sentry zonder hard dependency — skip als sentry_sdk ontbreekt."""
    try:
        import sentry_sdk  # type: ignore[import-not-found]
        from sentry_sdk.integrations.logging import LoggingIntegration  # type: ignore[import-not-found]
    except ImportError:
        logging.getLogger(__name__).info(
            "SENTRY_DSN set maar sentry-sdk niet geïnstalleerd — skipping",
        )
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("LEAD_RADAR_ENV", "dev"),
        traces_sample_rate=0.05,
        integrations=[
            LoggingIntegration(
                level=logging.DEBUG if verbose else logging.INFO,
                event_level=logging.WARNING,
            ),
        ],
    )
    sentry_sdk.set_tag("run_id", run_id)
    logging.getLogger(__name__).info("Sentry geïnitialiseerd voor run %s", run_id)


__all__ = ["setup_logging", "JsonFormatter"]
