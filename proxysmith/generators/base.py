"""Abstract base class for all ProxySmith config generators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from proxysmith.core.errors import TemplateError
from proxysmith.core.resolver import ResolvedConfig

# Locate the templates/ directory relative to this file's package root
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class GeneratedFile:
    """A single output file produced by a generator."""

    def __init__(self, filename: str, content: str) -> None:
        self.filename = filename
        self.content = content

    def write(self, output_dir: Path) -> Path:
        """Write content to *output_dir/filename* and return the path."""
        dest = output_dir / self.filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(self.content, encoding="utf-8")
        return dest

    def __repr__(self) -> str:
        return f"GeneratedFile({self.filename!r}, {len(self.content)} chars)"


class BaseGenerator(ABC):
    """Common interface for all proxy config generators."""

    #: Subdirectory under templates/ for this generator's templates.
    template_subdir: str

    def __init__(self) -> None:
        templates_path = _TEMPLATES_DIR / self.template_subdir
        self._env = Environment(
            loader=FileSystemLoader([str(_TEMPLATES_DIR), str(templates_path)]),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def _render(self, template_name: str, **ctx) -> str:
        """Render *template_name* with the given context variables.

        Args:
            template_name: Template path relative to the templates/ root.
            **ctx: Variables passed into the Jinja2 template.

        Returns:
            Rendered string.

        Raises:
            TemplateError: On any Jinja2 rendering failure.
        """
        try:
            tmpl = self._env.get_template(template_name)
            return tmpl.render(**ctx)
        except Exception as exc:
            raise TemplateError(f"Failed to render template '{template_name}': {exc}") from exc

    @abstractmethod
    def generate(self, config: ResolvedConfig) -> list[GeneratedFile]:
        """Generate one or more config files from a resolved config.

        Args:
            config: Enriched, validated config from the resolver.

        Returns:
            A list of :class:`GeneratedFile` objects.
        """
