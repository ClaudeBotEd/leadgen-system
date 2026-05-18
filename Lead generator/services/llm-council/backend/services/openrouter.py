"""Async OpenRouter API client with structured logging + streaming."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict, List, Optional

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


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    *,
    timeout: Optional[float] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Call a single model. Returns None on recoverable failure (graceful degradation)."""
    settings = get_settings()
    timeout = timeout if timeout is not None else settings.request_timeout_seconds

    payload: Dict[str, Any] = {"model": model, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(settings.openrouter_url, headers=_headers(), json=payload)
            r.raise_for_status()
            data = r.json()
            msg = data["choices"][0]["message"]
            return {
                "content": msg.get("content") or "",
                "reasoning_details": msg.get("reasoning_details"),
            }
    except httpx.HTTPStatusError as e:
        log.warning(
            "openrouter_http_error",
            model=model,
            status=e.response.status_code,
            body=e.response.text[:500],
        )
        return None
    except (httpx.TimeoutException, httpx.RequestError) as e:
        log.warning("openrouter_transport_error", model=model, error=str(e))
        return None
    except Exception as e:
        log.exception("openrouter_unexpected", model=model, error=str(e))
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    **kwargs: Any,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Fan out to many models concurrently. Returns dict keyed by model id."""
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
