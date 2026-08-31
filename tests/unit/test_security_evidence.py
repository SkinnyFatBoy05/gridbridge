import hashlib
from pathlib import Path

from gridbridge.models import SourceName
from gridbridge.security.evidence import build_manifest, redact_identifier, sha256_file


def test_manifest_captures_file_integrity_evidence(tmp_path: Path) -> None:
    """Changing a landed file must change the integrity evidence carried downstream."""
    source = tmp_path / "meter.csv"
    source.write_bytes(b"meter_id,value\nM1,1.5\n")

    manifest = build_manifest(source, SourceName.METER, "run-001")

    assert manifest.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest.sha256 == sha256_file(source)
    assert manifest.size_bytes == len(source.read_bytes())
    assert manifest.file_name == "meter.csv"


def test_redaction_is_stable_without_revealing_identifier() -> None:
    """Logs need joinable evidence without exposing meter identifiers."""
    redacted = redact_identifier("NMI00000001")

    assert redacted == redact_identifier("NMI00000001")
    assert redacted.startswith("redacted:")
    assert "NMI00000001" not in redacted
