from pathlib import Path

import duckdb
from typer.testing import CliRunner

from gridbridge.cli import app
from gridbridge.pipeline.run import run_demo


def test_demo_reconciles_all_sources_and_is_idempotent(tmp_path: Path) -> None:
    """The clean reviewer journey must account for every row and survive a replay."""
    first = run_demo(tmp_path, Path("config/pipeline.yml"), seed=42)
    second = run_demo(tmp_path, Path("config/pipeline.yml"), seed=42)

    assert first.reconciliation_balanced
    assert first.status == "degraded"
    assert first.total_landed > 288
    assert first.total_quarantined >= 3
    assert first.total_inserted > 0
    assert first.dbt_success
    assert first.report_path.exists()
    assert second.total_inserted == 0
    assert second.total_unchanged == second.total_accepted
    with duckdb.connect(str(first.warehouse_path), read_only=True) as connection:
        assert connection.execute("select count(*) from ingestion_runs").fetchone() == (2,)
        assert (
            connection.execute("select count(*) from fct_flex_interval_candidates").fetchone()[0]
            > 0
        )


def test_cli_demo_prints_evidence_paths(tmp_path: Path) -> None:
    """A reviewer should get useful next steps without inspecting implementation code."""
    result = CliRunner().invoke(
        app,
        [
            "demo",
            "--workspace",
            str(tmp_path),
            "--config",
            "config/pipeline.yml",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "GridBridge onboarding" in result.output
    assert "reconciliation: balanced" in result.output
    assert "gridbridge.duckdb" in result.output
    assert "run-summary.json" in result.output
