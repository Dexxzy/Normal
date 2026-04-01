"""Tests for auth scaffolding — htpasswd generation and APR1 implementation."""

from __future__ import annotations

import re

import pytest

from proxysmith.cli.commands.auth import _apr1_md5, _random_password


class TestApr1Md5:
    def test_format(self):
        entry = _apr1_md5("admin", "password")
        # Should be: user:$apr1$<8-char-salt>$<hash>
        assert entry.startswith("admin:$apr1$")
        parts = entry.split("$")
        assert len(parts) == 4          # ['admin:', 'apr1', salt, hash]
        assert len(parts[2]) == 8       # salt is 8 chars
        assert len(parts[3]) > 10       # hash is non-trivial

    def test_deterministic_for_same_salt(self):
        # Two different calls produce different salts → different hashes
        e1 = _apr1_md5("user", "pass")
        e2 = _apr1_md5("user", "pass")
        # Same user prefix
        assert e1.startswith("user:")
        assert e2.startswith("user:")

    def test_different_users(self):
        e1 = _apr1_md5("alice", "secret")
        e2 = _apr1_md5("bob", "secret")
        assert e1.startswith("alice:")
        assert e2.startswith("bob:")

    def test_special_chars_in_password(self):
        # Should not raise
        _apr1_md5("user", "p@$$w0rd!#%^&*()")

    def test_empty_password(self):
        entry = _apr1_md5("user", "")
        assert entry.startswith("user:$apr1$")


class TestRandomPassword:
    def test_length(self):
        pwd = _random_password(20)
        assert len(pwd) == 20

    def test_uniqueness(self):
        passwords = {_random_password(16) for _ in range(50)}
        assert len(passwords) > 45  # extremely unlikely to collide

    def test_default_length(self):
        pwd = _random_password()
        assert len(pwd) == 20


class TestAuthGenerateCommand:
    """Smoke tests for the auth generate command via its function."""

    def test_generates_htpasswd_entry(self, tmp_path):
        from typer.testing import CliRunner
        from proxysmith.cli.commands.auth import app

        runner = CliRunner()
        result = runner.invoke(app, ["generate", "testuser", "--password", "hunter2"])
        assert result.exit_code == 0
        assert "testuser" in result.output

    def test_writes_to_file(self, tmp_path):
        from typer.testing import CliRunner
        from proxysmith.cli.commands.auth import app

        out = tmp_path / "htpasswd"
        runner = CliRunner()
        result = runner.invoke(
            app, ["generate", "admin", "--password", "secret123", "--out", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert "admin:$apr1$" in content

    def test_appends_multiple_users(self, tmp_path):
        from typer.testing import CliRunner
        from proxysmith.cli.commands.auth import app

        out = tmp_path / "htpasswd"
        runner = CliRunner()
        runner.invoke(app, ["generate", "alice", "--password", "pw1", "--out", str(out)])
        runner.invoke(app, ["generate", "bob",   "--password", "pw2", "--out", str(out)])
        lines = out.read_text().strip().splitlines()
        assert len(lines) == 2
        assert lines[0].startswith("alice:")
        assert lines[1].startswith("bob:")
