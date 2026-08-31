# Interview Talking Points

## Thirty-second version

“I built GridBridge to practise the hardest part of utility platforms: onboarding heterogeneous external data with evidence. It ingests meter Parquet, GIS GeoJSON, SCADA events, DER CSV and market JSON; profiles and quarantines defects; normalizes DST and units; loads idempotently into DuckDB; transforms with dbt; validates feeder topology; and blocks flex advice when topology, telemetry or capacity is unsafe. The demo reconciles 302 rows exactly and the separate benchmark processes one million intervals.”

## Decisions worth discussing

- **Synthetic over scraped customer data:** reproducible, privacy-safe and lets known failures become regression tests.
- **DuckDB for the reviewer path:** demonstrates SQL/Parquet/dbt without requiring cloud credentials; production evolution is documented.
- **Airflow stays thin:** CLI and DAG invoke the same pipeline entry point, preventing scheduler-specific business logic.
- **Quarantine rather than drop:** a rejected record is still an operational fact with a source hash, payload fingerprint and reason.
- **Refuse unit/time guesses:** MVA is not silently converted to kW; repeated Sydney DST time requires an offset.
- **Flex is advisory:** `review`, `blocked` and `not_economic` states are explicit, and topology/freshness/capacity gates fail closed.

## Honest boundaries

- All included data is synthetic.
- The AEMO adapter is implemented and fixture-tested but not used by deterministic CI.
- NetworkX checks topology plausibility; this is not AC or three-phase power flow.
- The million-row result is a local observation from a generated Parquet/DuckDB path, not a production SLA.
- Security documentation is control-inspired, not a certification or compliance assessment.
- There is no live SCADA, meter, DERMS, GIS, market or device connection.

## Client scenario

If a client says “the spreadsheet is the source of truth,” start with grain, ownership, revision semantics and acceptance evidence. Land it unchanged, hash it, profile it, map it explicitly, quarantine rather than delete exceptions, reconcile counts, and make the unresolved questions visible with owners. Automate only after the manual decisions are understood and versioned.

