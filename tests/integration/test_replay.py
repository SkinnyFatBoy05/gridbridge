from pathlib import Path

import duckdb
import pytest

from gridbridge.pipeline.run import UnknownParentRunError, run_demo


def test_replay_records_parent_run_lineage(tmp_path: Path) -> None:
    """Corrected onboarding attempts must remain linked to the run they replace."""
    parent = run_demo(tmp_path, Path("config/pipeline.yml"))

    replay = run_demo(
        tmp_path,
        Path("config/pipeline.yml"),
        parent_run_id=parent.run_id,
    )

    assert replay.parent_run_id == parent.run_id
    with duckdb.connect(str(replay.warehouse_path), read_only=True) as connection:
        assert connection.execute(
            "select parent_run_id from ingestion_runs where run_id = ?", [replay.run_id]
        ).fetchone() == (parent.run_id,)


def test_replay_rejects_unknown_parent_before_writing_run(tmp_path: Path) -> None:
    """A mistyped parent ID cannot create an orphaned audit event."""
    with pytest.raises(UnknownParentRunError, match="missing-parent"):
        run_demo(
            tmp_path,
            Path("config/pipeline.yml"),
            parent_run_id="missing-parent",
        )
