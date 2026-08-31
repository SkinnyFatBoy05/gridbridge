"""Shared domain models used across GridBridge pipeline stages."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class SourceName(StrEnum):
    """Supported client source-system categories."""

    METER = "meter"
    GIS = "gis"
    SCADA = "scada"
    DER = "der"
    MARKET = "market"


class RunStatus(StrEnum):
    """Observable pipeline completion states."""

    SUCCESS = "success"
    DEGRADED = "degraded"
    FAILED = "failed"


class ReasonCode(StrEnum):
    """Stable data-quality reason codes exposed to operators."""

    METER_DUPLICATE_INTERVAL = "METER_DUPLICATE_INTERVAL"
    METER_NEGATIVE_IMPORT = "METER_NEGATIVE_IMPORT"
    METER_UNKNOWN = "METER_UNKNOWN"
    TIMESTAMP_DST_AMBIGUOUS = "TIMESTAMP_DST_AMBIGUOUS"
    UNIT_UNSUPPORTED = "UNIT_UNSUPPORTED"
    GIS_DANGLING_NODE = "GIS_DANGLING_NODE"
    GIS_MISSING_GEOMETRY = "GIS_MISSING_GEOMETRY"
    GIS_INVALID_VOLTAGE = "GIS_INVALID_VOLTAGE"
    SCADA_BAD_QUALITY = "SCADA_BAD_QUALITY"
    SCADA_DUPLICATE_SEQUENCE = "SCADA_DUPLICATE_SEQUENCE"
    SCADA_IMPLAUSIBLE_VALUE = "SCADA_IMPLAUSIBLE_VALUE"
    SCADA_UNKNOWN_ASSET = "SCADA_UNKNOWN_ASSET"
    DER_DUPLICATE = "DER_DUPLICATE"
    DER_UNIT_UNSUPPORTED = "DER_UNIT_UNSUPPORTED"
    DER_UNKNOWN_CONNECTION = "DER_UNKNOWN_CONNECTION"
    DER_EXPORT_ABOVE_NAMEPLATE = "DER_EXPORT_ABOVE_NAMEPLATE"
    MARKET_DUPLICATE_INTERVAL = "MARKET_DUPLICATE_INTERVAL"
    MARKET_INVALID_REGION = "MARKET_INVALID_REGION"


class SourceManifest(BaseModel):
    """Immutable evidence about one landed source object."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    source: SourceName
    path: Path
    file_name: str
    sha256: str
    size_bytes: int
    landed_at_utc: datetime


class QuarantineRecord(BaseModel):
    """A rejected row with stable, redacted operational evidence."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    source: SourceName
    source_record_id: str
    reason_code: ReasonCode
    detail: str
    payload_preview: str
    payload_fingerprint: str
    source_file_hash: str


class DatasetProfile(BaseModel):
    """Compact, serializable source health summary."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    row_count: int
    columns: list[str]
    null_counts: dict[str, int]
    distinct_counts: dict[str, int]
    timestamp_min: str | None = None
    timestamp_max: str | None = None


class ValidationOutcome(BaseModel):
    """Accepted rows and the evidence explaining every rejected row."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    valid: Any
    quarantined: list[QuarantineRecord]
