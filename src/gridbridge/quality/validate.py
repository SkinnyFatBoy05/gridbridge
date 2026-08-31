"""Row-level source validation with lossless quarantine evidence."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from gridbridge.models import (
    QuarantineRecord,
    ReasonCode,
    SourceManifest,
    SourceName,
    ValidationOutcome,
)
from gridbridge.security.evidence import fingerprint_payload, redact_identifier

Validator = Callable[[dict[str, object], set[tuple[object, ...]]], ReasonCode | None]


def _meter_reason(row: dict[str, object], seen: set[tuple[object, ...]]) -> ReasonCode | None:
    key = (row.get("meter_id"), row.get("channel"), row.get("interval_start_utc"))
    if key in seen:
        return ReasonCode.METER_DUPLICATE_INTERVAL
    seen.add(key)
    if row.get("energy_unit") not in {"Wh", "kWh", "MWh"}:
        return ReasonCode.UNIT_UNSUPPORTED
    value = row.get("energy_value")
    if isinstance(value, (int, float)) and value < 0:
        return ReasonCode.METER_NEGATIVE_IMPORT
    return None


def _scada_reason(row: dict[str, object], seen: set[tuple[object, ...]]) -> ReasonCode | None:
    if row.get("quality_code") != "GOOD":
        return ReasonCode.SCADA_BAD_QUALITY
    key = (row.get("point_id"), row.get("sequence_number"))
    if key in seen:
        return ReasonCode.SCADA_DUPLICATE_SEQUENCE
    seen.add(key)
    value = row.get("value")
    if isinstance(value, (int, float)) and abs(value) > 50_000:
        return ReasonCode.SCADA_IMPLAUSIBLE_VALUE
    return None


def _der_reason(row: dict[str, object], seen: set[tuple[object, ...]]) -> ReasonCode | None:
    key = (row.get("der_id"),)
    if key in seen:
        return ReasonCode.DER_DUPLICATE
    seen.add(key)
    unit = row.get("nameplate_unit")
    if unit not in {"W", "kW", "MW"}:
        return ReasonCode.DER_UNIT_UNSUPPORTED
    factor = {"W": 0.001, "kW": 1.0, "MW": 1000.0}[str(unit)]
    nameplate = float(str(row.get("nameplate_value", 0.0))) * factor
    if float(str(row.get("export_limit_kw", 0.0))) > nameplate:
        return ReasonCode.DER_EXPORT_ABOVE_NAMEPLATE
    return None


def _market_reason(row: dict[str, object], seen: set[tuple[object, ...]]) -> ReasonCode | None:
    if row.get("region") not in {"NSW1", "QLD1", "SA1", "TAS1", "VIC1"}:
        return ReasonCode.MARKET_INVALID_REGION
    key = (row.get("region"), row.get("interval_start"), row.get("revision"))
    if key in seen:
        return ReasonCode.MARKET_DUPLICATE_INTERVAL
    seen.add(key)
    return None


def _gis_reason(row: dict[str, object], _: set[tuple[object, ...]]) -> ReasonCode | None:
    if row.get("geometry_json") in {None, "null"}:
        return ReasonCode.GIS_MISSING_GEOMETRY
    voltage = row.get("nominal_voltage_v")
    if not isinstance(voltage, (int, float)) or voltage <= 0:
        return ReasonCode.GIS_INVALID_VOLTAGE
    return None


_VALIDATORS: dict[SourceName, Validator] = {
    SourceName.METER: _meter_reason,
    SourceName.GIS: _gis_reason,
    SourceName.SCADA: _scada_reason,
    SourceName.DER: _der_reason,
    SourceName.MARKET: _market_reason,
}


def validate_source(
    source: SourceName,
    frame: pl.DataFrame,
    manifest: SourceManifest,
) -> ValidationOutcome:
    """Split accepted rows from quarantined evidence using stable reason codes."""

    valid_rows: list[dict[str, object]] = []
    quarantined: list[QuarantineRecord] = []
    seen: set[tuple[object, ...]] = set()
    validator = _VALIDATORS[source]
    for index, row in enumerate(frame.to_dicts(), start=1):
        reason = validator(row, seen)
        if reason is None:
            valid_rows.append(row)
            continue
        record_id = str(row.get("source_record_id") or f"row-{index}")
        quarantined.append(
            QuarantineRecord(
                run_id=manifest.run_id,
                source=source,
                source_record_id=record_id,
                reason_code=reason,
                detail=f"{source.value} record rejected by {reason.value}",
                payload_preview=f"record={redact_identifier(record_id)}",
                payload_fingerprint=fingerprint_payload(row),
                source_file_hash=manifest.sha256,
            )
        )
    valid = pl.DataFrame(valid_rows) if valid_rows else frame.head(0)
    return ValidationOutcome(valid=valid, quarantined=quarantined)
