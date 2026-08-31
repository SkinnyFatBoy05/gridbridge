# Operator and Replay Runbook

## Normal run

```bash
uv run gridbridge demo --workspace work/demo
```

1. Record the printed run ID.
2. Open the HTML report and confirm the synthetic/advisory banner.
3. Check `reconciliation: balanced` and source row counts.
4. Review quarantine reason codes and source manifests in DuckDB.
5. Confirm dbt passed, inspect topology issues, then review flex statuses.
6. Treat `degraded` as expected only when explained defects are inside the agreed tolerance.

Useful read-only queries:

```sql
select * from ingestion_runs order by started_at_utc desc;
select source, reason_code, count(*) from quarantined_records group by 1, 2 order by 1, 2;
select * from reconciliation_results where run_id = '<run-id>';
select * from fct_flex_interval_candidates order by interval_start_utc;
```

## Remediate and replay

1. Preserve the original run ID, report and manifest hash.
2. Correct the synthetic source under `work/demo/source_data` or update a versioned mapping.
3. Add or update a regression test for the corrected rule.
4. Run:

```bash
uv run gridbridge replay --workspace work/demo --parent-run-id <run-id>
```

5. Confirm the new `ingestion_runs.parent_run_id` equals the original run.
6. Compare inserted/updated/unchanged counts. Corrected natural keys should report `updated`; identical facts should report `unchanged`.
7. Do not remove the earlier quarantine or report; they describe what was known at that time.

## Fail-closed conditions

- A source cannot be parsed under its contract.
- A required config value is invalid.
- Landed rows do not equal accepted plus quarantined.
- Accepted rows do not equal loaded effects.
- A dbt model or assertion fails.
- No accepted `GOOD` SCADA observation exists for operational gating.

The run begins in `failed` state and changes only after all mandatory stages complete. A topology defect creates a degraded run and blocks flex advice.

## Incident handling

For suspected credential, real-data or integrity exposure: stop runs; isolate the workspace; preserve logs, source hashes and run metadata; rotate affected credentials outside GridBridge; notify the named system/data/security owners; document scope and timestamps; and use synthetic data for reproduction. Do not paste sensitive utility data into a public issue.

## Retention

This repository ships no production retention policy. A deployment must define retention separately for raw source objects, accepted canonical rows, quarantine payloads, reports, audit logs and backups according to the client's classification and legal obligations.

