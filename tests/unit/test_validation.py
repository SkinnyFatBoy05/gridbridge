from pathlib import Path

import polars as pl

from gridbridge.models import ReasonCode, SourceName
from gridbridge.quality.validate import validate_source
from gridbridge.security.evidence import build_manifest


def _manifest(tmp_path: Path, source: SourceName):
    path = tmp_path / f"{source}.data"
    path.write_text("synthetic", encoding="utf-8")
    return build_manifest(path, source, "run-001")


def test_bad_scada_quality_is_quarantined_with_redacted_evidence(tmp_path: Path) -> None:
    """Bad telemetry must remain auditable but cannot enter operational calculations."""
    frame = pl.DataFrame(
        {
            "source_record_id": ["SCADA-BAD"],
            "point_id": ["PT-1"],
            "asset_id": ["LINE-1"],
            "quality_code": ["BAD"],
            "value": [250.0],
            "sequence_number": [1],
        }
    )

    outcome = validate_source(SourceName.SCADA, frame, _manifest(tmp_path, SourceName.SCADA))

    assert outcome.valid.height == 0
    assert len(outcome.quarantined) == 1
    assert outcome.quarantined[0].reason_code is ReasonCode.SCADA_BAD_QUALITY
    assert "PT-1" not in outcome.quarantined[0].payload_preview


def test_meter_duplicate_is_quarantined_without_discarding_first_row(tmp_path: Path) -> None:
    """Duplicate intervals keep the first canonical fact and quarantine later arrivals."""
    frame = pl.DataFrame(
        {
            "source_record_id": ["R1", "R2"],
            "meter_id": ["M1", "M1"],
            "channel": ["E1", "E1"],
            "interval_start_utc": ["2026-08-31T00:05:00Z", "2026-08-31T00:05:00Z"],
            "energy_value": [1.2, 1.2],
            "energy_unit": ["kWh", "kWh"],
        }
    )

    outcome = validate_source(SourceName.METER, frame, _manifest(tmp_path, SourceName.METER))

    assert outcome.valid["source_record_id"].to_list() == ["R1"]
    assert [record.reason_code for record in outcome.quarantined] == [
        ReasonCode.METER_DUPLICATE_INTERVAL
    ]
