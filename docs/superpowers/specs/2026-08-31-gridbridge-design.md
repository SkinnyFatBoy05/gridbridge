# GridBridge Utility Data Onboarding Control Plane

## Objective

Build a public, portfolio-grade utility data integration project that demonstrates the capabilities most relevant to 10x Labs' Data Integration Engineer role: client-style data onboarding, utility-domain source systems, high-volume time series, ETL/ELT orchestration, data-quality investigation, canonical modelling, flex-market concepts, security-conscious delivery, and lightweight distribution-network modelling.

GridBridge is a deterministic synthetic demonstration. It is not connected to operational infrastructure, does not issue control commands, and must not be presented as utility employment, a production deployment, or proof of regulatory compliance.

## Success Criteria

The finished repository must let a reviewer:

1. Run a complete onboarding demo with one CLI command after installing the project.
2. Inspect realistic meter, GIS, SCADA, DER, and market-price source contracts.
3. See deliberately messy records profiled, normalized, quarantined, and reconciled.
4. Trace source records through immutable landing manifests into canonical models and analytical marts.
5. Review an Airflow DAG that orchestrates the same independently testable pipeline stages.
6. Verify idempotent replay and safety-gated flex recommendations.
7. Generate and process at least one million interval records without committing the generated bulk data.
8. Understand the project's security controls, data mappings, operating runbook, and production-evolution path from the documentation alone.

## Chosen Approach

GridBridge is an integration-first onboarding control plane, not a lakehouse benchmark or a full power-system simulator. It borrows a reproducible scale benchmark from the lakehouse approach and feeder-topology checks from the digital-twin approach. This keeps the work aligned to a role that sits between client data teams and platform engineers while still providing credible time-series and power-domain evidence.

## System Boundary

### In scope

- Deterministic generation of synthetic utility source files and known defects.
- Batch adapters for Parquet, GeoJSON, CSV, and newline-delimited JSON.
- A REST-style JSON market-price adapter plus an optional public AEMO adapter that is disabled by default.
- Immutable landing manifests with source metadata and SHA-256 hashes.
- Profiling, contract validation, normalization, quarantine, reconciliation, and replay.
- A canonical utility model in DuckDB, transformed with dbt-core.
- Network topology validation with NetworkX.
- Interval aggregation and explainable flex-window recommendations for human review.
- A Python CLI for the fast local path and an Airflow DAG for orchestrated execution.
- Static HTML data-quality reporting.
- Automated tests, CI, documentation, and a scale benchmark.

### Out of scope

- Live SCADA, AMI, GIS, DERMS, market, or device connections.
- Operational control, switching, dispatch, or writes to field equipment.
- Full AC or unbalanced three-phase power-flow simulation.
- Forecasting or optimization that requires unverifiable performance claims.
- A hosted cloud deployment, Kubernetes, or Terraform.
- Formal ISO 27001 or NERC CIP compliance claims.
- Storage of real customer, meter, premise, credential, or critical-infrastructure data.

## Technology Choices

| Concern | Choice | Rationale |
|---|---|---|
| Language and packaging | Python 3.12 with `uv` and `pyproject.toml` | Matches the role, supports reproducible setup, and keeps the project easy to evaluate. |
| DataFrames and files | Polars and PyArrow | Efficient local processing of partitioned interval data and explicit schema handling. |
| Analytical store | DuckDB | Strong SQL and Parquet support with a zero-service local demo. |
| Transformation layer | dbt-core with dbt-duckdb | Shows modern ELT modelling, tests, documentation, and lineage. |
| Orchestration | Apache Airflow via Docker Compose | Directly demonstrates the preferred orchestration skill while leaving the CLI path fast. |
| Contracts | Pydantic models plus explicit Polars validation rules | Keeps source envelopes and row-level validation typed and testable. |
| Topology | NetworkX | Supports connectivity, orphan, path, and cycle checks without pretending to be a full power-flow engine. |
| CLI | Typer | Provides discoverable commands and a clean reviewer experience. |
| Report | Jinja2-rendered static HTML | Produces an attractive, portable result without adding a frontend application. |
| Quality | pytest, Ruff, mypy, dbt tests | Covers behaviour, contracts, style, typing, and warehouse assertions. |

