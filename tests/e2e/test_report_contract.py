from datetime import UTC
from pathlib import Path

from gridbridge.pipeline.run import run_demo


def test_demo_emits_html_report_and_machine_readable_summary(tmp_path: Path) -> None:
    """Human and machine evidence must be produced by the same successful run."""
    summary = run_demo(tmp_path, Path("config/pipeline.yml"))

    assert summary.report_path.suffix == ".html"
    assert summary.report_path.exists()
    assert summary.report_path.with_name("run-summary.json").exists()
    assert summary.run_id in summary.report_path.read_text(encoding="utf-8")
    assert all(item.interval_start_utc.tzinfo is UTC for item in summary.flex_recommendations)
