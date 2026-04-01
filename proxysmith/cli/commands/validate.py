"""proxysmith validate — lint proxysmith.toml."""

from __future__ import annotations

import socket
from pathlib import Path

from rich.console import Console
from rich.table import Table

from proxysmith.core.errors import ConfigError, ValidationError
from proxysmith.core.models import SSLMode
from proxysmith.core.parser import load_config

console = Console()


def run(config_path: Path, check_hosts: bool = False) -> bool:
    """Validate *config_path* and print a human-friendly summary.

    Args:
        config_path: Path to ``proxysmith.toml``.
        check_hosts: If True, attempt TCP connections to every upstream host:port.

    Returns:
        ``True`` if valid (and all hosts reachable when check_hosts=True), ``False`` otherwise.
    """
    console.print(f"\n[bold]Validating[/bold] [cyan]{config_path}[/cyan]\n")

    try:
        cfg = load_config(config_path)
    except (ConfigError, ValidationError) as exc:
        console.print(f"[bold red]✗ Validation failed[/bold red]\n{exc}")
        return False

    g = cfg.global_
    table = Table(title="Global Config", show_header=True, header_style="bold magenta")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value")
    table.add_row("domain", g.domain)
    table.add_row("ssl", g.ssl.value)
    table.add_row("email", g.email or "[dim]—[/dim]")
    console.print(table)

    svc_table = Table(title="Services", show_header=True, header_style="bold magenta")
    svc_table.add_column("#", style="dim", width=3)
    svc_table.add_column("name", style="cyan")
    svc_table.add_column("subdomain → fqdn")
    svc_table.add_column("upstream")
    svc_table.add_column("features", style="dim")
    if check_hosts:
        svc_table.add_column("reachable")

    all_reachable = True
    for i, svc in enumerate(cfg.services, 1):
        fqdn = f"{svc.subdomain}.{g.domain}"
        features: list[str] = []
        if svc.websocket:
            features.append("ws")
        if svc.auth.value != "none":
            features.append(f"auth:{svc.auth.value}")
        if svc.rate_limit:
            features.append(f"rl:{svc.rate_limit}")
        if svc.max_upload:
            features.append(f"upload:{svc.max_upload}")
        if svc.cors:
            features.append("cors")

        row = [
            str(i),
            svc.name,
            f"{svc.subdomain} → {fqdn}",
            f"{svc.host}:{svc.port}",
            ", ".join(features) or "—",
        ]

        if check_hosts:
            reachable, msg = _tcp_check(svc.host, svc.port)
            if not reachable:
                all_reachable = False
            row.append("[green]✓[/green]" if reachable else f"[red]✗[/red] {msg}")

        svc_table.add_row(*row)

    console.print(svc_table)

    # Warn if auto SSL and no email (belt-and-suspenders — model validator also catches this)
    if g.ssl == SSLMode.auto and not g.email:
        console.print("[yellow]⚠[/yellow]  ssl=auto but no email set — Let's Encrypt requires one")

    if check_hosts and not all_reachable:
        console.print(
            "\n[yellow]⚠  Some upstreams are unreachable.[/yellow] "
            "Configs will still generate; ensure hosts are up before deploying.\n"
        )
        return False

    console.print(
        f"\n[bold green]✓ Valid[/bold green] — "
        f"{len(cfg.services)} service(s) defined\n"
    )
    return True


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    """Attempt a TCP connection to *host:port*.

    Returns:
        A ``(success, error_message)`` tuple.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, ""
    except OSError as exc:
        return False, str(exc)
