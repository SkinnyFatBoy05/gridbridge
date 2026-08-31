"""Validated pipeline configuration."""

from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, Field, field_validator


class PipelineConfig(BaseModel):
    """Runtime thresholds shared by CLI and Airflow execution paths."""

    timezone: str = "Australia/Sydney"
    scada_freshness_minutes: int = Field(default=15, gt=0)
    quarantine_tolerance_pct: float = Field(default=20.0, ge=0.0, le=100.0)
    flex_price_threshold_aud_per_mwh: float = 150.0
    transformer_loading_limit_pct: float = Field(default=90.0, gt=0.0, le=100.0)

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown IANA timezone: {value}") from exc
        return value


def load_config(path: Path) -> PipelineConfig:
    """Load a YAML configuration file and validate all domain thresholds."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("pipeline configuration must be a YAML mapping")
    return PipelineConfig.model_validate(payload)
