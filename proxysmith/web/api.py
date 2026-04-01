"""FastAPI backend for ProxySmith web UI."""

from __future__ import annotations

import hashlib
import io
import tomllib
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from proxysmith import __version__
from proxysmith.core.errors import ConfigError, ValidationError
from proxysmith.core.parser import load_config, _format_pydantic_errors
from proxysmith.core.models import ProxySmithConfig
from proxysmith.core.resolver import resolve
from proxysmith.generators import CaddyGenerator, NginxGenerator, TraefikGenerator
from proxysmith.generators.base import BaseGenerator

app = FastAPI(
    title="ProxySmith",
    description="Reverse proxy config generator API",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_GENERATORS: dict[str, type[BaseGenerator]] = {
    "nginx": NginxGenerator,
    "caddy": CaddyGenerator,
    "traefik": TraefikGenerator,
}

# Mount static frontend (built React app) if it exists
_STATIC_DIR = Path(__file__).parent / "frontend" / "dist"
if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="assets")


# --------------------------------------------------------------------------- #
# Request / Response models                                                    #
# --------------------------------------------------------------------------- #


class ValidateRequest(BaseModel):
    toml: str = Field(..., description="Raw TOML string to validate")


class ValidateError(BaseModel):
    field: str
    message: str


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[ValidateError] = []
    service_count: int = 0
    domain: str = ""
    ssl_mode: str = ""


class GenerateRequest(BaseModel):
    toml: str = Field(..., description="Raw TOML content of proxysmith.toml")
    targets: list[str] = Field(
        default=["nginx"],
        description="Which backends to generate: nginx, caddy, traefik",
    )


class GeneratedFileOut(BaseModel):
    filename: str
    content: str
    size: int
    checksum: str


class GenerateResponse(BaseModel):
    files: list[GeneratedFileOut]


class ServiceSummary(BaseModel):
    name: str
    fqdn: str
    host: str
    port: int
    features: list[str]


class ConfigSummaryResponse(BaseModel):
    domain: str
    ssl_mode: str
    email: str | None
    services: list[ServiceSummary]


# --------------------------------------------------------------------------- #
# Endpoints                                                                    #
# --------------------------------------------------------------------------- #


@app.get("/api/health")
async def health() -> dict:
    """Health check."""
    return {"status": "ok", "version": __version__}


@app.post("/api/validate", response_model=ValidateResponse)
async def validate(body: ValidateRequest) -> ValidateResponse:
    """Validate a raw TOML string against the ProxySmith schema.

    Returns a structured list of errors (empty if valid).
    """
    try:
        raw = tomllib.loads(body.toml)
    except tomllib.TOMLDecodeError as exc:
        return ValidateResponse(
            valid=False,
            errors=[ValidateError(field="(toml)", message=str(exc))],
        )

    try:
        cfg = ProxySmithConfig.model_validate(raw)
    except PydanticValidationError as exc:
        errors = [
            ValidateError(
                field=" → ".join(str(p) for p in e["loc"]) if e["loc"] else "(root)",
                message=e["msg"],
            )
            for e in exc.errors()
        ]
        return ValidateResponse(valid=False, errors=errors)

    return ValidateResponse(
        valid=True,
        service_count=len(cfg.services),
        domain=cfg.global_.domain,
        ssl_mode=cfg.global_.ssl.value,
    )


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(body: GenerateRequest) -> GenerateResponse:
    """Generate proxy configs from a raw TOML string.

    Returns the generated file contents as JSON.
    """
    unknown = set(body.targets) - set(_GENERATORS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown targets: {', '.join(sorted(unknown))}. "
                   f"Valid: {', '.join(sorted(_GENERATORS))}",
        )

    try:
        raw = tomllib.loads(body.toml)
        cfg = ProxySmithConfig.model_validate(raw)
    except tomllib.TOMLDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"TOML parse error: {exc}")
    except PydanticValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Config validation failed:\n{_format_pydantic_errors(exc)}",
        )

    resolved = resolve(cfg)
    out_files: list[GeneratedFileOut] = []

    for target in body.targets:
        gen = _GENERATORS[target]()
        for gf in gen.generate(resolved):
            out_files.append(
                GeneratedFileOut(
                    filename=gf.filename,
                    content=gf.content,
                    size=len(gf.content),
                    checksum=hashlib.sha256(gf.content.encode()).hexdigest()[:12],
                )
            )

    return GenerateResponse(files=out_files)


@app.post("/api/generate/download")
async def generate_download(body: GenerateRequest) -> StreamingResponse:
    """Generate configs and return a zip archive for download."""
    resp = await generate(body)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in resp.files:
            zf.writestr(f.filename, f.content)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=proxysmith-configs.zip"},
    )


@app.post("/api/summary", response_model=ConfigSummaryResponse)
async def config_summary(body: ValidateRequest) -> ConfigSummaryResponse:
    """Parse a TOML string and return a structured summary of all services."""
    try:
        raw = tomllib.loads(body.toml)
        cfg = ProxySmithConfig.model_validate(raw)
    except (tomllib.TOMLDecodeError, PydanticValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    resolved = resolve(cfg)
    services = []
    for svc in resolved.services:
        features: list[str] = []
        if svc.websocket:
            features.append("websocket")
        if svc.auth != "none":
            features.append(f"auth:{svc.auth}")
        if svc.rate_limit:
            features.append(f"rate-limit:{svc.rate_limit}")
        if svc.max_upload:
            features.append(f"upload:{svc.max_upload}")
        if svc.cors:
            features.append("cors")
        services.append(
            ServiceSummary(
                name=svc.name,
                fqdn=svc.fqdn,
                host=svc.host,
                port=svc.port,
                features=features,
            )
        )

    return ConfigSummaryResponse(
        domain=resolved.domain,
        ssl_mode=resolved.ssl_mode.value,
        email=resolved.email,
        services=services,
    )


# --------------------------------------------------------------------------- #
# Serve React SPA (catch-all)                                                  #
# --------------------------------------------------------------------------- #

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str, request: Request):
    """Serve index.html for all non-API routes (React SPA)."""
    index = _STATIC_DIR / "index.html"
    if index.exists():
        from fastapi.responses import HTMLResponse
        return HTMLResponse(index.read_text(encoding="utf-8"))
    # Frontend not built yet — show helpful message
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        "ProxySmith web UI not built yet.\n\n"
        "To build the frontend:\n"
        "  cd proxysmith/web/frontend\n"
        "  npm install && npm run build\n\n"
        "API is available at /api/docs",
        status_code=200,
    )
