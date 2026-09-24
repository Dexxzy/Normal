"""Thin wrapper around the Anthropic SDK shared by the pipeline steps."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable, TypeVar

DEFAULT_MODEL = "claude-opus-5"

T = TypeVar("T")


def get_client():
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise SystemExit("pip install anthropic   (see requirements.txt)") from e
    return anthropic.Anthropic()


def complete(
    client,
    *,
    system: str,
    user: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    effort: str = "low",
    json_schema: dict | None = None,
    cache_system: bool = True,
) -> str:
    """One request, returns the text block. With ``json_schema`` the text is
    guaranteed-valid JSON for that schema (structured outputs)."""
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [
            {"type": "text", "text": system, **({"cache_control": {"type": "ephemeral"}} if cache_system else {})}
        ],
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": effort},
    }
    if json_schema is not None:
        kwargs["output_config"]["format"] = {"type": "json_schema", "schema": json_schema}
    response = client.messages.create(**kwargs)
    if response.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("hit max_tokens; raise --max-tokens or shrink the chunk")
    return next(b.text for b in response.content if b.type == "text")


def complete_json(client, **kwargs) -> dict:
    return json.loads(complete(client, **kwargs))


def run_parallel(
    items: Iterable[T],
    fn: Callable[[T], Any],
    workers: int = 4,
    label: str = "items",
    retries: int = 3,
) -> list[tuple[T, Any | None, Exception | None]]:
    """Map fn over items with a thread pool, simple retry, and a progress line."""
    import anthropic

    def attempt(item):
        delay = 2.0
        for i in range(retries + 1):
            try:
                return fn(item)
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                if i == retries:
                    raise
                time.sleep(delay)
                delay *= 2

    items = list(items)
    results: list = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(attempt, it): it for it in items}
        for n, fut in enumerate(as_completed(futures), 1):
            it = futures[fut]
            try:
                results.append((it, fut.result(), None))
            except Exception as e:  # keep going, report at the end
                results.append((it, None, e))
            print(f"\r{label}: {n}/{len(items)}", end="", flush=True)
    print()
    return results
