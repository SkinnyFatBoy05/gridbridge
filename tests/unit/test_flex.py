from datetime import UTC, datetime, timedelta

import pytest

from gridbridge.config import PipelineConfig
from gridbridge.flex.recommend import FlexInputs, recommend_flex

NOW = datetime(2026, 8, 31, 1, 0, tzinfo=UTC)


def _inputs(**updates: object) -> FlexInputs:
    values: dict[str, object] = {
        "feeder_id": "FDR-001",
        "interval_start_utc": NOW + timedelta(minutes=5),
        "net_load_kw": 600.0,
        "eligible_der_kw": 120.0,
        "transformer_capacity_kva": 1_000.0,
        "market_price_aud_per_mwh": 220.0,
        "scada_observed_at_utc": NOW - timedelta(minutes=5),
        "evaluation_time_utc": NOW,
        "topology_valid": True,
    }
    values.update(updates)
    return FlexInputs.model_validate(values)


@pytest.mark.parametrize(
    ("updates", "expected_reason"),
    [
        ({"topology_valid": False}, "topology_invalid"),
        ({"scada_observed_at_utc": NOW - timedelta(minutes=16)}, "telemetry_stale"),
        ({"net_load_kw": 920.0}, "transformer_headroom_exhausted"),
    ],
)
def test_failed_safety_gate_blocks_advice(updates: dict[str, object], expected_reason: str) -> None:
    """Removing any mandatory safety gate must allow this test to catch the regression."""
    recommendation = recommend_flex(_inputs(**updates), PipelineConfig())

    assert recommendation.status == "blocked"
    assert expected_reason in recommendation.block_reasons
    assert recommendation.advisory_kw == 0.0


def test_low_market_price_is_not_economic() -> None:
    """Safe capacity alone must not create an economic recommendation."""
    recommendation = recommend_flex(
        _inputs(market_price_aud_per_mwh=80.0),
        PipelineConfig(),
    )

    assert recommendation.status == "not_economic"
    assert recommendation.advisory_kw == 0.0


def test_valid_high_price_interval_returns_explainable_review_candidate() -> None:
    """A review candidate exposes bounded capacity and every scoring factor."""
    recommendation = recommend_flex(_inputs(), PipelineConfig())

    assert recommendation.status == "review"
    assert recommendation.advisory_kw == 120.0
    assert recommendation.score == 0.73
    assert recommendation.factors == {
        "eligible_der_kw": 120.0,
        "transformer_headroom_kw": 300.0,
        "market_price_aud_per_mwh": 220.0,
        "telemetry_age_minutes": 5.0,
    }
