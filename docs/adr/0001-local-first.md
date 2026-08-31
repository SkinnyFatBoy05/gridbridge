# ADR 0001: Local-First Reviewer Architecture

- Status: accepted
- Date: 2026-08-31

## Context

The portfolio must demonstrate utility integration and orchestration while remaining runnable without cloud credentials or access to real infrastructure.

## Decision

Use DuckDB, Parquet, dbt and a Python CLI for the zero-service path. Provide an Airflow Docker Compose path over the same pipeline. Keep cloud deployment as documented evolution rather than unverified infrastructure code.

## Consequences

Reviewers can reproduce the core system quickly and inspect SQL, lineage and defects. The repository does not demonstrate a live managed-cloud deployment, distributed transaction model or operational SLA; those boundaries are stated explicitly.

