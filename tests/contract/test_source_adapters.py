import csv
import io
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import polars as pl
import pytest

from gridbridge.adapters.aemo import AemoMarketAdapter
from gridbridge.adapters.readers import read_source
from gridbridge.generators.sources import generate_sources
from gridbridge.models import SourceName


@pytest.fixture
def generated_sources(tmp_path: Path) -> dict[SourceName, list[Path]]:
    return generate_sources(tmp_path, seed=42, meter_rows=288)


@pytest.mark.parametrize(
    ("source", "required_column"),
    [
        (SourceName.METER, "meter_id"),
        (SourceName.GIS, "asset_id"),
        (SourceName.SCADA, "point_id"),
        (SourceName.DER, "der_id"),
        (SourceName.MARKET, "price_aud_per_mwh"),
    ],
)
def test_read_source_exposes_source_contract(
    generated_sources: dict[SourceName, list[Path]],
    source: SourceName,
    required_column: str,
) -> None:
    """A format adapter must expose domain fields instead of opaque payloads."""
    frame = read_source(source, generated_sources[source])

    assert isinstance(frame, pl.DataFrame)
    assert frame.height > 0
    assert required_column in frame.columns
    assert "source_record_id" in frame.columns


def _dispatch_zip() -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        csv_buffer = io.StringIO(newline="")
        writer = csv.writer(csv_buffer, lineterminator="\n")
        writer.writerow(
            [
                "I",
                "DISPATCH",
                "PRICE",
                "3",
                "SETTLEMENTDATE",
                "RUNNO",
                "REGIONID",
                "DISPATCHINTERVAL",
                "RRP",
                "INTERVENTION",
            ]
        )
        writer.writerow(
            [
                "D",
                "DISPATCH",
                "PRICE",
                "3",
                "2026/08/31 00:05:00",
                "1",
                "NSW1",
                "20260831001",
                "82.40",
                "0",
            ]
        )
        writer.writerow(["C", "END OF REPORT", "1"])
        archive.writestr("PUBLIC_DISPATCHIS_SAMPLE.CSV", csv_buffer.getvalue())
    return buffer.getvalue()


def test_aemo_adapter_parses_nemweb_dispatch_price_rows() -> None:
    """AEMO's I/D/C CSV envelope must become the same market contract as fixtures."""
    requested_urls: list[str] = []

    def http_get(url: str) -> bytes:
        requested_urls.append(url)
        return _dispatch_zip()

    adapter = AemoMarketAdapter("https://www.nemweb.com.au/Reports/CURRENT", http_get)
    frame = adapter.fetch_dispatch_prices(date(2026, 8, 31), "sample.zip")

    assert requested_urls == [
        "https://www.nemweb.com.au/Reports/CURRENT/DispatchIS_Reports/sample.zip"
    ]
    assert frame.to_dicts() == [
        {
            "source_record_id": "AEMO-20260831001-NSW1-1",
            "region": "NSW1",
            "interval_start": "2026-08-31T00:05:00+10:00",
            "price_aud_per_mwh": 82.4,
            "intervention": False,
            "revision": 1,
            "trading_date": date(2026, 8, 31),
        }
    ]
