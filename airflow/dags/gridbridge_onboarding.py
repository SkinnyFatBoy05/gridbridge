"""Airflow entry point for the same pipeline exercised by the local CLI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

try:
    from airflow.sdk import dag, task
except ImportError:  # Airflow 2 compatibility for reviewers with an older local runtime.
    from airflow.decorators import dag, task

from gridbridge.pipeline.run import run_demo


@dag(
    dag_id="gridbridge_utility_onboarding",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["portfolio", "utility", "onboarding"],
)
def gridbridge_utility_onboarding():
    """Execute a manually triggered synthetic utility onboarding run."""

    @task()
    def onboard() -> dict[str, object]:
        summary = run_demo(
            Path("/opt/airflow/work/demo"),
            Path("/opt/airflow/gridbridge/config/pipeline.yml"),
        )
        return {
            "run_id": summary.run_id,
            "status": summary.status.value,
            "report_path": str(summary.report_path),
            "quarantined": summary.total_quarantined,
        }

    onboard()


gridbridge_utility_onboarding()
