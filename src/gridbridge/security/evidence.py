"""Integrity and privacy evidence for landed utility records."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from gridbridge.models import SourceManifest, SourceName


def sha256_file(path: Path) -> str:
    """Hash a file in bounded chunks."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_payload(payload: object) -> str:
    """Create stable evidence for a canonicalized payload representation."""

    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def redact_identifier(value: str) -> str:
    """Return a stable, non-reversible identifier suitable for logs."""

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"redacted:{digest}"


def build_manifest(path: Path, source: SourceName, run_id: str) -> SourceManifest:
    """Capture immutable metadata for a landed source object."""

    stat = path.stat()
    return SourceManifest(
        run_id=run_id,
        source=source,
        path=path,
        file_name=path.name,
        sha256=sha256_file(path),
        size_bytes=stat.st_size,
        landed_at_utc=datetime.now(UTC),
    )
