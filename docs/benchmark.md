# Million-Row Time-Series Benchmark

## Recorded result

Run on 31 August 2026 with Python 3.12.10 on Windows 11 and an AMD64 Family 25 Model 68 processor:

| Observation | Result |
|---|---:|
| Deterministic interval rows | 1,000,000 |
| Accepted / quarantined | 1,000,000 / 0 |
| Parquet generation | 0.6084 s |
| DuckDB contract load | 0.7995 s |
| Observed load throughput | 1,250,821 rows/s |
| Feeder/day aggregation | 182.07 ms |
| Parquet size | 60,272 bytes |
| DuckDB size | 12,070,912 bytes |

These numbers are local observations, not a universal performance claim or production SLA. The synthetic values are highly compressible, the machine was not isolated, and the benchmark does not include network transfer, encryption, Airflow scheduling, row-by-row quarantine persistence or cloud-storage latency.

## Method

1. DuckDB generates stable meter IDs across eight feeders and 288 five-minute positions per meter.
2. Energy values use a seeded deterministic expression.
3. Data is written to Zstandard-compressed Parquet with 100,000-row groups.
4. The load applies required-field, channel, cadence and non-negative-energy contract predicates.
5. A DuckDB table is materialized from accepted rows.
6. The representative query groups kWh and interval-average kW by feeder and day.
7. The command records Python, OS, processor, file sizes and timing as JSON beside ignored runtime files.

## Reproduce

```bash
uv run gridbridge benchmark --rows 1000000 --output work/benchmark --seed 42
```

Bulk Parquet, DuckDB and JSON runtime evidence stays under ignored `work/`. Commit only reviewed, machine-contextualized observations such as this document.

