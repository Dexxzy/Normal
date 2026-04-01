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
) -> None:
    """Lint [bold]proxysmith.toml[/bold] — check schema and detect conflicts."""
    from proxysmith.cli.commands.validate import run

    ok = run(config_path=config)
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
