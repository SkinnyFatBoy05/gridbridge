"""Reproducible high-volume meter interval benchmark."""

from __future__ import annotations

import os
import platform
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import duckdb
from pydantic import BaseModel, ConfigDict


class BenchmarkResult(BaseModel):
    """Machine-contextualized observations from one local benchmark run."""

    model_config = ConfigDict(frozen=True)

    rows: int
    accepted: int
    quarantined: int
    seed: int
    generation_seconds: float
    load_seconds: float
    rows_per_second: float
    query_milliseconds: float
    parquet_bytes: int
    database_bytes: int
    python_version: str
    platform: str
    processor: str
    completed_at_utc: datetime
    evidence_path: Path


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def run_meter_benchmark(
    output_dir: Path,
    rows: int = 1_000_000,
    seed: int = 42,
) -> BenchmarkResult:
    """Generate, contract-check, load, and query deterministic interval data."""

    if rows <= 0:
        raise ValueError("rows must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = output_dir / "meter_intervals.parquet"
    database_path = output_dir / "benchmark.duckdb"
    evidence_path = output_dir / "benchmark.json"

    generation_started = perf_counter()
    with duckdb.connect() as connection:
        connection.execute(
            f"""
            copy (
                select
                    'M' || lpad(cast(floor(i / 288) + 1 as varchar), 7, '0') as meter_id,
                    'FDR-' || lpad(cast((floor(i / 288) % 8) + 1 as varchar), 3, '0') as feeder_id,
                    'E1' as channel,
                    timestamptz '2026-08-31 00:00:00+00'
                        + (i % 288) * interval '5 minutes' as interval_start_utc,
                    5 as interval_minutes,
                    0.25 + (((i * 1103515245 + {int(seed)}) % 1000) / 1000.0) as energy_kwh
                from range({int(rows)}) as generated(i)
            ) to '{_sql_path(parquet_path)}'
            (format parquet, compression zstd, row_group_size 100000)
            """
        )
    generation_seconds = perf_counter() - generation_started

    load_started = perf_counter()
    with duckdb.connect(str(database_path)) as connection:
        connection.execute(
            f"""
            create table meter_intervals as
            select * from read_parquet('{_sql_path(parquet_path)}')
            where meter_id is not null
              and feeder_id is not null
              and channel = 'E1'
              and interval_minutes = 5
              and energy_kwh >= 0
            """
        )
        accepted_row = connection.execute("select count(*) from meter_intervals").fetchone()
        if accepted_row is None:
            raise RuntimeError("benchmark accepted-row query returned no result")
        accepted = int(accepted_row[0])
        query_started = perf_counter()
        connection.execute(
            """
            select feeder_id, date_trunc('day', interval_start_utc) as day,
                   sum(energy_kwh) as energy_kwh,
                   sum(energy_kwh * 12.0) as average_load_kw
            from meter_intervals
            group by feeder_id, day
            order by feeder_id, day
            """
        ).fetchall()
        query_milliseconds = (perf_counter() - query_started) * 1000.0
    load_seconds = perf_counter() - load_started
    processing_seconds = max(load_seconds, 1e-9)
    result = BenchmarkResult(
        rows=rows,
        accepted=accepted,
        quarantined=rows - accepted,
        seed=seed,
        generation_seconds=round(generation_seconds, 4),
        load_seconds=round(load_seconds, 4),
        rows_per_second=round(rows / processing_seconds, 1),
        query_milliseconds=round(max(query_milliseconds, 0.0001), 4),
        parquet_bytes=parquet_path.stat().st_size,
        database_bytes=database_path.stat().st_size,
        python_version=platform.python_version(),
        platform=platform.platform(),
        processor=platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown"),
        completed_at_utc=datetime.now(UTC),
        evidence_path=evidence_path,
    )
    evidence_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
