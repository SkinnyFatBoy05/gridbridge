"""Read client source formats into tabular onboarding contracts."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from gridbridge.models import SourceName


def _read_gis(paths: list[Path]) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for path in paths:
        collection = json.loads(path.read_text(encoding="utf-8"))
        for feature in collection["features"]:
            properties = dict(feature["properties"])
            properties["source_record_id"] = properties.get("asset_id")
            properties["geometry_json"] = json.dumps(
                feature.get("geometry"), sort_keys=True, separators=(",", ":")
            )
            rows.append(properties)
    return pl.DataFrame(rows)


def _read_market(paths: list[Path]) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for index, item in enumerate(payload["data"], start=1):
            row = dict(item)
            row["source_record_id"] = (
                f"MARKET-{row['region']}-{row['interval_start']}-{row.get('revision', index)}"
            )
            row["source_published_at"] = payload["published_at"]
            rows.append(row)
    return pl.DataFrame(rows)


def read_source(source: SourceName, paths: list[Path]) -> pl.DataFrame:
    """Read one logical source drop with an explicit format per source."""

    if not paths:
        raise ValueError(f"no paths supplied for {source.value}")
    if source is SourceName.METER:
        return pl.concat([pl.read_parquet(path) for path in paths], how="diagonal_relaxed")
    if source is SourceName.GIS:
        return _read_gis(paths)
    if source is SourceName.SCADA:
        return pl.concat([pl.read_ndjson(path) for path in paths], how="diagonal_relaxed")
    if source is SourceName.DER:
        return pl.concat([pl.read_csv(path) for path in paths], how="diagonal_relaxed")
    if source is SourceName.MARKET:
        return _read_market(paths)
    raise ValueError(f"unsupported source: {source}")
