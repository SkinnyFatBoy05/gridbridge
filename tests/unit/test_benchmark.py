import json
from pathlib import Path

from gridbridge.benchmark import run_meter_benchmark


def test_benchmark_processes_requested_rows_and_records_context(tmp_path: Path) -> None:
    """A broken generator, load, query, or evidence write must fail the scale proof."""
    result = run_meter_benchmark(tmp_path, rows=10_000, seed=42)

    assert result.rows == 10_000
    assert result.accepted == 10_000
    assert result.quarantined == 0
    assert result.rows_per_second > 0
    assert result.query_milliseconds > 0
    assert result.parquet_bytes > 0
    assert result.database_bytes > 0
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert evidence["rows"] == 10_000
    assert evidence["python_version"].startswith("3.12")


def test_benchmark_rejects_non_positive_volume(tmp_path: Path) -> None:
    """A zero-row run cannot be published as time-series scale evidence."""
    try:
        run_meter_benchmark(tmp_path, rows=0)
    except ValueError as exc:
        assert str(exc) == "rows must be positive"
    else:
        raise AssertionError("zero-row benchmark should fail")
