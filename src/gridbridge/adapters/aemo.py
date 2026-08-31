"""Optional adapter for public AEMO NEMWeb dispatch-price reports."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from datetime import date, datetime
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import polars as pl

HttpGet = Callable[[str], bytes]


class AemoMarketAdapter:
    """Parse public NEMWeb I/D/C CSV reports behind an injected HTTP boundary."""

    def __init__(self, base_url: str, http_get: HttpGet) -> None:
        self._base_url = base_url.rstrip("/")
        self._http_get = http_get

    def fetch_dispatch_prices(self, trading_date: date, report_name: str) -> pl.DataFrame:
        """Fetch one named public DispatchIS ZIP and return regional energy prices."""

        url = f"{self._base_url}/DispatchIS_Reports/{report_name}"
        return self.parse_dispatch_prices(self._http_get(url), trading_date)

    @staticmethod
    def parse_dispatch_prices(payload: bytes, trading_date: date) -> pl.DataFrame:
        """Parse DISPATCH/PRICE records from a zipped NEMWeb CSV payload."""

        output: list[dict[str, object]] = []
        with ZipFile(io.BytesIO(payload)) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(csv_names) != 1:
                raise ValueError("AEMO report ZIP must contain exactly one CSV")
            text = archive.read(csv_names[0]).decode("utf-8-sig")

        header: list[str] | None = None
        for row in csv.reader(io.StringIO(text)):
            if row[:4] == ["I", "DISPATCH", "PRICE", "3"]:
                header = row[4:]
                continue
            if row[:4] != ["D", "DISPATCH", "PRICE", "3"]:
                continue
            if header is None:
                raise ValueError("AEMO price data appeared before its information row")
            values = dict(zip(header, row[4:], strict=True))
            local_time = datetime.strptime(values["SETTLEMENTDATE"], "%Y/%m/%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("Australia/Sydney")
            )
            run_number = int(values["RUNNO"])
            region = values["REGIONID"]
            interval = values["DISPATCHINTERVAL"]
            output.append(
                {
                    "source_record_id": f"AEMO-{interval}-{region}-{run_number}",
                    "region": region,
                    "interval_start": local_time.isoformat(),
                    "price_aud_per_mwh": float(values["RRP"]),
                    "intervention": values["INTERVENTION"] == "1",
                    "revision": run_number,
                    "trading_date": trading_date,
                }
            )
        if not output:
            raise ValueError("AEMO report contained no DISPATCH/PRICE rows")
        return pl.DataFrame(output)
