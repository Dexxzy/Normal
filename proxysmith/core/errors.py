"""Custom exceptions for ProxySmith."""

from __future__ import annotations


class ProxySmithError(Exception):
    """Base exception for all ProxySmith errors."""


class ConfigError(ProxySmithError):
    """Raised when a proxysmith.toml is invalid or unparseable."""


class ValidationError(ProxySmithError):
    """Raised when service definitions fail semantic validation."""


class GeneratorError(ProxySmithError):
    """Raised when a config generator encounters an unrecoverable error."""


class TemplateError(ProxySmithError):
    """Raised when a Jinja2 template fails to render."""
