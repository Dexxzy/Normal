"""proxysmith diff — show what changed since last generation."""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

from proxysmith.core.errors import ConfigError, ValidationError
from proxysmith.core.parser import load_config
from proxysmith.core.resolver import resolve
from proxysmith.generators import CaddyGenerator, NginxGenerator, TraefikGenerator
from proxysmith.generators.base import BaseGenerator

console = Console()

_STATE_FILENAME = ".proxysmith_state.json"

_GENERATORS: dict[str, type[BaseGenerator]] = {
    "nginx": NginxGenerator,
    "caddy": CaddyGenerator,
    "traefik": TraefikGenerator,
}


def run(
    config_path: Path,
    target: str,
    output_dir: Path,
) -> bool:
    """Compare the current generation output against the last saved state.

    Args:
        config_path: Path to ``proxysmith.toml``.
        target: One of ``nginx``, ``caddy``, ``traefik``, or ``all``.
        output_dir: Directory that contains previously generated files.

    Returns:
        ``True`` if the diff ran successfully (even if no changes).
    """
    console.print(f"\n[bold]ProxySmith Diff[/bold] — target=[cyan]{target}[/cyan]\n")

    state_path = output_dir / _STATE_FILENAME
    if not state_path.exists():
        console.print(
            "[yellow]⚠[/yellow]  No previous state found. "
            "Run [bold]proxysmith generate[/bold] first."
        )
        return False

    try:
        cfg = load_config(config_path)
    except (ConfigError, ValidationError) as exc:
        console.print(f"[bold red]✗[/bold red] {exc}")
        return False

    resolved = resolve(cfg)
    targets = list(_GENERATORS.keys()) if target == "all" else [target]

    old_state: dict[str, str] = json.loads(state_path.read_text(encoding="utf-8"))
    changed = False

    for t in targets:
        gen = _GENERATORS[t]()
        files = gen.generate(resolved)

        for gf in files:
            new_hash = hashlib.sha256(gf.content.encode()).hexdigest()
            old_hash = old_state.get(gf.filename)

            if old_hash is None:
                console.print(f"[green]+ NEW[/green]  {gf.filename}")
                changed = True
                continue

            if old_hash == new_hash:
                console.print(f"[dim]  unchanged  {gf.filename}[/dim]")
                continue

            # Generate a textual diff against on-disk file (if present)
            changed = True
            disk_path = output_dir / gf.filename
            if disk_path.exists():
                old_lines = disk_path.read_text(encoding="utf-8").splitlines(keepends=True)
            else:
                old_lines = []

            new_lines = gf.content.splitlines(keepends=True)
            diff = list(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"a/{gf.filename}",
                    tofile=f"b/{gf.filename}",
                    lineterm="",
                )
            )
            if diff:
                console.rule(f"[cyan]{gf.filename}[/cyan]")
                syntax = Syntax("".join(diff), "diff", theme="ansi_dark", line_numbers=False)
                console.print(syntax)

    if not changed:
        console.print("\n[bold green]✓ No changes[/bold green] since last generation.\n")
    else:
        console.print(
            "\n[yellow]Changes detected.[/yellow] "
            "Run [bold]proxysmith generate[/bold] to apply.\n"
        )
    return True
