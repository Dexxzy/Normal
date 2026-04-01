"""Nginx config generator."""

from __future__ import annotations

from proxysmith.core.resolver import ResolvedConfig
from proxysmith.generators.base import BaseGenerator, GeneratedFile


class NginxGenerator(BaseGenerator):
    """Generates Nginx server blocks with upstream definitions."""

    template_subdir = "nginx"

    def generate(self, config: ResolvedConfig) -> list[GeneratedFile]:
        """Generate a single ``proxysmith.conf`` for all services.

        Args:
            config: Resolved proxy configuration.

        Returns:
            A list containing one :class:`GeneratedFile`.
        """
        has_rate_limits = any(svc.rate_limit for svc in config.services)
        ctx = config.as_dict()

        # Rebuild services as dicts with resolved objects accessible by template
        ctx["config"] = config.as_dict()
        ctx["config"]["_services_obj"] = config.services

        content = self._render(
            "nginx/nginx.conf.j2",
            config=_ConfigWrapper(config),
            has_rate_limits=has_rate_limits,
        )
        return [GeneratedFile("nginx/proxysmith.conf", content)]


class _ConfigWrapper:
    """Thin wrapper that lets Jinja2 iterate services as attribute-friendly objects."""

    def __init__(self, config: ResolvedConfig) -> None:
        self.domain = config.domain
        self.ssl_mode = config.ssl_mode.value
        self.email = config.email
        self.services = [_ServiceWrapper(svc) for svc in config.services]

    def __len__(self) -> int:
        return len(self.services)


class _ServiceWrapper:
    """Exposes :class:`ResolvedService` fields as Jinja2-friendly attributes."""

    def __init__(self, svc) -> None:  # noqa: ANN001
        self.name = svc.name
        self.host = svc.host
        self.port = svc.port
        self.subdomain = svc.subdomain
        self.fqdn = svc.fqdn
        self.upstream_name = svc.upstream_name
        self.websocket = svc.websocket
        self.auth = svc.auth
        self.rate_limit = svc.rate_limit
        self.max_upload = svc.max_upload
        self.headers = svc.headers
        self.cors = svc.cors
        self.use_ssl = svc.use_ssl
        self.ssl_mode = svc.ssl_mode.value
