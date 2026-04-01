"""proxysmith generate — produce reverse proxy configs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from proxysmith.core.errors import ConfigError, GeneratorError, ValidationError
from proxysmith.core.parser import load_config
from proxysmith.core.resolver import resolve
from proxysmith.generators import CaddyGenerator, NginxGenerator, TraefikGenerator
from proxysmith.generators.base import BaseGenerator

console = Console()

_GENERATORS: dict[str, type[BaseGenerator]] = {
    "nginx": NginxGenerator,
    "caddy": CaddyGenerator,
    "traefik": TraefikGenerator,
}

# State file used by `proxysmith diff`
_STATE_FILENAME = ".proxysmith_state.json"


def run(
    config_path: Path,
    target: str,
    output_dir: Path,
    dry_run: bool = False,
) -> bool:
    """Generate reverse proxy configs from *config_path*.

    Args:
        config_path: Path to ``proxysmith.toml``.
        target: One of ``nginx``, ``caddy``, ``traefik``, or ``all``.
        output_dir: Directory to write generated files into.
        dry_run: If True, print output without writing files.

    Returns:
        ``True`` on success.
    """
    console.print(
        f"\n[bold]ProxySmith Generate[/bold] — target=[cyan]{target}[/cyan]"
        f"{'  [yellow](dry-run)[/yellow]' if dry_run else ''}\n"
    )

    # --- Load & validate ---
    try:
        cfg = load_config(config_path)
    except (ConfigError, ValidationError) as exc:
        console.print(f"[bold red]✗[/bold red] {exc}")
        return False

    resolved = resolve(cfg)
    targets = list(_GENERATORS.keys()) if target == "all" else [target]

    results: list[tuple[str, str, int]] = []  # (filename, preview_head, byte_count)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        for t in targets:
            task = progress.add_task(f"Generating [cyan]{t}[/cyan] config…", total=None)
            try:
                gen = _GENERATORS[t]()
                files = gen.generate(resolved)
            except GeneratorError as exc:
                console.print(f"[bold red]✗[/bold red] Generator error ({t}): {exc}")
                return False

            for gf in files:
                if not dry_run:
                    dest = gf.write(output_dir)
                    results.append((str(dest.relative_to(output_dir)), gf.content, len(gf.content)))
                else:
                    results.append((gf.filename, gf.content, len(gf.content)))
            progress.remove_task(task)

    # --- Output ---
    if dry_run:
        for filename, content, _ in results:
            console.rule(f"[bold cyan]{filename}[/bold cyan]")
            console.print(content)
        console.rule()
        return True

    # --- Summary table ---
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right", style="dim")
    for filename, _, size in results:
        table.add_row(filename, f"{size:,} bytes")
    console.print(table)

    # --- Persist state for `diff` ---
    state = {
        filename: hashlib.sha256(content.encode()).hexdigest()
        for filename, content, _ in results
    }
    state_path = output_dir / _STATE_FILENAME
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    console.print(
        f"\n[bold green]✓[/bold green] Generated {len(results)} file(s) "
        f"→ [cyan]{output_dir}[/cyan]\n"
    )
    return True