## Repository Architecture

```text
gridbridge/
  airflow/dags/                 Airflow orchestration entry point
  config/                       Source contracts, mappings, and thresholds
  dbt/                          Staging, intermediate, and mart SQL models
  docs/                         Architecture, mappings, runbooks, controls, evidence
  sample_data/                  Small deterministic source fixtures only
  src/gridbridge/
    adapters/                   Source-specific readers
    canonical/                  Shared schemas and normalization
    cli.py                      Reviewer-facing command surface
    flex/                       Advisory flex-window calculations
    generators/                 Deterministic synthetic data and defect injection
    observability/              Run audit, reconciliation, and report models
    pipeline/                   Independently callable pipeline stages
    quality/                    Profiling and row/dataset validation
    security/                   Hashing, redaction, and classification helpers
    topology/                   Feeder graph validation
  tests/                        Unit, contract, integration, and end-to-end tests
  docker-compose.yml            Airflow demonstration stack
  pyproject.toml                Dependencies and tool configuration
```

Each package has one primary responsibility. Source-specific logic ends at the adapter boundary; downstream validation and transformations use canonical field names and shared result types. The CLI and Airflow DAG call the same pipeline functions, preventing orchestration logic from becoming a second implementation.

## Source Systems and Contracts

### Meter intervals

- Format: partitioned Parquet.
- Grain: meter, channel, and interval start.
- Representative fields: `meter_id`, `nmi`, `channel`, `interval_start_local`, `interval_minutes`, `energy_value`, `energy_unit`, `quality_method`.
- Injected defects: duplicate intervals, gaps, negative import readings, unsupported units, unknown meters, and a daylight-saving duplicate local time.

### GIS network model

- Format: GeoJSON feature collections for nodes and edges.
- Representative fields: `asset_id`, `asset_type`, `from_node`, `to_node`, `nominal_voltage_v`, `rated_capacity_kva`, `status`, and geometry.
- Injected defects: dangling endpoints, orphan devices, an unintended cycle, invalid voltage transitions, missing geometry, and a de-energized segment.

### SCADA telemetry

- Format: newline-delimited JSON event batches.
- Grain: point and event timestamp.
- Representative fields: `point_id`, `asset_id`, `event_time`, `value`, `unit`, `quality_code`, and `sequence_number`.
- Injected defects: out-of-order events, repeated sequence numbers, stale observations, bad-quality values, implausible ranges, and unknown assets.

### DER register

- Format: CSV.
- Grain: DER unit.
- Representative fields: `der_id`, `connection_point_id`, `technology_type`, `nameplate_value`, `nameplate_unit`, `export_limit_kw`, `phase`, and `commissioned_date`.
- Injected defects: W/kW/MW mismatches, missing connection points, export limits above nameplate capacity, invalid phase values, and duplicate registrations.

### Market prices

- Default format: bundled REST-style JSON fixture.
- Grain: region and five-minute interval.
- Representative fields: `region`, `interval_start`, `price_aud_per_mwh`, `intervention`, and `source_published_at`.
- Injected defects: missing intervals, duplicate revisions, stale publication times, and one invalid region.
- Optional adapter: public AEMO market data, isolated behind an interface and excluded from deterministic CI.

## Canonical Data Model

### Network entities

- `network_nodes`
- `network_edges`
- `substations`
- `feeders`
- `transformers`
- `connection_points`

### Customer and device entities

- `premises`
- `meters`
- `der_units`
- `scada_points`

### Time-series facts

- `meter_intervals`
- `scada_observations`
- `market_prices`

### Operational evidence

- `ingestion_runs`
- `source_manifests`
- `validation_results`
- `quarantined_records`
- `reconciliation_results`

### Analytical marts

- `feeder_interval_load`
- `der_interval_availability`
- `flex_interval_candidates`

Every canonical record carries a `run_id`, `source_system`, `source_record_id`, `source_file_hash`, and ingestion timestamp. Time-series uniqueness is enforced at its documented grain. Raw payloads are retained only in the synthetic local workspace; quarantine reporting uses redacted payload previews and stable fingerprints.

