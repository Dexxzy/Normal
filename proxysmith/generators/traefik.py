"""Traefik config generator (Docker labels + file provider)."""

from __future__ import annotations

from proxysmith.core.resolver import ResolvedConfig
from proxysmith.generators.base import BaseGenerator, GeneratedFile
from proxysmith.generators.nginx import _ConfigWrapper  # reuse wrappers


class TraefikGenerator(BaseGenerator):
    """Generates Traefik Docker Compose labels and file provider YAML."""

    template_subdir = "traefik"

    def generate(self, config: ResolvedConfig) -> list[GeneratedFile]:
        """Generate both Docker labels and file provider YAML.

        Args:
            config: Resolved proxy configuration.

        Returns:
            A list of two :class:`GeneratedFile` objects.
        """
        wrapper = _ConfigWrapper(config)

        docker_labels = self._render(
            "traefik/docker_labels.yml.j2",
            config=wrapper,
        )
        file_provider = self._render(
            "traefik/file_provider.yml.j2",
            config=wrapper,
        )

        return [
            GeneratedFile("traefik/docker-compose.labels.yml", docker_labels),
            GeneratedFile("traefik/file-provider.yml", file_provider),
        ]
