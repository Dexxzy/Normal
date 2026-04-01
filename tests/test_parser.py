"""Tests for the TOML parser and Pydantic validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from proxysmith.core.errors import ConfigError, ValidationError
from proxysmith.core.models import AuthMode, SSLMode
from proxysmith.core.parser import load_config

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadConfig:
    def test_full_config_parses(self):
        cfg = load_config(FIXTURES / "full.toml")
        assert cfg.global_.domain == "home.example.com"
        assert cfg.global_.ssl == SSLMode.auto
        assert cfg.global_.email == "admin@example.com"
        assert len(cfg.services) == 4

    def test_minimal_config_parses(self):
        cfg = load_config(FIXTURES / "minimal.toml")
        assert cfg.global_.ssl == SSLMode.none
        assert cfg.global_.email is None
        assert len(cfg.services) == 1

    def test_service_fields(self):
        cfg = load_config(FIXTURES / "full.toml")
        plex = next(s for s in cfg.services if s.name == "plex")
        assert plex.host == "192.168.1.50"
        assert plex.port == 32400
        assert plex.subdomain == "plex"
        assert plex.websocket is True
        assert plex.headers == {"X-Plex-Client-Identifier": "proxysmith"}

        immich = next(s for s in cfg.services if s.name == "immich")
        assert immich.max_upload == "10G"

        ollama = next(s for s in cfg.services if s.name == "ollama")
        assert ollama.auth == AuthMode.basic
        assert ollama.rate_limit == "60/min"

    def test_missing_file_raises_config_error(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path / "nonexistent.toml")

    def test_invalid_toml_raises_config_error(self, tmp_path):
        bad = tmp_path / "bad.toml"
        bad.write_text("not = [valid toml", encoding="utf-8")
        with pytest.raises(ConfigError, match="TOML parse error"):
            load_config(bad)

    def test_duplicate_subdomain_raises_validation_error(self):
        with pytest.raises(ValidationError, match="Duplicate subdomain"):
            load_config(FIXTURES / "bad_duplicate_subdomain.toml")

    def test_auto_ssl_requires_email(self):
        with pytest.raises(ValidationError, match="email is required"):
            load_config(FIXTURES / "bad_missing_email.toml")

    def test_invalid_service_name_raises(self, tmp_path):
        bad = tmp_path / "bad_name.toml"
        bad.write_text(
            '[global]\ndomain="x.com"\nssl="none"\n'
            '[[service]]\nname="BAD NAME"\nhost="1.2.3.4"\nport=80\nsubdomain="ok"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValidationError):
            load_config(bad)

    def test_invalid_port_raises(self, tmp_path):
        bad = tmp_path / "bad_port.toml"
        bad.write_text(
            '[global]\ndomain="x.com"\nssl="none"\n'
            '[[service]]\nname="app"\nhost="1.2.3.4"\nport=99999\nsubdomain="app"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValidationError):
            load_config(bad)

    def test_invalid_rate_limit_raises(self, tmp_path):
        bad = tmp_path / "bad_rl.toml"
        bad.write_text(
            '[global]\ndomain="x.com"\nssl="none"\n'
            '[[service]]\nname="app"\nhost="1.2.3.4"\nport=80\nsubdomain="app"\n'
            'rate_limit="fast"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValidationError):
            load_config(bad)