## Pipeline and Data Flow

1. `generate` creates the small synthetic source package and an expected-defect ledger.
2. `land` copies source objects into a run-scoped raw zone and writes SHA-256 manifests.
3. `profile` records schema, row counts, null rates, distinct counts, timestamp coverage, and unit distributions.
4. `validate` applies source contracts and produces valid and quarantined record sets with reason codes.
5. `normalize` converts identifiers, timestamps, quality codes, and units into canonical representations.
6. `load` writes idempotently to DuckDB staging tables using stable natural keys and payload fingerprints.
7. `transform` runs dbt staging, intermediate, and mart models plus dbt tests.
8. `validate-topology` constructs feeder graphs and writes network defects and feeder health summaries.
9. `recommend-flex` builds advisory candidates only when freshness, topology, capacity, and telemetry-quality gates pass.
10. `reconcile` compares landed, accepted, quarantined, and loaded counts by source and reason code.
11. `report` renders the static HTML data-quality and onboarding report.

The `gridbridge demo` command runs these stages in order. Airflow models them as separate tasks with explicit dependencies, retries only safe transient steps, and exposes run IDs through task context.

## Time, Unit, and Domain Rules

- Source local timestamps are interpreted in `Australia/Sydney` and stored in UTC with the original local value and offset retained for audit.
- Ambiguous or nonexistent daylight-saving local timestamps require an explicit offset or are quarantined.
- Power is normalized to kW and energy to kWh; original values and units remain traceable.
- Meter interval energy is never silently treated as instantaneous power.
- Meter facts are unique by meter, channel, and UTC interval start.
- SCADA observations with bad quality, impossible ranges, or insufficient freshness are excluded from flex calculations but retained as evidence.
- De-energized network segments remain modelled but are excluded from available paths.
- DER export limits cannot exceed normalized nameplate capacity without a documented exception.

## Topology and Flex Logic

NetworkX graphs are built per feeder from energized nodes and edges. Validation detects dangling references, orphans, disconnected components, unexpected cycles in a radial demonstration feeder, missing paths to a substation, invalid voltage transitions, and transformer-to-DER capacity concerns. These are engineering plausibility checks rather than electrical load-flow results.

Flex candidates aggregate net load, eligible DER capacity, transformer headroom, market price, and data freshness at five-minute intervals. A candidate receives a transparent score and a list of contributing factors. It is blocked when any mandatory safety gate fails. Output wording remains advisory: `review`, `blocked`, or `not_economic`; no `dispatch` command exists.

## Failure Handling, Quarantine, and Replay

Validation failures use stable reason codes such as `METER_DUPLICATE_INTERVAL`, `TIMESTAMP_DST_AMBIGUOUS`, `SCADA_BAD_QUALITY`, `DER_UNIT_UNSUPPORTED`, and `GIS_DANGLING_NODE`. Each quarantine row stores the run, source, source record identifier where available, reason code, human-readable detail, redacted preview, and payload fingerprint.

A run fails closed if a source contract cannot be parsed, manifests do not match, reconciliation does not balance, dbt tests fail, or mandatory topology/freshness gates fail. Row-level defects within configured tolerances can complete the onboarding run with a degraded status. Tolerances are configuration, not hard-coded exceptions.

Reprocessing the same landed input is idempotent. A replay references the original manifest, applies corrected mapping or source data, and records its parent run. Stable natural keys and fingerprints prevent duplicate canonical facts while preserving an audit trail of both attempts.

## Security and Regulated-Environment Evidence

The repository will document controls inspired by ISO 27001 and NERC CIP practices without asserting compliance:

- Least-privilege role matrix for source uploader, pipeline operator, reviewer, and administrator.
- No committed credentials; environment variables and example secret names only.
- Synthetic-only public fixtures and explicit data classification labels.
- Immutable hashes and reconciliation for source integrity.
- Structured audit events for run, mapping, validation, replay, and configuration changes.
- Redaction helpers for identifiers in logs and HTML reports.
- Dependency pinning, automated dependency review, secret scanning, and container scanning where reliable.
- Change control through pull requests, CI gates, mapping versioning, and architecture decision records.
- Retention and incident-response guidance in the operating runbook.
- A documented production evolution that separates orchestration, storage, and operational networks.

