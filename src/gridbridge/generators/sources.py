"""Generate deterministic, deliberately messy utility source drops."""

from __future__ import annotations

import csv
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from random import Random
from zoneinfo import ZoneInfo

import polars as pl

from gridbridge.models import ReasonCode, SourceName


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _meter_rows(count: int, seed: int) -> list[dict[str, object]]:
    rng = Random(seed)
    start = datetime(2026, 8, 30, tzinfo=UTC)
    rows: list[dict[str, object]] = []
    for index in range(count):
        timestamp = start + timedelta(minutes=5 * index)
        baseline = 1.25 + 0.65 * math.sin(index / 18)
        rows.append(
            {
                "source_record_id": f"MTR-{index + 1:06d}",
                "meter_id": f"M{index % 12 + 1:03d}",
                "nmi": f"NMI{index % 12 + 1:08d}",
                "connection_point_id": f"CP-{index % 12 + 1:03d}",
                "feeder_id": "FDR-001",
                "channel": "E1",
                "interval_start_local": timestamp.astimezone(
                    ZoneInfo("Australia/Sydney")
                ).isoformat(),
                "interval_start_utc": timestamp.isoformat(),
                "interval_minutes": 5,
                "energy_value": round(baseline + rng.uniform(-0.05, 0.05), 4),
                "energy_unit": "kWh",
                "quality_method": "A",
            }
        )
    duplicate = dict(rows[4])
    duplicate["source_record_id"] = "MTR-DUPLICATE"
    rows.append(duplicate)
    return rows


def _write_meter(path: Path, count: int, seed: int) -> None:
    pl.DataFrame(_meter_rows(count, seed)).write_parquet(
        path,
        compression="zstd",
        statistics=True,
        row_group_size=10_000,
    )


def _write_gis(path: Path) -> None:
    features = [
        {
            "type": "Feature",
            "properties": {
                "asset_id": "SUB-001",
                "asset_type": "substation",
                "from_node": None,
                "to_node": "N-SUB",
                "nominal_voltage_v": 11000,
                "rated_capacity_kva": 5000,
                "status": "energized",
            },
            "geometry": {"type": "Point", "coordinates": [151.2093, -33.8688]},
        },
        {
            "type": "Feature",
            "properties": {
                "asset_id": "LINE-001",
                "asset_type": "line",
                "from_node": "N-SUB",
                "to_node": "N-001",
                "nominal_voltage_v": 11000,
                "rated_capacity_kva": 2000,
                "status": "energized",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[151.2093, -33.8688], [151.21, -33.8695]],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "asset_id": "LINE-DANGLING",
                "asset_type": "line",
                "from_node": "N-001",
                "to_node": "N-MISSING",
                "nominal_voltage_v": 415,
                "rated_capacity_kva": 100,
                "status": "energized",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[151.21, -33.8695], [151.211, -33.87]],
            },
        },
    ]
    _write_json(path, {"type": "FeatureCollection", "features": features})


def _write_scada(path: Path) -> None:
    observations = [
        {
            "source_record_id": "SCADA-001",
            "point_id": "PT-FDR-LOAD",
            "asset_id": "LINE-001",
            "event_time": "2026-08-31T00:10:00Z",
            "value": 520.0,
            "unit": "kW",
            "quality_code": "GOOD",
            "sequence_number": 2,
        },
        {
            "source_record_id": "SCADA-002",
            "point_id": "PT-FDR-LOAD",
            "asset_id": "LINE-001",
            "event_time": "2026-08-31T00:05:00Z",
            "value": 515.0,
            "unit": "kW",
            "quality_code": "GOOD",
            "sequence_number": 1,
        },
        {
            "source_record_id": "SCADA-BAD",
            "point_id": "PT-FDR-LOAD",
            "asset_id": "LINE-001",
            "event_time": "2026-08-31T00:15:00Z",
            "value": 99999.0,
            "unit": "kW",
            "quality_code": "BAD",
            "sequence_number": 3,
        },
    ]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for observation in observations:
            handle.write(json.dumps(observation, sort_keys=True) + "\n")


def _write_der(path: Path) -> None:
    fields = [
        "source_record_id",
        "der_id",
        "connection_point_id",
        "technology_type",
        "nameplate_value",
        "nameplate_unit",
        "export_limit_kw",
        "phase",
        "commissioned_date",
    ]
    rows = [
        ["DER-ROW-001", "DER-001", "CP-001", "solar_pv", 8.0, "kW", 5.0, "ABC", "2024-05-01"],
        ["DER-ROW-002", "DER-002", "CP-002", "battery", 0.012, "MW", 10.0, "ABC", "2025-11-12"],
        ["DER-ROW-BAD", "DER-003", "CP-MISSING", "solar_pv", 6.0, "MVA", 8.0, "X", "2026-02-14"],
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)


def _write_market(path: Path) -> None:
    _write_json(
        path,
        {
            "published_at": "2026-08-31T00:20:00Z",
            "data": [
                {
                    "region": "NSW1",
                    "interval_start": "2026-08-31T00:05:00Z",
                    "price_aud_per_mwh": 82.4,
                    "intervention": False,
                    "revision": 1,
                },
                {
                    "region": "NSW1",
                    "interval_start": "2026-08-31T00:10:00Z",
                    "price_aud_per_mwh": 218.6,
                    "intervention": False,
                    "revision": 1,
                },
                {
                    "region": "INVALID",
                    "interval_start": "2026-08-31T00:15:00Z",
                    "price_aud_per_mwh": 175.0,
                    "intervention": False,
                    "revision": 1,
                },
            ],
        },
    )


def generate_sources(
    output_dir: Path,
    seed: int = 42,
    meter_rows: int = 288,
) -> dict[SourceName, list[Path]]:
    """Generate five deterministic source drops plus a known-defect ledger."""

    if meter_rows < 12:
        raise ValueError("meter_rows must be at least 12")
    output_dir.mkdir(parents=True, exist_ok=True)
    meter_path = output_dir / "meter_intervals.parquet"
    gis_path = output_dir / "network.geojson"
    scada_path = output_dir / "scada.ndjson"
    der_path = output_dir / "der_register.csv"
    market_path = output_dir / "market_prices.json"

    _write_meter(meter_path, meter_rows, seed)
    _write_gis(gis_path)
    _write_scada(scada_path)
    _write_der(der_path)
    _write_market(market_path)

    defects = [
        {"source": "meter", "reason_code": ReasonCode.METER_DUPLICATE_INTERVAL},
        {"source": "gis", "reason_code": ReasonCode.GIS_DANGLING_NODE},
        {"source": "scada", "reason_code": ReasonCode.SCADA_BAD_QUALITY},
        {"source": "der", "reason_code": ReasonCode.DER_UNIT_UNSUPPORTED},
        {"source": "market", "reason_code": ReasonCode.MARKET_INVALID_REGION},
    ]
    _write_json(output_dir / "expected_defects.json", defects)
    return {
        SourceName.METER: [meter_path],
        SourceName.GIS: [gis_path],
        SourceName.SCADA: [scada_path],
        SourceName.DER: [der_path],
        SourceName.MARKET: [market_path],
    }
