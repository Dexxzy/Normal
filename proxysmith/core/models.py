"""Pydantic v2 models for proxysmith.toml schema."""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator


class SSLMode(str, Enum):
    """SSL/TLS provisioning strategy."""

    auto = "auto"       # ACME / Let's Encrypt
    manual = "manual"   # user-supplied cert paths
    none = "none"       # plaintext HTTP only


class AuthMode(str, Enum):
    """Per-service authentication mode."""

    none = "none"
    basic = "basic"             # HTTP Basic Auth (htpasswd)
    forward = "forward"         # Forward auth (Authelia / Authentik)


class GlobalConfig(BaseModel):
    """Top-level [global] block."""

    domain: str = Field(..., description="Base domain, e.g. home.example.com")
    ssl: SSLMode = Field(SSLMode.auto, description="SSL provisioning strategy")
    email: str | None = Field(None, description="ACME contact email (required for ssl=auto)")

    @model_validator(mode="after")
    def email_required_for_auto(self) -> GlobalConfig:
        if self.ssl == SSLMode.auto and not self.email:
            raise ValueError("email is required when ssl = 'auto' (needed for Let's Encrypt)")
        return self


class ServiceConfig(BaseModel):
    """One [[service]] block."""

    name: str = Field(..., description="Short identifier, used in upstream/label names")
    host: str = Field(..., description="Upstream host (IP or DNS name)")
    port: Annotated[int, Field(ge=1, le=65535)] = Field(..., description="Upstream port")
    subdomain: str = Field(..., description="Subdomain prefix → <subdomain>.<global.domain>")

    # Optional feature flags
    websocket: bool = Field(False, description="Enable WebSocket upgrade headers")
    auth: AuthMode = Field(AuthMode.none, description="Authentication mode")
    rate_limit: str | None = Field(
        None,
        description="Rate limit string, e.g. '60/min', '10/s'",
        examples=["60/min", "100/hour"],
    )
    max_upload: str | None = Field(
        None,
        description="Max client body / upload size, e.g. '10G', '500M'",
        examples=["10G", "500M", "100M"],
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Extra response/proxy headers to inject",
    )
    cors: bool = Field(False, description="Add permissive CORS headers")

    @field_validator("name")
    @classmethod
    def name_is_slug(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9][a-z0-9_-]*$", v):
            raise ValueError(
                f"Service name '{v}' must be lowercase alphanumeric with hyphens/underscores"
            )
        return v

    @field_validator("subdomain")
    @classmethod
    def subdomain_is_label(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", v):
            raise ValueError(
                f"Subdomain '{v}' must be a valid DNS label (lowercase, hyphens allowed, "
                "no leading/trailing hyphens)"
            )
        return v

    @field_validator("rate_limit")
    @classmethod
    def rate_limit_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        import re
        if not re.match(r"^\d+/(s|min|hour|day)$", v):
            raise ValueError(
                f"rate_limit '{v}' must match '<number>/<unit>' where unit is s, min, hour, or day"
            )
        return v

    @property
    def fqdn(self) -> str:
        """Fully-qualified domain name — requires GlobalConfig; set by resolver."""
        raise AttributeError("fqdn is set by the resolver, not available on raw ServiceConfig")


class ProxySmithConfig(BaseModel):
    """Root configuration object parsed from proxysmith.toml."""

    global_: GlobalConfig = Field(..., alias="global")
    services: list[ServiceConfig] = Field(..., alias="service", min_length=1)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def no_duplicate_subdomains(self) -> ProxySmithConfig:
        seen: dict[str, str] = {}
        for svc in self.services:
            if svc.subdomain in seen:
                raise ValueError(
                    f"Duplicate subdomain '{svc.subdomain}' used by both "
                    f"'{seen[svc.subdomain]}' and '{svc.name}'"
                )
            seen[svc.subdomain] = svc.name
        return self

    @model_validator(mode="after")
    def no_duplicate_names(self) -> ProxySmithConfig:
        seen: set[str] = set()
        for svc in self.services:
            if svc.name in seen:
                raise ValueError(f"Duplicate service name '{svc.name}'")
            seen.add(svc.name)
        return self
