"""Dataset-level profiling for client onboarding evidence."""

from __future__ import annotations

import polars as pl

from gridbridge.models import DatasetProfile, SourceName

_TIMESTAMP_COLUMNS = (
    "interval_start_utc",
    "interval_start_local",
    "event_time",
    "interval_start",
)


def profile_frame(source: SourceName, frame: pl.DataFrame) -> DatasetProfile:
    """Summarize volume, shape, missingness, cardinality, and time coverage."""

    null_counts = {column: int(frame[column].null_count()) for column in frame.columns}
    distinct_counts = {column: int(frame[column].n_unique()) for column in frame.columns}
    timestamp_column = next((name for name in _TIMESTAMP_COLUMNS if name in frame.columns), None)
    timestamp_min: str | None = None
    timestamp_max: str | None = None
    if timestamp_column and frame.height:
        values = frame[timestamp_column].drop_nulls().cast(pl.String)
        if not values.is_empty():
            timestamp_min = str(values.min())
            timestamp_max = str(values.max())
    return DatasetProfile(
        source=source,
        row_count=frame.height,
        columns=frame.columns,
        null_counts=null_counts,
        distinct_counts=distinct_counts,
        timestamp_min=timestamp_min,
        timestamp_max=timestamp_max,
    )
