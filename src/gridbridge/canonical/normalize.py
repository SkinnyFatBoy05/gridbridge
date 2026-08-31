"""Explicit timestamp and unit normalization for accepted source rows."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import polars as pl

from gridbridge.models import SourceName


class UnsupportedUnitError(ValueError):
    """Raised when a unit cannot be mapped without guessing."""


class AmbiguousTimestampError(ValueError):
    """Raised when a local time occurs twice during daylight-saving rollback."""


def _normalize(value: float, unit: str, factors: dict[str, float]) -> float:
    try:
        return value * factors[unit]
    except KeyError as exc:
        raise UnsupportedUnitError(f"unsupported unit: {unit}") from exc


def normalize_power(value: float, unit: str) -> float:
    """Normalize instantaneous power to kW."""

    return _normalize(value, unit, {"W": 0.001, "kW": 1.0, "MW": 1000.0})


def normalize_energy(value: float, unit: str) -> float:
    """Normalize interval energy to kWh."""

    return _normalize(value, unit, {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0})


def normalize_timestamp(value: str, timezone: str) -> datetime:
    """Normalize an ISO timestamp to UTC, refusing ambiguous naive local times."""

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC)
    zone = ZoneInfo(timezone)
    earlier = parsed.replace(tzinfo=zone, fold=0)
    later = parsed.replace(tzinfo=zone, fold=1)
    if earlier.utcoffset() != later.utcoffset():
        raise AmbiguousTimestampError(f"timestamp requires an explicit offset: {value}")
    return earlier.astimezone(UTC)


def normalize_source(source: SourceName, frame: pl.DataFrame, timezone: str) -> pl.DataFrame:
    """Add canonical timestamp and unit columns while preserving source values."""

    rows: list[dict[str, object]] = []
    for source_row in frame.to_dicts():
        row = dict(source_row)
        if source is SourceName.METER:
            row["interval_start_utc"] = normalize_timestamp(
                str(row["interval_start_local"]), timezone
            )
            row["energy_kwh"] = normalize_energy(
                float(row["energy_value"]), str(row["energy_unit"])
            )
        elif source is SourceName.SCADA:
            row["event_time_utc"] = normalize_timestamp(str(row["event_time"]), timezone)
            row["power_kw"] = normalize_power(float(row["value"]), str(row["unit"]))
        elif source is SourceName.DER:
            row["nameplate_kw"] = normalize_power(
                float(row["nameplate_value"]), str(row["nameplate_unit"])
            )
        elif source is SourceName.MARKET:
            row["interval_start_utc"] = normalize_timestamp(str(row["interval_start"]), timezone)
        rows.append(row)
    return pl.DataFrame(rows) if rows else frame.clone()
