"""Run the checked-in dbt project against a run-specific DuckDB warehouse."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from gridbridge.models import DbtResult


def run_dbt(project_dir: Path, warehouse_path: Path) -> DbtResult:
    """Execute dbt build and capture operator-readable evidence."""

    project = project_dir.resolve()
    warehouse = warehouse_path.resolve()
    environment = os.environ.copy()
    environment["GRIDBRIDGE_DUCKDB_PATH"] = str(warehouse)
    process = subprocess.run(
        [
            "dbt",
            "build",
            "--project-dir",
            str(project),
            "--profiles-dir",
            str(project),
            "--no-use-colors",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )
    output = "\n".join(part.strip() for part in (process.stdout, process.stderr) if part.strip())
    return DbtResult(success=process.returncode == 0, command="dbt build", output=output)
