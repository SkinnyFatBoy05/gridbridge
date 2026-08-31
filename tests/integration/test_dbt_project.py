from datetime import UTC, datetime
from pathlib import Path

import duckdb
import polars as pl

from gridbridge.pipeline.dbt import run_dbt
from gridbridge.pipeline.warehouse import Warehouse


def _seed_warehouse(path: Path) -> None:
    warehouse = Warehouse(path, run_id="dbt-test")
    warehouse.initialize()
    interval = datetime(2026, 8, 31, 0, 5, tzinfo=UTC)
    warehouse.load_frame(
        "meter_intervals",
        pl.DataFrame(
            {
                "meter_id": ["M1", "M2"],
                "channel": ["E1", "E1"],
                "feeder_id": ["FDR-001", "FDR-001"],
                "interval_start_utc": [interval, interval],
                "interval_minutes": [5, 5],
                "energy_kwh": [1.0, 2.0],
            }
        ),
        ("meter_id", "channel", "interval_start_utc"),
    )
    warehouse.load_frame(
        "scada_observations",
        pl.DataFrame(
            {
                "point_id": ["PT-1"],
                "event_time_utc": [interval],
                "sequence_number": [1],
                "asset_id": ["LINE-001"],
                "quality_code": ["GOOD"],
                "power_kw": [35.5],
            }
        ),
        ("point_id", "event_time_utc", "sequence_number"),
    )
    warehouse.load_frame(
        "der_units",
        pl.DataFrame(
            {
                "der_id": ["DER-1"],
                "feeder_id": ["FDR-001"],
                "nameplate_kw": [10.0],
                "export_limit_kw": [8.0],
            }
        ),
        ("der_id",),
    )
    warehouse.load_frame(
        "market_prices",
        pl.DataFrame(
            {
                "region": ["NSW1"],
                "interval_start_utc": [interval],
                "revision": [1],
                "price_aud_per_mwh": [218.6],
                "intervention": [False],
            }
        ),
        ("region", "interval_start_utc", "revision"),
    )


def test_dbt_build_creates_tested_flex_candidate_mart(tmp_path: Path) -> None:
    """Breaking source lineage, mart grain, or dbt tests must fail the build."""
    warehouse_path = tmp_path / "gridbridge.duckdb"
    _seed_warehouse(warehouse_path)

    result = run_dbt(Path("dbt"), warehouse_path)

    assert result.success, result.output
    assert result.command == "dbt build"
    with duckdb.connect(str(warehouse_path), read_only=True) as connection:
        row = connection.execute(
            """
            select feeder_id, energy_kwh, average_load_kw, eligible_der_kw,
                   price_aud_per_mwh
            from fct_flex_interval_candidates
            """
        ).fetchone()
    assert row == ("FDR-001", 3.0, 36.0, 8.0, 218.6)
