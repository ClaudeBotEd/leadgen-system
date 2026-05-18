"""Async OpenRouter API client with structured logging + streaming."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx

from ..config import get_settings
from ..errors import UpstreamModelError
from ..logging import get_logger

log = get_logger("openrouter")


def _headers() -> Dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/karpathy/llm-council",
        "X-Title": "LLM Council (Lead generator)",
    }


def _classify_http_error(status: int, body: str) -> Tuple[str, str]:
    """Map an OpenRouter HTTP error to (error_kind, human_message)."""
    upstream_msg = ""
    try:
        upstream_msg = (json.loads(body).get("error") or {}).get("message", "") or ""
    except (json.JSONDecodeError, AttributeError):
        upstream_msg = body[:200]

    if status == 402:
        return (
            "insufficient_credits",
            upstream_msg
            or "OpenRouter account has insufficient credits. Top up at https://openrouter.ai/settings/credits.",
        )
    if status == 401:
        return ("unauthorized", upstream_msg or "OpenRouter API key invalid or missing.")
    if status == 404:
        return ("invalid_model", upstream_msg or "Model not found on OpenRouter.")
    if status == 429:
        return ("rate_limited", upstream_msg or "OpenRouter rate limit hit.")
    if 500 <= status < 600:
        return ("upstream_5xx", upstream_msg or f"OpenRouter upstream error ({status}).")
    return ("http_error", upstream_msg or f"OpenRouter HTTP {status}.")


def _success(
    content: str, reasoning_details: Any, usage: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    return {
        "ok": True,
        "content": content,
        "reasoning_details": reasoning_details,
        "usage": usage,
    }


def _failure(kind: str, message: str, *, status: Optional[int] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "error_kind": kind,
        "status": status,
        "message": message,
    }


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    *,
    timeout: Optional[float] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Call a single model. Always returns a dict with `ok` flag.

    On success: {"ok": True, "content", "reasoning_details", "usage"}
    On failure: {"ok": False, "error_kind", "status", "message"}
    """
    settings = get_settings()
    timeout = timeout if timeout is not None else settings.request_timeout_seconds

    payload: Dict[str, Any] = {"model": model, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    log.debug("openrouter_request", model=model, message_count=len(messages), timeout=timeout)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(settings.openrouter_url, headers=_headers(), json=payload)
            r.raise_for_status()
            data = r.json()
            msg = data["choices"][0]["message"]
            usage = data.get("usage")
            if usage:
                log.info(
                    "openrouter_usage",
                    model=model,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                )
            return _success(msg.get("content") or "", msg.get("reasoning_details"), usage)
    except httpx.HTTPStatusError as e:
        body = e.response.text or ""
        kind, message = _classify_http_error(e.response.status_code, body)
        log.warning(
            "openrouter_http_error",
            model=model,
            status=e.response.status_code,
            error_kind=kind,
            body=body[:500],
        )
        return _failure(kind, message, status=e.response.status_code)
    except httpx.TimeoutException as e:
        log.warning("openrouter_timeout", model=model, error=str(e))
        return _failure("timeout", f"Timed out calling {model}.")
    except httpx.RequestError as e:
        log.warning("openrouter_transport_error", model=model, error=str(e))
        return _failure("transport", f"Network error calling {model}: {e}")
    except Exception as e:
        log.exception("openrouter_unexpected", model=model, error=str(e))
        return _failure("unexpected", f"Unexpected error calling {model}: {e}")


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    **kwargs: Any,
) -> Dict[str, Dict[str, Any]]:
    """Fan out to many models concurrently. Returns dict keyed by model id.

    Every value is a structured result dict (`ok` flag); never None.
    """
    tasks = [query_model(m, messages, **kwargs) for m in models]
    results = await asyncio.gather(*tasks)
    return {m: r for m, r in zip(models, results)}


async def stream_model(
    model: str,
    messages: List[Dict[str, str]],
    *,
    timeout: Optional[float] = None,
    temperature: Optional[float] = None,
) -> AsyncIterator[str]:
    """Yield text deltas from a streaming completion (SSE under the hood)."""
    settings = get_settings()
    timeout = timeout if timeout is not None else settings.request_timeout_seconds

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", settings.openrouter_url, headers=_headers(), json=payload
            ) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace")
                    raise UpstreamModelError(
                        f"OpenRouter stream failed ({response.status_code})",
                        details={"model": model, "body": body[:500]},
                    )
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (
                        obj.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content")
                    )
                    if delta:
                        yield delta
    except UpstreamModelError:
        raise
    except Exception as e:
        log.exception("openrouter_stream_error", model=model, error=str(e))
        raise UpstreamModelError(
            f"Streaming failed for {model}: {e}", details={"model": model}
        ) from e
