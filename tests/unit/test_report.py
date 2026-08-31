from datetime import UTC, datetime
from pathlib import Path

from gridbridge.flex.recommend import FlexRecommendation
from gridbridge.models import DatasetProfile, ReconciliationResult, RunStatus, SourceName
from gridbridge.pipeline.run import PipelineSummary, SourceRunSummary
from gridbridge.report.render import render_report
from gridbridge.topology.validate import TopologyIssue, TopologyResult


def _summary(tmp_path: Path) -> PipelineSummary:
    now = datetime(2026, 8, 31, 1, 0, tzinfo=UTC)
    source = SourceRunSummary(
        source=SourceName.METER,
        landed=10,
        accepted=9,
        quarantined=1,
        inserted=9,
        updated=0,
        unchanged=0,
        manifest_sha256="a" * 64,
    )
    return PipelineSummary(
        run_id="run-001",
        parent_run_id=None,
        status=RunStatus.DEGRADED,
        started_at_utc=now,
        completed_at_utc=now,
        workspace=tmp_path,
        warehouse_path=tmp_path / "gridbridge.duckdb",
        report_path=tmp_path / "report.html",
        source_summaries=[source],
        profiles=[
            DatasetProfile(
                source=SourceName.METER,
                row_count=10,
                columns=["meter_id"],
                null_counts={"meter_id": 0},
                distinct_counts={"meter_id": 2},
            )
        ],
        reconciliations=[
            ReconciliationResult(
                source=SourceName.METER,
                landed=10,
                accepted=9,
                quarantined=1,
                loaded=9,
                balanced=True,
            )
        ],
        topology=TopologyResult(
            valid=False,
            issues=[
                TopologyIssue(
                    code="GIS_DANGLING_NODE",
                    detail="edge references missing node",
                    asset_id="LINE-009",
                )
            ],
            energized_nodes=4,
            energized_edges=3,
        ),
        flex_recommendations=[
            FlexRecommendation(
                feeder_id="FDR-001",
                interval_start_utc=now,
                status="blocked",
                advisory_kw=0.0,
                score=0.0,
                block_reasons=["topology_invalid"],
                factors={
                    "eligible_der_kw": 10.0,
                    "transformer_headroom_kw": 100.0,
                    "market_price_aud_per_mwh": 218.6,
                    "telemetry_age_minutes": 5.0,
                },
            )
        ],
        total_landed=10,
        total_accepted=9,
        total_quarantined=1,
        total_inserted=9,
        total_updated=0,
        total_unchanged=0,
        reconciliation_balanced=True,
        dbt_success=True,
    )


def test_report_is_standalone_and_contains_operational_evidence(tmp_path: Path) -> None:
    """Removing a key evidence panel or adding remote dependencies must fail review."""
    report = render_report(_summary(tmp_path), tmp_path / "report.html")
    html = report.read_text(encoding="utf-8")

    assert "Source reconciliation" in html
    assert "Topology findings" in html
    assert "Flex advisory" in html
    assert "GIS_DANGLING_NODE" in html
    assert "topology_invalid" in html
    assert "Synthetic portfolio demonstration" in html
    assert "https://" not in html
    assert "http://" not in html
    assert "C:\\Users" not in html


def test_report_uses_semantic_status_and_table_markup(tmp_path: Path) -> None:
    """The evidence remains readable without charts, JavaScript, or colour alone."""
    html = render_report(_summary(tmp_path), tmp_path / "report.html").read_text(encoding="utf-8")

    assert "<title>GridBridge onboarding evidence</title>" in html
    assert html.count("<table") >= 2
    assert 'aria-label="Run status: degraded"' in html
    assert "<script" not in html
