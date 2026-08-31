import hashlib
import json
from pathlib import Path

from gridbridge.generators.sources import generate_sources
from gridbridge.models import SourceName


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_generate_sources_is_deterministic(tmp_path: Path) -> None:
    """The same seed must reproduce byte-identical client source drops."""
    first = generate_sources(tmp_path / "first", seed=42, meter_rows=288)
    second = generate_sources(tmp_path / "second", seed=42, meter_rows=288)

    first_hashes = {path.name: _digest(path) for paths in first.values() for path in paths}
    second_hashes = {path.name: _digest(path) for paths in second.values() for path in paths}

    assert first_hashes == second_hashes
    assert set(first) == set(SourceName)


def test_generate_sources_documents_known_defects(tmp_path: Path) -> None:
    """The fixture must contain controlled evidence for every source category."""
    generate_sources(tmp_path, seed=42, meter_rows=288)

    defects = json.loads((tmp_path / "expected_defects.json").read_text(encoding="utf-8"))

    assert {defect["source"] for defect in defects} == {
        "meter",
        "gis",
        "scada",
        "der",
        "market",
    }
    assert "METER_DUPLICATE_INTERVAL" in {defect["reason_code"] for defect in defects}
    assert "GIS_DANGLING_NODE" in {defect["reason_code"] for defect in defects}
