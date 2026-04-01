"""ProxySmith CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from proxysmith import __version__

app = typer.Typer(
    name="proxysmith",
    help="Reverse proxy config generator for homelabbers and self-hosters.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()

_DEFAULT_CONFIG = Path("proxysmith.toml")
_DEFAULT_OUTPUT = Path("output")

# --------------------------------------------------------------------------- #
# Version                                                                      #
# --------------------------------------------------------------------------- #


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold]ProxySmith[/bold] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-V",
            help="Print version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """[bold cyan]ProxySmith[/bold cyan] — generate Nginx, Caddy, or Traefik configs from a single TOML file."""


# --------------------------------------------------------------------------- #
# init                                                                         #
# --------------------------------------------------------------------------- #


@app.command()
def init(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Destination path for the generated proxysmith.toml.",
            show_default=True,
        ),
    ] = _DEFAULT_CONFIG,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompts."),
    ] = False,
) -> None:
    """Scaffold a [bold]proxysmith.toml[/bold] with example services."""
    from proxysmith.cli.commands.init import run

    run(output=output, yes=yes)


# --------------------------------------------------------------------------- #
# validate                                                                     #
# --------------------------------------------------------------------------- #


@app.command()
def validate(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to proxysmith.toml.",
            show_default=True,
        ),
    ] = _DEFAULT_CONFIG,
    check_hosts: Annotated[
        bool,
        typer.Option(
            "--check-hosts",
            help="Attempt TCP connections to every upstream host:port.",
        ),
    ] = False,
) -> None:
    """Lint [bold]proxysmith.toml[/bold] — check schema and detect conflicts."""
    from proxysmith.cli.commands.validate import run

    ok = run(config_path=config, check_hosts=check_hosts)
    if not ok:
        raise typer.Exit(1)


# --------------------------------------------------------------------------- #
# generate                                                                     #
# --------------------------------------------------------------------------- #

_TargetArg = Annotated[
    str,
    typer.Option(
        "--target",
        "-t",
        help="Proxy backend to generate for. One of: nginx, caddy, traefik, all.",
        show_default=True,
    ),
]


@app.command()
def generate(
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to proxysmith.toml.", show_default=True),
    ] = _DEFAULT_CONFIG,
    target: _TargetArg = "nginx",
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Output directory.", show_default=True),
    ] = _DEFAULT_OUTPUT,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print configs to stdout without writing files."),
    ] = False,
) -> None:
    """Generate reverse proxy configuration files."""
    _validate_target(target)
    from proxysmith.cli.commands.generate import run

    ok = run(config_path=config, target=target, output_dir=out, dry_run=dry_run)
    if not ok:
        raise typer.Exit(1)


# --------------------------------------------------------------------------- #
# diff                                                                         #
# --------------------------------------------------------------------------- #


@app.command()
def diff(
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to proxysmith.toml.", show_default=True),
    ] = _DEFAULT_CONFIG,
    target: _TargetArg = "all",
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Output directory to compare against.", show_default=True),
    ] = _DEFAULT_OUTPUT,
) -> None:
    """Show what would change if you re-ran [bold]generate[/bold] now."""
    _validate_target(target)
    from proxysmith.cli.commands.diff import run

    ok = run(config_path=config, target=target, output_dir=out)
    if not ok:
        raise typer.Exit(1)


# --------------------------------------------------------------------------- #
# doctor                                                                       #
# --------------------------------------------------------------------------- #


@app.command()
def doctor(
    out: Annotated[
        Path,
        typer.Option(
            "--out", "-o", help="Output directory with generated configs.", show_default=True
        ),
    ] = _DEFAULT_OUTPUT,
) -> None:
    """Check installed proxy tools and validate generated configs."""
    from proxysmith.cli.commands.doctor import run

    run(output_dir=out)


# --------------------------------------------------------------------------- #
# auth (subcommand group)                                                      #
# --------------------------------------------------------------------------- #


@app.command("auth")
def auth_command(
    ctx: typer.Context,
    subcommand: Annotated[
        Optional[str],
        typer.Argument(help="Subcommand: list | generate | forward"),
    ] = None,
) -> None:
    """Authentication scaffolding — [dim]use `proxysmith auth --help` for subcommands[/dim].

    \b
    proxysmith auth list                   Show auth mode for all services
    proxysmith auth generate <user>        Generate htpasswd entry
    proxysmith auth forward [provider]     Show forward-auth snippets
    """
    # This thin wrapper lets us register `auth` as a Typer sub-app below.
    # The real dispatch happens via the imported sub-app.
    pass


# Mount the auth sub-app so `proxysmith auth list|generate|forward` work
from proxysmith.cli.commands.auth import app as _auth_app  # noqa: E402

app.add_typer(_auth_app, name="auth", help="Authentication scaffolding.")

# Remove the stub command we registered above (the typer add_typer takes over)
# Typer registers the sub-app under the same name — the stub is harmless but
# we override it cleanly by re-registering the sub-app after the stub.


# --------------------------------------------------------------------------- #
# serve                                                                        #
# --------------------------------------------------------------------------- #


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option("--host", help="Bind host.", show_default=True),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Bind port.", show_default=True),
    ] = 7771,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Enable auto-reload (development)."),
    ] = False,
    open_browser: Annotated[
        bool,
        typer.Option("--open", help="Open browser automatically."),
    ] = True,
) -> None:
    """Start the [bold]ProxySmith web UI[/bold] on http://localhost:7771."""
    try:
        import uvicorn
    except ImportError:
        console.print(
            "[bold red]✗[/bold red] uvicorn not installed. "
            "Install web extras: [cyan]pip install proxysmith[web][/cyan]"
        )
        raise typer.Exit(1)

    url = f"http://{host}:{port}"
    console.print(
        f"\n[bold cyan]ProxySmith Web UI[/bold cyan]\n"
        f"  [dim]→[/dim] {url}\n"
        f"  [dim]→[/dim] {url}/api/docs  (API explorer)\n"
    )

    if open_browser and not reload:
        import threading
        import time
        import webbrowser

        def _open():
            time.sleep(1.2)
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(
        "proxysmith.web.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="warning",
    )


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

_VALID_TARGETS = {"nginx", "caddy", "traefik", "all"}


def _validate_target(target: str) -> None:
    if target not in _VALID_TARGETS:
        console.print(
            f"[bold red]✗[/bold red] Unknown target '{target}'. "
            f"Must be one of: {', '.join(sorted(_VALID_TARGETS))}"
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
