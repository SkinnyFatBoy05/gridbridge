import polars as pl

from gridbridge.models import SourceName
from gridbridge.quality.profile import profile_frame


def test_profile_exposes_missingness_cardinality_and_time_coverage() -> None:
    """Removing any onboarding health dimension should break reviewer evidence."""
    frame = pl.DataFrame(
        {
            "meter_id": ["M1", "M1", "M2"],
            "interval_start_utc": [
                "2026-08-31T00:05:00Z",
                "2026-08-31T00:10:00Z",
                "2026-08-31T00:15:00Z",
            ],
            "energy_value": [1.0, None, 2.0],
        }
    )

    profile = profile_frame(SourceName.METER, frame)

    assert profile.row_count == 3
    assert profile.null_counts["energy_value"] == 1
    assert profile.distinct_counts["meter_id"] == 2
    assert profile.timestamp_min == "2026-08-31T00:05:00Z"
    assert profile.timestamp_max == "2026-08-31T00:15:00Z"
