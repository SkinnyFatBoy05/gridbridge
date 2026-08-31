"""Transactional DuckDB persistence with natural-key idempotency."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path

import duckdb
import polars as pl

from gridbridge.models import LoadResult, QuarantineRecord

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"unsafe SQL identifier: {value}")
    return f'"{value}"'


def _payload_fingerprint(row: dict[str, object]) -> str:
    payload = json.dumps(row, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _count(connection: duckdb.DuckDBPyConnection, query: str) -> int:
    row = connection.execute(query).fetchone()
    if row is None:
        raise RuntimeError("count query returned no row")
    return int(row[0])


class Warehouse:
    """Own the local analytical warehouse and operational evidence tables."""

    def __init__(self, path: Path, run_id: str = "standalone") -> None:
        self.path = path
        self.run_id = run_id

    def initialize(self) -> None:
        """Create operational evidence tables without changing existing facts."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(self.path)) as connection:
            connection.execute(
                """
                create table if not exists ingestion_runs (
                    run_id varchar primary key,
                    parent_run_id varchar,
                    status varchar not null,
                    started_at_utc timestamptz not null,
                    completed_at_utc timestamptz
                );
                create table if not exists source_manifests (
                    run_id varchar not null,
                    source varchar not null,
                    file_name varchar not null,
                    sha256 varchar not null,
                    size_bytes bigint not null,
                    landed_at_utc timestamptz not null,
                    primary key (run_id, source, file_name)
                );
                create table if not exists quarantined_records (
                    run_id varchar not null,
                    source varchar not null,
                    source_record_id varchar not null,
                    reason_code varchar not null,
                    detail varchar not null,
                    payload_preview varchar not null,
                    payload_fingerprint varchar not null,
                    source_file_hash varchar not null,
                    primary key (
                        run_id, source, source_record_id, reason_code, payload_fingerprint
                    )
                );
                create table if not exists reconciliation_results (
                    run_id varchar not null,
                    source varchar not null,
                    landed bigint not null,
                    accepted bigint not null,
                    quarantined bigint not null,
                    loaded bigint not null,
                    balanced boolean not null,
                    primary key (run_id, source)
                );
                """
            )

    def _table_exists(self, connection: duckdb.DuckDBPyConnection, table: str) -> bool:
        result = connection.execute(
            "select count(*) from information_schema.tables where table_name = ?",
            [table],
        ).fetchone()
        return bool(result and result[0])

    def load_frame(
        self,
        table: str,
        frame: pl.DataFrame,
        natural_keys: tuple[str, ...],
    ) -> LoadResult:
        """Insert new facts, update corrected payloads, and count identical replays."""

        if frame.is_empty():
            return LoadResult(inserted=0, updated=0, unchanged=0)
        missing = set(natural_keys) - set(frame.columns)
        if missing:
            raise ValueError(f"natural keys missing from {table}: {sorted(missing)}")
        table_sql = _safe_identifier(table)
        key_sql = " and ".join(
            f"t.{_safe_identifier(key)} is not distinct from i.{_safe_identifier(key)}"
            for key in natural_keys
        )
        fingerprints = [_payload_fingerprint(row) for row in frame.to_dicts()]
        incoming = frame.with_columns(
            pl.Series("_payload_fingerprint", fingerprints, dtype=pl.String),
            pl.lit(self.run_id).alias("_run_id"),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(self.path)) as connection:
            connection.register("_incoming", incoming.to_arrow())
            if not self._table_exists(connection, table):
                connection.execute(
                    f"create table {table_sql} as select * from _incoming where false"
                )
            unchanged = _count(
                connection,
                f"""
                    select count(*) from _incoming i join {table_sql} t on {key_sql}
                    where t._payload_fingerprint = i._payload_fingerprint
                    """,
            )
            updated = _count(
                connection,
                f"""
                    select count(*) from _incoming i join {table_sql} t on {key_sql}
                    where t._payload_fingerprint <> i._payload_fingerprint
                    """,
            )
            inserted = _count(
                connection,
                f"""
                    select count(*) from _incoming i
                    where not exists (select 1 from {table_sql} t where {key_sql})
                    """,
            )
            connection.execute("begin transaction")
            try:
                connection.execute(
                    f"""
                    delete from {table_sql} as t using _incoming as i
                    where {key_sql} and t._payload_fingerprint <> i._payload_fingerprint
                    """
                )
                connection.execute(
                    f"""
                    insert into {table_sql}
                    select i.* from _incoming i
                    where not exists (select 1 from {table_sql} t where {key_sql})
                    """
                )
                connection.execute("commit")
            except Exception:
                connection.execute("rollback")
                raise
            finally:
                connection.unregister("_incoming")
        return LoadResult(inserted=inserted, updated=updated, unchanged=unchanged)

    def record_quarantine(self, records: Sequence[QuarantineRecord]) -> int:
        """Persist quarantine evidence once per run, reason, and payload."""

        if not records:
            return 0
        self.initialize()
        rows = [
            (
                record.run_id,
                record.source.value,
                record.source_record_id,
                record.reason_code.value,
                record.detail,
                record.payload_preview,
                record.payload_fingerprint,
                record.source_file_hash,
            )
            for record in records
        ]
        with duckdb.connect(str(self.path)) as connection:
            before = _count(connection, "select count(*) from quarantined_records")
            connection.executemany(
                """
                insert or ignore into quarantined_records values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            after = _count(connection, "select count(*) from quarantined_records")
        return after - before
