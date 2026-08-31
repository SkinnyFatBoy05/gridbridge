"""Fail-closed, explainable flex-window recommendations."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from gridbridge.config import PipelineConfig


class FlexInputs(BaseModel):
    """Canonical operational and market inputs for one feeder interval."""

    model_config = ConfigDict(frozen=True)

    feeder_id: str
    interval_start_utc: datetime
    net_load_kw: float = Field(ge=0.0)
    eligible_der_kw: float = Field(ge=0.0)
    transformer_capacity_kva: float = Field(gt=0.0)
    market_price_aud_per_mwh: float
    scada_observed_at_utc: datetime
    evaluation_time_utc: datetime
    topology_valid: bool


class FlexRecommendation(BaseModel):
    """Advisory-only result with transparent block reasons and factors."""

    model_config = ConfigDict(frozen=True)

    feeder_id: str
    interval_start_utc: datetime
    status: Literal["review", "blocked", "not_economic"]
    advisory_kw: float
    score: float
    block_reasons: list[str]
    factors: dict[str, float]


def recommend_flex(inputs: FlexInputs, config: PipelineConfig) -> FlexRecommendation:
    """Gate advisory capacity on topology, freshness, transformer headroom, and price."""

    telemetry_age = max(
        0.0,
        (inputs.evaluation_time_utc - inputs.scada_observed_at_utc).total_seconds() / 60.0,
    )
    permitted_load = inputs.transformer_capacity_kva * config.transformer_loading_limit_pct / 100.0
    headroom = max(0.0, permitted_load - inputs.net_load_kw)
    factors = {
        "eligible_der_kw": round(inputs.eligible_der_kw, 3),
        "transformer_headroom_kw": round(headroom, 3),
        "market_price_aud_per_mwh": round(inputs.market_price_aud_per_mwh, 3),
        "telemetry_age_minutes": round(telemetry_age, 3),
    }
    block_reasons: list[str] = []
    if not inputs.topology_valid:
        block_reasons.append("topology_invalid")
    if telemetry_age > config.scada_freshness_minutes:
        block_reasons.append("telemetry_stale")
    if headroom <= 0:
        block_reasons.append("transformer_headroom_exhausted")
    if inputs.eligible_der_kw <= 0:
        block_reasons.append("no_eligible_der_capacity")
    if block_reasons:
        return FlexRecommendation(
            feeder_id=inputs.feeder_id,
            interval_start_utc=inputs.interval_start_utc,
            status="blocked",
            advisory_kw=0.0,
            score=0.0,
            block_reasons=block_reasons,
            factors=factors,
        )
    if inputs.market_price_aud_per_mwh < config.flex_price_threshold_aud_per_mwh:
        return FlexRecommendation(
            feeder_id=inputs.feeder_id,
            interval_start_utc=inputs.interval_start_utc,
            status="not_economic",
            advisory_kw=0.0,
            score=0.0,
            block_reasons=[],
            factors=factors,
        )
    advisory_kw = min(inputs.eligible_der_kw, headroom)
    market_signal_score = min(
        1.0,
        inputs.market_price_aud_per_mwh / (2.0 * config.flex_price_threshold_aud_per_mwh),
    )
    return FlexRecommendation(
        feeder_id=inputs.feeder_id,
        interval_start_utc=inputs.interval_start_utc,
        status="review",
        advisory_kw=round(advisory_kw, 3),
        score=round(market_signal_score, 2),
        block_reasons=[],
        factors=factors,
    )
