"""Caddy config generator."""

from __future__ import annotations

from proxysmith.core.resolver import ResolvedConfig
from proxysmith.generators.base import BaseGenerator, GeneratedFile
from proxysmith.generators.nginx import _ConfigWrapper  # reuse wrappers


class CaddyGenerator(BaseGenerator):
    """Generates an idiomatic Caddyfile for all services."""

    template_subdir = "caddy"

    def generate(self, config: ResolvedConfig) -> list[GeneratedFile]:
        """Generate a ``Caddyfile`` for all services.

        Args:
            config: Resolved proxy configuration.

        Returns:
            A list containing one :class:`GeneratedFile`.
        """
        content = self._render(
            "caddy/caddyfile.j2",
            config=_ConfigWrapper(config),
        )
        return [GeneratedFile("caddy/Caddyfile", content)]
