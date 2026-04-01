"""proxysmith doctor — check installed proxies and validate generated configs."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _run(cmd: list[str]) -> tuple[int, str]:
    """Run a command and return (returncode, combined stdout+stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return 127, "command not found"
    except subprocess.TimeoutExpired:
        return 1, "timed out"


def run(output_dir: Path) -> None:
    """Run diagnostics on installed proxy tools and generated configs.

    Args:
        output_dir: Directory containing generated ProxySmith configs.
    """
    console.print("\n[bold]ProxySmith Doctor[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Detail", style="dim")

    # --- Nginx ---
    nginx_bin = _which("nginx")
    if nginx_bin:
        code, out = _run(["nginx", "-v"])
        version = out.split("\n")[0] if out else "unknown"
        table.add_row("nginx installed", "[green]✓[/green]", f"{nginx_bin} — {version}")

        nginx_conf = output_dir / "nginx" / "proxysmith.conf"
        if nginx_conf.exists():
            code, out = _run(["nginx", "-t", "-c", str(nginx_conf.resolve())])
            if code == 0:
                table.add_row("nginx config test", "[green]✓[/green]", str(nginx_conf))
            else:
                table.add_row("nginx config test", "[red]✗[/red]", out[:120])
        else:
            table.add_row("nginx config", "[dim]—[/dim]", "not generated yet")
    else:
        table.add_row("nginx installed", "[dim]not found[/dim]", "")

    # --- Caddy ---
    caddy_bin = _which("caddy")
    if caddy_bin:
        code, out = _run(["caddy", "version"])
        version = out.split("\n")[0] if out else "unknown"
        table.add_row("caddy installed", "[green]✓[/green]", f"{caddy_bin} — {version}")

        caddyfile = output_dir / "caddy" / "Caddyfile"
        if caddyfile.exists():
            code, out = _run(["caddy", "validate", "--config", str(caddyfile)])
            if code == 0:
                table.add_row("caddy config test", "[green]✓[/green]", str(caddyfile))
            else:
                table.add_row("caddy config test", "[red]✗[/red]", out[:120])
        else:
            table.add_row("caddy config", "[dim]—[/dim]", "not generated yet")
    else:
        table.add_row("caddy installed", "[dim]not found[/dim]", "")

    # --- Traefik ---
    traefik_bin = _which("traefik")
    if traefik_bin:
        code, out = _run(["traefik", "version"])
        version = out.split("\n")[0] if out else "unknown"
        table.add_row("traefik installed", "[green]✓[/green]", f"{traefik_bin} — {version}")
    else:
        table.add_row("traefik installed", "[dim]not found[/dim]", "")

    # --- Docker ---
    docker_bin = _which("docker")
    if docker_bin:
        code, out = _run(["docker", "version", "--format", "{{.Server.Version}}"])
        table.add_row(
            "docker installed",
            "[green]✓[/green]" if code == 0 else "[yellow]daemon offline[/yellow]",
            out[:60] if out else "",
        )
    else:
        table.add_row("docker installed", "[dim]not found[/dim]", "")

    console.print(table)
    console.print()
