# Canonical Data Dictionary

## Operational evidence

| Table | Grain | Purpose |
|---|---|---|
| `ingestion_runs` | One row per run | Status, timestamps and parent replay lineage |
| `source_manifests` | Run/source/file | File name, byte count, SHA-256 and landing time |
| `quarantined_records` | Run/source/record/reason/payload | Lossless exception evidence with redacted preview |
| `reconciliation_results` | Run/source | Landed, accepted, quarantined, loaded and balanced flag |

## Canonical source tables

| Table | Grain | Important fields |
|---|---|---|
| `meter_intervals` | Meter/channel/UTC interval | NMI, connection point, feeder, interval minutes, source value/unit, `energy_kwh` |
| `network_assets` | Asset | Type, nodes, voltage, capacity, status, geometry JSON |
| `scada_observations` | Point/UTC event/sequence | Asset, quality, source value/unit, `power_kw` |
| `der_units` | DER unit | Connection point, feeder, technology, nameplate kW, export limit kW, phase |
| `market_prices` | Region/UTC interval/revision | A$/MWh, intervention and publication time |

All canonical tables add `_run_id` and `_payload_fingerprint`. Accepted source frames also carry `source_system`, `source_record_id` and `source_file_hash`.

## dbt relations

| Relation | Grain | Calculation |
|---|---|---|
| `stg_meter_intervals` | Meter/channel/interval | Typed canonical interval fields |
| `stg_scada_observations` | Point/event/sequence | Accepted, normalized telemetry |
| `stg_der_units` | DER unit | Feeder and eligible capacity inputs |
| `stg_market_prices` | Region/interval | Latest revision by row number |
| `int_feeder_interval_load` | Feeder/interval | Sum kWh and interval-average kW |
| `int_der_capacity` | Feeder | Nameplate and export-limited eligible kW |
| `fct_flex_interval_candidates` | Feeder/market interval | Load, DER capacity, region and price for safety gating |

