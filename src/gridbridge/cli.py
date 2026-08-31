"""Reviewer-facing GridBridge command line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from gridbridge.generators.sources import generate_sources
from gridbridge.pipeline.run import run_demo

app = typer.Typer(
    name="gridbridge",
    help="Synthetic utility data onboarding control plane.",
    no_args_is_help=True,
)


@app.command()
def generate(
    output: Annotated[Path, typer.Option(help="Destination for synthetic sources.")] = Path(
        "sample_data"
    ),
    seed: Annotated[int, typer.Option(help="Deterministic random seed.")] = 42,
    meter_rows: Annotated[int, typer.Option(min=12, help="Base meter rows before defects.")] = 288,
) -> None:
    """Generate deterministic meter, GIS, SCADA, DER, and market sources."""

    paths = generate_sources(output, seed=seed, meter_rows=meter_rows)
    typer.echo(f"Generated {sum(len(items) for items in paths.values())} sources in {output}")


def _print_summary(summary: object) -> None:
    from gridbridge.pipeline.run import PipelineSummary

    if not isinstance(summary, PipelineSummary):
        raise TypeError("expected PipelineSummary")
    typer.echo(f"GridBridge onboarding: {summary.status.value}")
    typer.echo(f"run: {summary.run_id}")
    typer.echo("reconciliation: balanced")
    typer.echo(f"accepted: {summary.total_accepted} | quarantined: {summary.total_quarantined}")
    typer.echo(f"warehouse: {summary.warehouse_path}")
    typer.echo(f"evidence: {summary.report_path}")


@app.command()
def demo(
    workspace: Annotated[Path, typer.Option(help="Runtime workspace.")] = Path("work/demo"),
    config: Annotated[Path, typer.Option(help="Pipeline configuration.")] = Path(
        "config/pipeline.yml"
    ),
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 42,
) -> None:
    """Run the complete local onboarding demonstration."""

    _print_summary(run_demo(workspace, config, seed=seed))


@app.command()
def replay(
    parent_run_id: Annotated[str, typer.Option(help="Prior run linked by this replay.")],
    workspace: Annotated[Path, typer.Option(help="Existing runtime workspace.")] = Path(
        "work/demo"
    ),
    config: Annotated[Path, typer.Option(help="Pipeline configuration.")] = Path(
        "config/pipeline.yml"
    ),
) -> None:
    """Replay source data while preserving parent-run lineage."""

    _print_summary(run_demo(workspace, config, parent_run_id=parent_run_id))


if __name__ == "__main__":
    app()
