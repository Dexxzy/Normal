"""TOML parsing and Pydantic validation for proxysmith.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from proxysmith.core.errors import ConfigError, ValidationError
from proxysmith.core.models import ProxySmithConfig


def load_config(path: Path) -> ProxySmithConfig:
    """Parse *path* as TOML and validate against the ProxySmith schema.

    Args:
        path: Filesystem path to ``proxysmith.toml``.

    Returns:
        A validated :class:`~proxysmith.core.models.ProxySmithConfig`.

    Raises:
        ConfigError: If the file cannot be read or is not valid TOML.
        ValidationError: If the schema or semantic rules are violated.
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"TOML parse error in {path}: {exc}") from exc

    # tomllib gives us {"global": {...}, "service": [{...}, ...]}
    # Pydantic model expects "global" aliased to "global_" and "service" aliased to "services"
    try:
        return ProxySmithConfig.model_validate(raw)
    except PydanticValidationError as exc:
        messages = _format_pydantic_errors(exc)
        raise ValidationError(f"Config validation failed:\n{messages}") from exc


def _format_pydantic_errors(exc: PydanticValidationError) -> str:
    """Convert Pydantic v2 errors into human-readable lines."""
    lines: list[str] = []
    for err in exc.errors():
        loc = " → ".join(str(p) for p in err["loc"]) if err["loc"] else "(root)"
        msg = err["msg"]
        lines.append(f"  • {loc}: {msg}")
    return "\n".join(lines)
