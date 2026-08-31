from pathlib import Path

import pytest

from gridbridge.config import load_config


def test_load_config_rejects_non_positive_scada_freshness(tmp_path: Path) -> None:
    """A zero-minute freshness window would make every SCADA point stale."""
    config_path = tmp_path / "pipeline.yml"
    config_path.write_text("scada_freshness_minutes: 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="scada_freshness_minutes"):
        load_config(config_path)


def test_load_config_uses_utility_domain_defaults(tmp_path: Path) -> None:
    """Omitted settings retain the agreed Sydney and advisory defaults."""
    config_path = tmp_path / "pipeline.yml"
    config_path.write_text("{}\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.timezone == "Australia/Sydney"
    assert config.scada_freshness_minutes == 15
    assert config.flex_price_threshold_aud_per_mwh == 150.0
