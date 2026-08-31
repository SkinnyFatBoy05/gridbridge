from datetime import UTC, datetime

import polars as pl
import pytest

from gridbridge.canonical.normalize import (
    AmbiguousTimestampError,
    UnsupportedUnitError,
    normalize_energy,
    normalize_power,
    normalize_source,
    normalize_timestamp,
)
from gridbridge.models import SourceName


def test_power_and_energy_use_distinct_canonical_units() -> None:
    """Power and interval energy must never be silently interchanged."""
    assert normalize_power(2.5, "MW") == 2500.0
    assert normalize_power(800.0, "W") == 0.8
    assert normalize_energy(2.5, "MWh") == 2500.0
    assert normalize_energy(800.0, "Wh") == 0.8
    with pytest.raises(UnsupportedUnitError):
        normalize_power(1.0, "MWh")


def test_ambiguous_sydney_local_time_requires_offset() -> None:
    """The repeated daylight-saving hour cannot be guessed during onboarding."""
    with pytest.raises(AmbiguousTimestampError):
        normalize_timestamp("2026-04-05T02:30:00", "Australia/Sydney")

    result = normalize_timestamp("2026-04-05T02:30:00+10:00", "Australia/Sydney")
    assert result == datetime(2026, 4, 4, 16, 30, tzinfo=UTC)


def test_meter_normalization_preserves_source_fields_and_adds_canonical_values() -> None:
    """A normalized meter row remains traceable to its original value and unit."""
    frame = pl.DataFrame(
        {
            "source_record_id": ["R1"],
            "meter_id": ["M1"],
            "interval_start_local": ["2026-08-31T10:05:00+10:00"],
            "energy_value": [750.0],
            "energy_unit": ["Wh"],
        }
    )

    normalized = normalize_source(SourceName.METER, frame, "Australia/Sydney")

    assert normalized["energy_kwh"].to_list() == [0.75]
    assert normalized["energy_value"].to_list() == [750.0]
    assert normalized["energy_unit"].to_list() == ["Wh"]
    assert normalized["interval_start_utc"].to_list() == [datetime(2026, 8, 31, 0, 5, tzinfo=UTC)]
