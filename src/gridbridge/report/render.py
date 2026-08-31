"""Render pipeline evidence as portable, dependency-free HTML."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
    from gridbridge.pipeline.run import PipelineSummary


def render_report(summary: PipelineSummary, output_path: Path) -> Path:
    """Render one complete onboarding summary without external assets or tracking."""

    template_dir = Path(__file__).parent / "templates"
    environment = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template("report.html.j2")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        template.render(
            summary=summary,
            acceptance_rate=(summary.total_accepted / summary.total_landed * 100)
            if summary.total_landed
            else 0.0,
            duration_seconds=(summary.completed_at_utc - summary.started_at_utc).total_seconds(),
            warehouse_name=summary.warehouse_path.name,
        ),
        encoding="utf-8",
    )
    return output_path
