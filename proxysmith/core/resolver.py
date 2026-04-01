"""Resolve raw config into enriched render context dicts for generators."""

from __future__ import annotations

from dataclasses import dataclass, field

from proxysmith.core.models import ProxySmithConfig, ServiceConfig, SSLMode


@dataclass
class ResolvedService:
    """A :class:`ServiceConfig` enriched with computed fields."""

    # --- raw fields mirrored for convenience ---
    name: str
    host: str
    port: int
    subdomain: str
    websocket: bool
    auth: str
    rate_limit: str | None
    max_upload: str | None
    headers: dict[str, str]
    cors: bool

    # --- computed ---
    fqdn: str               # subdomain.domain
    upstream_name: str      # nginx upstream block name: proxysmith_<name>
    use_ssl: bool
    ssl_mode: SSLMode

    def as_dict(self) -> dict:
        """Return all fields as a plain dict for Jinja2 rendering."""
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "subdomain": self.subdomain,
            "fqdn": self.fqdn,
            "upstream_name": self.upstream_name,
            "websocket": self.websocket,
            "auth": self.auth,
            "rate_limit": self.rate_limit,
            "max_upload": self.max_upload,
            "headers": self.headers,
            "cors": self.cors,
            "use_ssl": self.use_ssl,
            "ssl_mode": self.ssl_mode.value,
        }


@dataclass
class ResolvedConfig:
    """Top-level resolved configuration passed to generators."""

    domain: str
    ssl_mode: SSLMode
    email: str | None
    services: list[ResolvedService] = field(default_factory=list)

    def as_dict(self) -> dict:
        """Return all fields as a plain dict for Jinja2 rendering."""
        return {
            "domain": self.domain,
            "ssl_mode": self.ssl_mode.value,
            "email": self.email,
            "services": [svc.as_dict() for svc in self.services],
        }


def resolve(config: ProxySmithConfig) -> ResolvedConfig:
    """Enrich a :class:`ProxySmithConfig` with computed/derived fields.

    Args:
        config: A validated raw config from the parser.

    Returns:
        A :class:`ResolvedConfig` ready for generator consumption.
    """
    g = config.global_
    ssl_mode = g.ssl
    use_ssl = ssl_mode != SSLMode.none

    services: list[ResolvedService] = []
    for svc in config.services:
        fqdn = f"{svc.subdomain}.{g.domain}"
        services.append(
            ResolvedService(
                name=svc.name,
                host=svc.host,
                port=svc.port,
                subdomain=svc.subdomain,
                fqdn=fqdn,
                upstream_name=f"proxysmith_{svc.name}",
                websocket=svc.websocket,
                auth=svc.auth.value,
                rate_limit=svc.rate_limit,
                max_upload=svc.max_upload,
                headers=svc.headers,
                cors=svc.cors,
                use_ssl=use_ssl,
                ssl_mode=ssl_mode,
            )
        )

    return ResolvedConfig(
        domain=g.domain,
        ssl_mode=ssl_mode,
        email=g.email,
        services=services,
    )
