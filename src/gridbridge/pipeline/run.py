"""End-to-end onboarding composition shared by the CLI and Airflow."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb
import polars as pl
from pydantic import BaseModel, ConfigDict

from gridbridge.adapters.readers import read_source
from gridbridge.canonical.normalize import normalize_source
from gridbridge.config import load_config
from gridbridge.flex.recommend import FlexInputs, FlexRecommendation, recommend_flex
from gridbridge.generators.sources import generate_sources
from gridbridge.models import (
    DatasetProfile,
    LoadResult,
    ReconciliationResult,
    RunStatus,
    SourceManifest,
    SourceName,
)
from gridbridge.pipeline.dbt import run_dbt
from gridbridge.pipeline.reconcile import reconcile_source
from gridbridge.pipeline.warehouse import Warehouse
from gridbridge.quality.profile import profile_frame
from gridbridge.quality.validate import validate_source
from gridbridge.security.evidence import build_manifest
from gridbridge.topology.validate import TopologyResult, validate_topology


class UnknownParentRunError(ValueError):
    """Raised when replay lineage references a run that does not exist."""


class PipelineExecutionError(RuntimeError):
    """Raised when a mandatory fail-closed stage does not complete."""


class SourceRunSummary(BaseModel):
    """Per-source volume, quality, and persistence evidence."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    landed: int
    accepted: int
    quarantined: int
    inserted: int
    updated: int
    unchanged: int
    manifest_sha256: str


