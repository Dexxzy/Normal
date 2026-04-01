"""proxysmith init — scaffold a proxysmith.toml with examples."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()

_EXAMPLE_TOML = '''\
[global]
domain = "{domain}"
ssl    = "auto"
email  = "{email}"

# Each [[service]] block defines one reverse-proxied app.
# Run `proxysmith generate --target nginx` to produce configs.

[[service]]
name      = "homepage"
host      = "192.168.1.50"
port      = 3000
subdomain = "dash"

[[service]]
name      = "plex"
host      = "192.168.1.50"
port      = 32400
subdomain = "plex"
websocket = true
headers   = {{ X-Plex-Client-Identifier = "proxysmith" }}

[[service]]
name       = "immich"
host       = "192.168.1.50"
port       = 2283
subdomain  = "photos"
max_upload = "10G"

# [[service]]
# name       = "ollama"
# host       = "192.168.1.50"
# port       = 11434
# subdomain  = "llm"
# auth       = "basic"
# rate_limit = "60/min"
'''


def run(
    output: Path = Path("proxysmith.toml"),
    yes: bool = False,
) -> None:
    """Interactively scaffold a proxysmith.toml file.

    Args:
        output: Destination path (default: ./proxysmith.toml).
        yes: Skip confirmation prompts.
    """
    console.print("\n[bold cyan]ProxySmith Init[/bold cyan] — create a starter config\n")

    if output.exists() and not yes:
        overwrite = Confirm.ask(
            f"[yellow]{output}[/yellow] already exists. Overwrite?",
            default=False,
        )
        if not overwrite:
            console.print("[dim]Aborted.[/dim]")
            raise typer.Exit(0)

    domain = Prompt.ask(
        "Base domain",
        default="home.example.com",
        console=console,
    )
    email = Prompt.ask(
        "ACME/Let's Encrypt email",
        default="admin@example.com",
        console=console,
    )

    content = _EXAMPLE_TOML.format(domain=domain, email=email)
    output.write_text(content, encoding="utf-8")

    console.print(f"\n[green]✓[/green] Created [bold]{output}[/bold]")
    console.print("\nNext steps:")
    console.print("  1. Edit [bold]proxysmith.toml[/bold] — add your services")
    console.print("  2. [bold]proxysmith validate[/bold] — check for errors")
    console.print(
        "  3. [bold]proxysmith generate --target nginx --out ./output[/bold] — generate configs\n"
    )
