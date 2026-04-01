"""Tests for the FastAPI backend."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from proxysmith.web.api import app

client = TestClient(app)

VALID_TOML = """\
[global]
domain = "home.example.com"
ssl    = "auto"
email  = "admin@example.com"

[[service]]
name      = "plex"
host      = "192.168.1.50"
port      = 32400
subdomain = "plex"
websocket = true

[[service]]
name      = "dash"
host      = "192.168.1.50"
port      = 3000
subdomain = "dash"
"""

INVALID_TOML = """\
[global]
domain = "home.example.com"
ssl    = "auto"
# missing email

[[service]]
name      = "app"
host      = "1.2.3.4"
port      = 8080
subdomain = "app"
"""

BROKEN_TOML = "this is not = [valid toml"


class TestHealth:
    def test_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestValidate:
    def test_valid_config(self):
        r = client.post("/api/validate", json={"toml": VALID_TOML})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True
        assert data["service_count"] == 2
        assert data["domain"] == "home.example.com"
        assert data["ssl_mode"] == "auto"
        assert data["errors"] == []

    def test_invalid_config_returns_errors(self):
        r = client.post("/api/validate", json={"toml": INVALID_TOML})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_broken_toml_returns_error(self):
        r = client.post("/api/validate", json={"toml": BROKEN_TOML})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False
        assert any("toml" in e["field"].lower() for e in data["errors"])


class TestGenerate:
    def test_nginx_generation(self):
        r = client.post("/api/generate", json={"toml": VALID_TOML, "targets": ["nginx"]})
        assert r.status_code == 200
        data = r.json()
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "nginx/proxysmith.conf"
        assert "upstream proxysmith_plex" in data["files"][0]["content"]

    def test_caddy_generation(self):
        r = client.post("/api/generate", json={"toml": VALID_TOML, "targets": ["caddy"]})
        assert r.status_code == 200
        data = r.json()
        assert data["files"][0]["filename"] == "caddy/Caddyfile"

    def test_traefik_generation(self):
        r = client.post("/api/generate", json={"toml": VALID_TOML, "targets": ["traefik"]})
        assert r.status_code == 200
        data = r.json()
        assert len(data["files"]) == 2

    def test_all_targets(self):
        r = client.post(
            "/api/generate",
            json={"toml": VALID_TOML, "targets": ["nginx", "caddy", "traefik"]},
        )
        assert r.status_code == 200
        data = r.json()
        # nginx(1) + caddy(1) + traefik(2) = 4 files
        assert len(data["files"]) == 4

    def test_unknown_target_422(self):
        r = client.post("/api/generate", json={"toml": VALID_TOML, "targets": ["apache"]})
        assert r.status_code == 422

    def test_invalid_toml_422(self):
        r = client.post("/api/generate", json={"toml": BROKEN_TOML, "targets": ["nginx"]})
        assert r.status_code == 422

    def test_file_has_checksum(self):
        r = client.post("/api/generate", json={"toml": VALID_TOML, "targets": ["nginx"]})
        f = r.json()["files"][0]
        assert len(f["checksum"]) == 12
        assert f["size"] > 0


class TestDownload:
    def test_returns_zip(self):
        r = client.post(
            "/api/generate/download",
            json={"toml": VALID_TOML, "targets": ["nginx", "caddy"]},
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        # ZIP magic bytes
        assert r.content[:2] == b"PK"


class TestSummary:
    def test_summary(self):
        r = client.post("/api/summary", json={"toml": VALID_TOML})
        assert r.status_code == 200
        data = r.json()
        assert data["domain"] == "home.example.com"
        assert len(data["services"]) == 2
        fqdns = {s["fqdn"] for s in data["services"]}
        assert "plex.home.example.com" in fqdns
        assert "dash.home.example.com" in fqdns

    def test_websocket_in_features(self):
        r = client.post("/api/summary", json={"toml": VALID_TOML})
        plex = next(s for s in r.json()["services"] if s["name"] == "plex")
        assert "websocket" in plex["features"]

    def test_invalid_toml_422(self):
        r = client.post("/api/summary", json={"toml": BROKEN_TOML})
        assert r.status_code == 422