## Testing Strategy

### Unit tests

- Unit and timestamp normalization, including daylight-saving ambiguity.
- Stable hashing, redaction, reason codes, scoring, and safety gates.
- Topology checks for paths, orphans, cycles, and disconnected components.

### Contract tests

- Accepted source schemas and representative invalid records for all five adapters.
- Mapping configuration validation and rejection of unknown required fields.

### Integration tests

- Valid/quarantine splits, DuckDB loading, idempotent reruns, dbt models, and reconciliation.
- Airflow DAG import and task dependency assertions without requiring a running scheduler.

### End-to-end test

- Generate the small fixture, run the complete onboarding pipeline, assert expected row counts and reason codes, and render the report.

### Scale benchmark

- Deterministically generate at least one million interval records outside version control.
- Record machine context, elapsed time, throughput, accepted/quarantined counts, warehouse size, and representative analytical query time.
- Treat benchmark numbers as local observations, not universal performance claims.

## CI and Quality Gates

GitHub Actions will run on pushes and pull requests:

1. Ruff formatting and lint checks.
2. mypy type checking for the production package.
3. pytest unit, contract, integration, and end-to-end suites.
4. dbt model parsing and tests against an ephemeral DuckDB database.
5. Airflow DAG import validation using the project's supported environment.
6. Dependency review on pull requests and secret scanning through repository-native controls where available.
7. Docker build and a lightweight vulnerability scan if it remains deterministic and does not make normal contributions brittle.

The README may claim a passing check only after the corresponding workflow and local verification succeed.

## Reviewer Experience and Documentation

The README leads with the role-relevant outcome, a report screenshot, an architecture diagram, a five-minute quick start, and a defect-to-resolution walkthrough. Supporting documents include:

- Architecture and lineage diagrams.
- Source-to-target mapping specification.
- Canonical data dictionary.
- Client onboarding questionnaire and discovery checklist.
- Data-quality reason-code catalogue.
- Operator runbook with replay and incident scenarios.
- Security control mapping and threat boundaries.
- Benchmark method and reproducible results.
- Production-evolution notes.
- Interview talking points that distinguish what is implemented from what is simulated.

The generated HTML report includes run status, source health, row reconciliation, quarantine trends, unit and freshness issues, topology defects, and flex candidates with block reasons. It must work as a standalone file and expose no external analytics or tracking.

## Delivery Sequence

1. Establish packaging, configuration, shared run models, and deterministic source generation.
2. Implement adapters, contracts, profiling, normalization, quarantine, and reconciliation using tests first.
3. Add the DuckDB canonical layer and dbt transformations/tests.
4. Add topology validation and advisory flex logic with safety-gate tests.
5. Compose the CLI pipeline and prove idempotent replay end to end.
6. Add Airflow orchestration and Docker Compose.
7. Build the HTML report and reviewer-facing documentation.
8. Run the scale benchmark, security/quality checks, and full verification.
9. Create the public GitHub repository under `SkinnyFatBoy05`, push `main`, and verify repository rendering and Actions status.

## Acceptance Criteria

- `gridbridge demo` produces a successful or explicitly degraded run, balanced reconciliation, DuckDB warehouse, and standalone HTML report from a clean workspace.
- The expected synthetic defects appear under stable quarantine reason codes.
- Re-running identical inputs does not duplicate canonical facts.
- Corrected data can be replayed with a recorded parent run.
- Flex recommendations are blocked under stale telemetry, invalid topology, or failed capacity gates.
- dbt and pytest suites pass, Airflow DAG imports cleanly, and CI reflects those checks.
- The million-row benchmark completes and records reproducible methodology and honest local results.
- Documentation covers mapping, onboarding, operation, security, and production evolution.
- No credentials, real utility data, personal customer data, or unsupported compliance/production claims enter the repository.
- The public GitHub repository is readable, runnable, and clearly aligned to a utility data integration role.
