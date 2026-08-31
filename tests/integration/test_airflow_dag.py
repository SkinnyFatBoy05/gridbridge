import ast
from pathlib import Path


def test_airflow_dag_calls_shared_pipeline_entry_point() -> None:
    """The scheduler must not grow a second onboarding implementation."""
    path = Path("airflow/dags/gridbridge_onboarding.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "gridbridge.pipeline.run"
        for alias in node.names
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "run_demo" in imports
    assert "run_demo" in calls
    assert "gridbridge_utility_onboarding" in path.read_text(encoding="utf-8")
