from datetime import UTC, datetime
from pathlib import Path

import duckdb
import polars as pl

from gridbridge.models import QuarantineRecord, ReasonCode, SourceName
from gridbridge.pipeline.warehouse import Warehouse


def test_load_frame_is_idempotent_and_tracks_unchanged_rows(tmp_path: Path) -> None:
    """Replaying the same source drop must not duplicate canonical facts."""
    warehouse = Warehouse(tmp_path / "gridbridge.duckdb", run_id="run-001")
    warehouse.initialize()
    frame = pl.DataFrame(
        {
            "meter_id": ["M1"],
            "channel": ["E1"],
            "interval_start_utc": [datetime(2026, 8, 31, 0, 5, tzinfo=UTC)],
            "energy_kwh": [1.25],
        }
    )

    first = warehouse.load_frame(
        "meter_intervals", frame, ("meter_id", "channel", "interval_start_utc")
    )
    second = warehouse.load_frame(
        "meter_intervals", frame, ("meter_id", "channel", "interval_start_utc")
    )

    assert first.model_dump() == {"inserted": 1, "updated": 0, "unchanged": 0}
    assert second.model_dump() == {"inserted": 0, "updated": 0, "unchanged": 1}
    with duckdb.connect(str(warehouse.path), read_only=True) as connection:
        assert connection.execute("select count(*) from meter_intervals").fetchone() == (1,)


def test_corrected_payload_updates_fact_without_duplication(tmp_path: Path) -> None:
    """A corrected value for the same natural key replaces the fact and records an update."""
    path = tmp_path / "gridbridge.duckdb"
    original = Warehouse(path, run_id="run-001")
    original.initialize()
    original.load_frame(
        "der_units",
        pl.DataFrame({"der_id": ["DER-1"], "nameplate_kw": [5.0]}),
        ("der_id",),
    )
    corrected = Warehouse(path, run_id="run-002")

    result = corrected.load_frame(
        "der_units",
        pl.DataFrame({"der_id": ["DER-1"], "nameplate_kw": [8.0]}),
        ("der_id",),
    )

    assert result.model_dump() == {"inserted": 0, "updated": 1, "unchanged": 0}
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute(
            "select nameplate_kw, _run_id from der_units where der_id = 'DER-1'"
        ).fetchone() == (8.0, "run-002")


def test_quarantine_evidence_is_persisted_once(tmp_path: Path) -> None:
    """Replaying an invalid record preserves one stable evidence row rather than duplicates."""
    warehouse = Warehouse(tmp_path / "gridbridge.duckdb", run_id="run-001")
    warehouse.initialize()
    record = QuarantineRecord(
        run_id="run-001",
        source=SourceName.SCADA,
        source_record_id="SCADA-BAD",
        reason_code=ReasonCode.SCADA_BAD_QUALITY,
        detail="bad quality",
        payload_preview="record=redacted:abc",
        payload_fingerprint="f" * 64,
        source_file_hash="a" * 64,
    )

    assert warehouse.record_quarantine([record]) == 1
    assert warehouse.record_quarantine([record]) == 0