class PipelineSummary(BaseModel):
    """Serializable evidence for a complete onboarding attempt."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    parent_run_id: str | None
    status: RunStatus
    started_at_utc: datetime
    completed_at_utc: datetime
    workspace: Path
    warehouse_path: Path
    report_path: Path
    source_summaries: list[SourceRunSummary]
    profiles: list[DatasetProfile]
    reconciliations: list[ReconciliationResult]
    topology: TopologyResult
    flex_recommendations: list[FlexRecommendation]
    total_landed: int
    total_accepted: int
    total_quarantined: int
    total_inserted: int
    total_updated: int
    total_unchanged: int
    reconciliation_balanced: bool
    dbt_success: bool


_TABLES: dict[SourceName, tuple[str, tuple[str, ...]]] = {
    SourceName.METER: (
        "meter_intervals",
        ("meter_id", "channel", "interval_start_utc"),
    ),
    SourceName.GIS: ("network_assets", ("asset_id",)),
    SourceName.SCADA: (
        "scada_observations",
        ("point_id", "event_time_utc", "sequence_number"),
    ),
    SourceName.DER: ("der_units", ("der_id",)),
    SourceName.MARKET: (
        "market_prices",
        ("region", "interval_start_utc", "revision"),
    ),
}


def _record_run_start(
    warehouse: Warehouse,
    run_id: str,
    parent_run_id: str | None,
    started_at: datetime,
) -> None:
    warehouse.initialize()
    with duckdb.connect(str(warehouse.path)) as connection:
        if parent_run_id is not None:
            exists = connection.execute(
                "select count(*) from ingestion_runs where run_id = ?", [parent_run_id]
            ).fetchone()
            if not exists or exists[0] == 0:
                raise UnknownParentRunError(f"unknown parent run: {parent_run_id}")
        connection.execute(
            "insert into ingestion_runs values (?, ?, ?, ?, null)",
            [run_id, parent_run_id, RunStatus.FAILED.value, started_at],
        )


def _record_manifest(warehouse: Warehouse, manifest: SourceManifest) -> None:
    with duckdb.connect(str(warehouse.path)) as connection:
        connection.execute(
            "insert into source_manifests values (?, ?, ?, ?, ?, ?)",
            [
                manifest.run_id,
                manifest.source.value,
                manifest.file_name,
                manifest.sha256,
                manifest.size_bytes,
                manifest.landed_at_utc,
            ],
        )


def _record_reconciliation(
    warehouse: Warehouse,
    run_id: str,
    result: ReconciliationResult,
) -> None:
    with duckdb.connect(str(warehouse.path)) as connection:
        connection.execute(
            "insert into reconciliation_results values (?, ?, ?, ?, ?, ?, ?)",
            [
                run_id,
                result.source.value,
                result.landed,
                result.accepted,
                result.quarantined,
                result.loaded,
                result.balanced,
            ],
        )


def _record_run_complete(
    warehouse: Warehouse,
    run_id: str,
    status: RunStatus,
    completed_at: datetime,
) -> None:
    with duckdb.connect(str(warehouse.path)) as connection:
        connection.execute(
            "update ingestion_runs set status = ?, completed_at_utc = ? where run_id = ?",
            [status.value, completed_at, run_id],
        )


def _land_sources(
    source_paths: dict[SourceName, list[Path]],
    run_dir: Path,
    run_id: str,
) -> dict[SourceName, list[SourceManifest]]:
    manifests: dict[SourceName, list[SourceManifest]] = {}
    for source, paths in source_paths.items():
        landed_dir = run_dir / "raw" / source.value
        landed_dir.mkdir(parents=True, exist_ok=True)
        manifests[source] = []
        for path in paths:
            landed_path = landed_dir / path.name
            shutil.copy2(path, landed_path)
            manifests[source].append(build_manifest(landed_path, source, run_id))
    return manifests


def _topology_from_gis(frame: pl.DataFrame) -> TopologyResult:
    rows = frame.to_dicts()
    node_rows = [
        {
            "node_id": str(row["to_node"]),
            "node_type": str(row["asset_type"]),
            "nominal_voltage_v": int(row["nominal_voltage_v"]),
        }
        for row in rows
        if row.get("asset_type") in {"substation", "node"} and row.get("to_node")
    ]
    edge_rows = [
        {
            "asset_id": str(row["asset_id"]),
            "from_node": str(row["from_node"]),
            "to_node": str(row["to_node"]),
            "asset_type": str(row["asset_type"]),
            "status": str(row["status"]),
        }
        for row in rows
        if row.get("asset_type") in {"line", "transformer"}
    ]
    return validate_topology(pl.DataFrame(node_rows), pl.DataFrame(edge_rows))


def _flex_from_mart(
    warehouse_path: Path,
    topology: TopologyResult,
    config_path: Path,
) -> list[FlexRecommendation]:
    config = load_config(config_path)
    with duckdb.connect(str(warehouse_path), read_only=True) as connection:
        candidates = connection.execute(
            """
            select feeder_id, interval_start_utc, average_load_kw,
                   eligible_der_kw, price_aud_per_mwh
            from fct_flex_interval_candidates
            order by interval_start_utc
            limit 10
            """
        ).fetchall()
        scada_row = connection.execute(
            "select max(event_time_utc) from scada_observations where quality_code = 'GOOD'"
        ).fetchone()
    if not scada_row or scada_row[0] is None:
        raise PipelineExecutionError("no accepted GOOD SCADA observation is available")
    observed_at = scada_row[0]
    recommendations: list[FlexRecommendation] = []
    for feeder_id, interval, load_kw, der_kw, price in candidates:
        recommendations.append(
            recommend_flex(
                FlexInputs(
                    feeder_id=feeder_id,
                    interval_start_utc=interval,
                    net_load_kw=load_kw,
                    eligible_der_kw=der_kw,
                    transformer_capacity_kva=2_000.0,
                    market_price_aud_per_mwh=price,
                    scada_observed_at_utc=observed_at,
                    evaluation_time_utc=interval,
                    topology_valid=topology.valid,
                ),
                config,
            )
        )
    return recommendations


def run_demo(
    workspace: Path,
    config_path: Path,
    seed: int = 42,
    parent_run_id: str | None = None,
) -> PipelineSummary:
    """Run a deterministic onboarding attempt and return auditable evidence."""

    workspace = workspace.resolve()
    config_path = config_path.resolve()
    config = load_config(config_path)
    source_dir = workspace / "source_data"
    if not source_dir.exists():
        source_paths = generate_sources(source_dir, seed=seed, meter_rows=288)
    else:
        source_paths = {
            SourceName.METER: [source_dir / "meter_intervals.parquet"],
            SourceName.GIS: [source_dir / "network.geojson"],
            SourceName.SCADA: [source_dir / "scada.ndjson"],
            SourceName.DER: [source_dir / "der_register.csv"],
            SourceName.MARKET: [source_dir / "market_prices.json"],
        }

    run_id = uuid4().hex
    started_at = datetime.now(UTC)
    run_dir = workspace / "runs" / run_id
    warehouse = Warehouse(workspace / "gridbridge.duckdb", run_id=run_id)
    _record_run_start(warehouse, run_id, parent_run_id, started_at)

    manifests = _land_sources(source_paths, run_dir, run_id)
    profiles: list[DatasetProfile] = []
    source_summaries: list[SourceRunSummary] = []
    reconciliations: list[ReconciliationResult] = []
    canonical: dict[SourceName, pl.DataFrame] = {}

    for source in SourceName:
        source_manifests = manifests[source]
        for manifest in source_manifests:
            _record_manifest(warehouse, manifest)
        frame = read_source(source, [manifest.path for manifest in source_manifests])
        profiles.append(profile_frame(source, frame))
        outcome = validate_source(source, frame, source_manifests[0])
        valid = normalize_source(source, outcome.valid, config.timezone).with_columns(
            pl.lit(source.value).alias("source_system"),
            pl.lit(source_manifests[0].sha256).alias("source_file_hash"),
        )
        canonical[source] = valid
        warehouse.record_quarantine(outcome.quarantined)
        table, natural_keys = _TABLES[source]
        load_result: LoadResult = warehouse.load_frame(table, valid, natural_keys)
        loaded = load_result.inserted + load_result.updated + load_result.unchanged
        reconciliation = reconcile_source(
            source,
            landed=frame.height,
            accepted=valid.height,
            quarantined=len(outcome.quarantined),
            loaded=loaded,
        )
        _record_reconciliation(warehouse, run_id, reconciliation)
        reconciliations.append(reconciliation)
        source_summaries.append(
            SourceRunSummary(
                source=source,
                landed=frame.height,
                accepted=valid.height,
                quarantined=len(outcome.quarantined),
                inserted=load_result.inserted,
                updated=load_result.updated,
                unchanged=load_result.unchanged,
                manifest_sha256=source_manifests[0].sha256,
            )
        )

    project_dir = Path(__file__).resolve().parents[3] / "dbt"
    dbt_result = run_dbt(project_dir, warehouse.path)
    if not dbt_result.success:
        _record_run_complete(warehouse, run_id, RunStatus.FAILED, datetime.now(UTC))
        raise PipelineExecutionError(f"dbt build failed:\n{dbt_result.output}")

    topology = _topology_from_gis(canonical[SourceName.GIS])
    flex_recommendations = _flex_from_mart(warehouse.path, topology, config_path)
    completed_at = datetime.now(UTC)
    status = (
        RunStatus.DEGRADED
        if any(summary.quarantined for summary in source_summaries) or not topology.valid
        else RunStatus.SUCCESS
    )
    report_path = run_dir / "run-summary.json"
    summary = PipelineSummary(
        run_id=run_id,
        parent_run_id=parent_run_id,
        status=status,
        started_at_utc=started_at,
        completed_at_utc=completed_at,
        workspace=workspace,
        warehouse_path=warehouse.path,
        report_path=report_path,
        source_summaries=source_summaries,
        profiles=profiles,
        reconciliations=reconciliations,
        topology=topology,
        flex_recommendations=flex_recommendations,
        total_landed=sum(item.landed for item in source_summaries),
        total_accepted=sum(item.accepted for item in source_summaries),
        total_quarantined=sum(item.quarantined for item in source_summaries),
        total_inserted=sum(item.inserted for item in source_summaries),
        total_updated=sum(item.updated for item in source_summaries),
        total_unchanged=sum(item.unchanged for item in source_summaries),
        reconciliation_balanced=all(item.balanced for item in reconciliations),
        dbt_success=True,
    )
    report_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    _record_run_complete(warehouse, run_id, status, completed_at)
    return summary
