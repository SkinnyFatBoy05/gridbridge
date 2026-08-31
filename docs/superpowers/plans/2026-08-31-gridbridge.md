# GridBridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a one-command synthetic utility data onboarding control plane covering meter, GIS, SCADA, DER, market, time-series scale, Airflow orchestration, flex advisory logic, and security-conscious delivery.

**Architecture:** Source adapters convert five deterministic input formats into typed records and validation outcomes. Shared pipeline stages land, profile, validate, normalize, load, transform, reconcile, assess topology, gate flex candidates, and render a standalone report; the Typer CLI and Airflow DAG call the same stage functions. DuckDB and dbt provide the SQL layer, while every run retains manifests, lineage, quarantine reason codes, and replay metadata.

**Tech Stack:** Python 3.12, uv, Polars, PyArrow, DuckDB, dbt-core/dbt-duckdb, Pydantic, NetworkX, Typer, Jinja2, Apache Airflow, pytest, Ruff, mypy, Docker Compose, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-31-gridbridge-design.md`

## Global Constraints

- The repository contains deterministic synthetic data only and never claims production utility operation, utility employment, live control capability, ISO 27001 certification, or NERC CIP compliance.
- `gridbridge demo` must run from a clean checkout without Docker after the core dependencies are installed.
- The Airflow DAG must call the same pipeline functions as the CLI.
- Source local time is interpreted in `Australia/Sydney`; canonical time is UTC; canonical power is kW; canonical energy is kWh.
- Every accepted or quarantined row must be traceable to a run, source, source record, and source file hash.
- Reruns of identical inputs must be idempotent, and replays must record their parent run.
- Flex output is advisory and must fail closed on topology, freshness, data-quality, or capacity gate failures.
- Generated million-row benchmark data and runtime artifacts must stay outside version control.
- Use focused modules with one primary responsibility and public functions typed with Python 3.12 annotations.

## File Map

```text
pyproject.toml                         Packaging, commands, dependencies, quality tools
.gitignore                            Runtime and generated-data exclusions
.env.example                          Non-secret local configuration names
src/gridbridge/models.py              Shared enums and immutable result models
src/gridbridge/config.py              YAML configuration loader and validation
src/gridbridge/generators/sources.py  Deterministic five-source fixture generation
src/gridbridge/adapters/*.py          Format-specific source readers
src/gridbridge/adapters/aemo.py       Optional public AEMO market adapter
src/gridbridge/quality/profile.py     Dataset-level profiling
src/gridbridge/quality/validate.py    Source validation and quarantine outcomes
src/gridbridge/canonical/normalize.py Timestamp, unit, and canonical row normalization
src/gridbridge/security/evidence.py   SHA-256, identifier redaction, manifests
src/gridbridge/pipeline/warehouse.py  DuckDB schema and idempotent loading
src/gridbridge/pipeline/run.py        Stage composition, audit, replay, reconciliation
src/gridbridge/topology/validate.py   Feeder graph validation
src/gridbridge/flex/recommend.py      Safety-gated advisory candidate generation
src/gridbridge/report/render.py       Standalone HTML report renderer
src/gridbridge/benchmark.py           Million-row deterministic benchmark
src/gridbridge/cli.py                 Typer command surface
dbt/models/**                         Staging, intermediate, and mart SQL models
airflow/dags/gridbridge_onboarding.py Airflow DAG over shared commands
config/**                             Contracts, mappings, and thresholds
sample_data/**                        Small generated fixture committed for review
tests/**                              Unit, contract, integration, E2E, DAG, and docs tests
docs/**                               Mapping, data dictionary, runbooks, controls, diagrams
.github/workflows/ci.yml              Pull-request and push verification
docker-compose.yml                    Local Airflow stack
Dockerfile                            Reproducible project image
README.md                             Reviewer-facing portfolio story and quick start
```

---

### Task 1: Project Foundation, Shared Models, and Synthetic Sources

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/gridbridge/__init__.py`
- Create: `src/gridbridge/models.py`
- Create: `src/gridbridge/config.py`
- Create: `src/gridbridge/generators/__init__.py`
- Create: `src/gridbridge/generators/sources.py`
- Create: `config/pipeline.yml`
- Test: `tests/unit/test_generators.py`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Produces: `SourceName`, `RunStatus`, `ReasonCode`, `QuarantineRecord`, `SourceManifest`, `PipelineConfig`, `load_config(path: Path) -> PipelineConfig`, and `generate_sources(output_dir: Path, seed: int = 42, meter_rows: int = 288) -> dict[SourceName, list[Path]]`.

- [ ] **Step 1: Write failing generator and configuration tests**

```python
def test_generate_sources_is_deterministic(tmp_path: Path) -> None:
    first = generate_sources(tmp_path / "first", seed=42)
    second = generate_sources(tmp_path / "second", seed=42)
    assert {p.name: sha256_file(p) for paths in first.values() for p in paths} == {
        p.name: sha256_file(p) for paths in second.values() for p in paths
    }

def test_load_config_rejects_non_positive_freshness(tmp_path: Path) -> None:
    path = tmp_path / "pipeline.yml"
    path.write_text("scada_freshness_minutes: 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="scada_freshness_minutes"):
        load_config(path)
```

- [ ] **Step 2: Run tests and verify missing-module failures**

Run: `uv run pytest tests/unit/test_generators.py tests/unit/test_config.py -v`
Expected: collection fails because `gridbridge.generators.sources` and `gridbridge.config` do not exist.

- [ ] **Step 3: Implement packaging, typed models, validated configuration, and deterministic generation**

```python
class SourceName(StrEnum):
    METER = "meter"
    GIS = "gis"
    SCADA = "scada"
    DER = "der"
    MARKET = "market"

class ReasonCode(StrEnum):
    METER_DUPLICATE_INTERVAL = "METER_DUPLICATE_INTERVAL"
    TIMESTAMP_DST_AMBIGUOUS = "TIMESTAMP_DST_AMBIGUOUS"
    SCADA_BAD_QUALITY = "SCADA_BAD_QUALITY"
    DER_UNIT_UNSUPPORTED = "DER_UNIT_UNSUPPORTED"
    GIS_DANGLING_NODE = "GIS_DANGLING_NODE"

class PipelineConfig(BaseModel):
    timezone: str = "Australia/Sydney"
    scada_freshness_minutes: int = Field(default=15, gt=0)
    quarantine_tolerance_pct: float = Field(default=20.0, ge=0, le=100)
    flex_price_threshold_aud_per_mwh: float = 150.0
```

Generate the five formats with stable sorting, timestamps, identifiers, and a checked-in `expected_defects.json`. Include at least one defect from each source category specified in the design.

- [ ] **Step 4: Run unit tests and quality checks**

Run: `uv run pytest tests/unit/test_generators.py tests/unit/test_config.py -v && uv run ruff check src tests`
Expected: all selected tests pass and Ruff reports no errors.

- [ ] **Step 5: Commit foundation**

```bash
git add pyproject.toml .gitignore .env.example src/gridbridge config tests/unit
git commit -m "feat: add deterministic utility source contracts"
```

### Task 2: Security Evidence, Adapters, Profiling, Validation, and Normalization

**Files:**
- Create: `src/gridbridge/security/__init__.py`
- Create: `src/gridbridge/security/evidence.py`
- Create: `src/gridbridge/adapters/__init__.py`
- Create: `src/gridbridge/adapters/readers.py`
- Create: `src/gridbridge/adapters/aemo.py`
- Create: `src/gridbridge/quality/__init__.py`
- Create: `src/gridbridge/quality/profile.py`
- Create: `src/gridbridge/quality/validate.py`
- Create: `src/gridbridge/canonical/__init__.py`
- Create: `src/gridbridge/canonical/normalize.py`
- Create: `config/source_mappings.yml`
- Test: `tests/unit/test_security_evidence.py`
- Test: `tests/contract/test_source_adapters.py`
- Test: `tests/unit/test_normalize.py`
- Test: `tests/unit/test_validation.py`

**Interfaces:**
- Consumes: `SourceName`, `ReasonCode`, `QuarantineRecord`, and generated source paths from Task 1.
- Produces: `sha256_file(path: Path) -> str`, `redact_identifier(value: str) -> str`, `build_manifest(path: Path, source: SourceName, run_id: str) -> SourceManifest`, `read_source(source: SourceName, paths: list[Path]) -> pl.DataFrame`, `profile_frame(source: SourceName, frame: pl.DataFrame) -> DatasetProfile`, `validate_source(source: SourceName, frame: pl.DataFrame, manifest: SourceManifest) -> ValidationOutcome`, `normalize_source(source: SourceName, frame: pl.DataFrame, timezone: str) -> pl.DataFrame`.
- Produces: `AemoMarketAdapter(base_url: str, http_get: HttpGet)`, whose `fetch_dispatch_prices(trading_date: date) -> pl.DataFrame` parses public data without entering the deterministic demo path.

- [ ] **Step 1: Write failing evidence, adapter, validation, and normalization tests**

```python
def test_normalize_power_to_kw() -> None:
    assert normalize_power(2.5, "MW") == 2500.0
    assert normalize_power(800.0, "W") == 0.8

def test_bad_scada_quality_is_quarantined(manifest: SourceManifest) -> None:
    frame = pl.DataFrame({"point_id": ["P1"], "quality_code": ["BAD"]})
    outcome = validate_source(SourceName.SCADA, frame, manifest)
    assert outcome.quarantined[0].reason_code is ReasonCode.SCADA_BAD_QUALITY

def test_aemo_adapter_uses_injected_http_client(fixture_zip: bytes) -> None:
    adapter = AemoMarketAdapter("https://example.invalid", lambda _: fixture_zip)
    frame = adapter.fetch_dispatch_prices(date(2026, 8, 31))
    assert frame.select("region").to_series().to_list() == ["NSW1"]
```

- [ ] **Step 2: Run tests and verify expected failures**

Run: `uv run pytest tests/unit/test_security_evidence.py tests/contract/test_source_adapters.py tests/unit/test_normalize.py tests/unit/test_validation.py -v`
Expected: collection fails for missing adapter, validation, and normalization modules.

- [ ] **Step 3: Implement readers, manifests, profiles, row validation, and canonical conversion**

```python
def normalize_power(value: float, unit: str) -> float:
    factors = {"W": 0.001, "kW": 1.0, "MW": 1000.0}
    try:
        return value * factors[unit]
    except KeyError as exc:
        raise UnsupportedUnitError(unit) from exc

def redact_identifier(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
    return f"redacted:{digest}"
```

Validation must split valid rows from quarantined rows without dropping evidence. Profiles must capture row count, columns, null counts, distinct counts, and timestamp ranges. Timestamp normalization must reject ambiguous local times without offsets.

- [ ] **Step 4: Run focused and full tests**

Run: `uv run pytest tests/unit tests/contract -v`
Expected: all unit and contract tests pass.

- [ ] **Step 5: Commit source onboarding primitives**

```bash
git add src/gridbridge config/source_mappings.yml tests
git commit -m "feat: validate and normalize utility source data"
```

### Task 3: DuckDB Warehouse, Idempotent Loads, and Reconciliation

**Files:**
- Create: `src/gridbridge/pipeline/__init__.py`
- Create: `src/gridbridge/pipeline/warehouse.py`
- Create: `src/gridbridge/pipeline/reconcile.py`
- Test: `tests/integration/test_warehouse.py`
- Test: `tests/integration/test_reconciliation.py`

**Interfaces:**
- Consumes: normalized Polars frames, manifests, validation outcomes, and run IDs.
- Produces: `Warehouse(path: Path)`, `Warehouse.initialize() -> None`, `Warehouse.load_frame(table: str, frame: pl.DataFrame, natural_keys: tuple[str, ...]) -> LoadResult`, `Warehouse.record_quarantine(records: Sequence[QuarantineRecord]) -> int`, and `reconcile_source(source: SourceName, landed: int, accepted: int, quarantined: int, loaded: int) -> ReconciliationResult`.

- [ ] **Step 1: Write failing idempotency and reconciliation tests**

```python
def test_load_frame_is_idempotent(tmp_path: Path) -> None:
    warehouse = Warehouse(tmp_path / "gridbridge.duckdb")
    warehouse.initialize()
    frame = pl.DataFrame({"meter_id": ["M1"], "interval_start_utc": [datetime(2026, 1, 1, tzinfo=UTC)]})
    assert warehouse.load_frame("meter_intervals", frame, ("meter_id", "interval_start_utc")).inserted == 1
    assert warehouse.load_frame("meter_intervals", frame, ("meter_id", "interval_start_utc")).inserted == 0

def test_reconciliation_requires_balance() -> None:
    with pytest.raises(ReconciliationError):
        reconcile_source(SourceName.METER, landed=10, accepted=8, quarantined=1, loaded=8)
```

- [ ] **Step 2: Run tests and verify missing warehouse failures**

Run: `uv run pytest tests/integration/test_warehouse.py tests/integration/test_reconciliation.py -v`
Expected: collection fails because the pipeline warehouse and reconciliation modules do not exist.

- [ ] **Step 3: Implement schema, upsert-by-natural-key, operational evidence, and balance checks**

Use DuckDB transactions and temporary registered Polars Arrow tables. Create operational tables before domain tables. `LoadResult` must distinguish inserted, unchanged, and updated counts; the normal replay path expects unchanged rows, while corrected payloads update the canonical row and retain the new run ID.

- [ ] **Step 4: Run integration tests twice to expose state leakage**

Run: `uv run pytest tests/integration/test_warehouse.py tests/integration/test_reconciliation.py -v && uv run pytest tests/integration/test_warehouse.py tests/integration/test_reconciliation.py -v`
Expected: both runs pass with independent temporary warehouses.

- [ ] **Step 5: Commit warehouse layer**

```bash
git add src/gridbridge/pipeline tests/integration
git commit -m "feat: add idempotent utility warehouse loads"
```

### Task 4: dbt Transformation and Data Tests

**Files:**
- Create: `dbt/dbt_project.yml`
- Create: `dbt/profiles.yml`
- Create: `dbt/models/sources.yml`
- Create: `dbt/models/staging/stg_meter_intervals.sql`
- Create: `dbt/models/staging/stg_scada_observations.sql`
- Create: `dbt/models/intermediate/int_feeder_interval_load.sql`
- Create: `dbt/models/marts/fct_flex_interval_candidates.sql`
- Create: `dbt/models/schema.yml`
- Test: `tests/integration/test_dbt_project.py`

**Interfaces:**
- Consumes: the DuckDB domain tables created by `Warehouse.initialize()` and loaded by Task 3.
- Produces: dbt relations `stg_meter_intervals`, `stg_scada_observations`, `int_feeder_interval_load`, and `fct_flex_interval_candidates`; `run_dbt(project_dir: Path, warehouse_path: Path) -> DbtResult`.

- [ ] **Step 1: Write a failing dbt integration test**

```python
def test_dbt_build_creates_flex_mart(seeded_warehouse: Path) -> None:
    result = run_dbt(Path("dbt"), seeded_warehouse)
    assert result.success
    with duckdb.connect(str(seeded_warehouse), read_only=True) as con:
        assert con.execute("select count(*) from fct_flex_interval_candidates").fetchone()[0] > 0
```

- [ ] **Step 2: Run test and verify missing project failure**

Run: `uv run pytest tests/integration/test_dbt_project.py -v`
Expected: test fails because the dbt project and runner do not exist.

- [ ] **Step 3: Implement dbt project and subprocess runner**

Models must use explicit columns, UTC timestamps, documented grains, uniqueness/not-null/relationship tests, and no hidden production source. The Python runner passes the DuckDB path through `--vars` and captures structured success/failure evidence.

- [ ] **Step 4: Run dbt and integration tests**

Run: `uv run dbt build --project-dir dbt --profiles-dir dbt && uv run pytest tests/integration/test_dbt_project.py -v`
Expected: dbt reports PASS for models/tests and pytest passes.

- [ ] **Step 5: Commit SQL transformation layer**

```bash
git add dbt src/gridbridge/pipeline tests/integration/test_dbt_project.py
git commit -m "feat: model canonical utility data with dbt"
```

### Task 5: Network Topology and Safety-Gated Flex Advisory

**Files:**
- Create: `src/gridbridge/topology/__init__.py`
- Create: `src/gridbridge/topology/validate.py`
- Create: `src/gridbridge/flex/__init__.py`
- Create: `src/gridbridge/flex/recommend.py`
- Test: `tests/unit/test_topology.py`
- Test: `tests/unit/test_flex.py`

**Interfaces:**
- Consumes: canonical nodes, edges, DER capacity, feeder interval load, SCADA freshness, market price, and configured thresholds.
- Produces: `validate_topology(nodes: pl.DataFrame, edges: pl.DataFrame) -> TopologyResult` and `recommend_flex(inputs: FlexInputs, config: PipelineConfig) -> FlexRecommendation`.

- [ ] **Step 1: Write failing topology and fail-closed flex tests**

```python
def test_dangling_edge_is_reported() -> None:
    result = validate_topology(nodes_frame(["N1"]), edges_frame([("N1", "MISSING")]))
    assert "GIS_DANGLING_NODE" in {issue.code for issue in result.issues}

@pytest.mark.parametrize("gate", ["topology_valid", "telemetry_fresh", "capacity_valid"])
def test_failed_safety_gate_blocks_recommendation(gate: str) -> None:
    inputs = valid_flex_inputs().model_copy(update={gate: False})
    assert recommend_flex(inputs, config()).status == "blocked"
```

- [ ] **Step 2: Run tests and verify missing implementation failures**

Run: `uv run pytest tests/unit/test_topology.py tests/unit/test_flex.py -v`
Expected: collection fails because topology and flex packages do not exist.

- [ ] **Step 3: Implement graph checks and transparent advisory scoring**

Use energized edges only. Check edge references, connected components, paths to the substation, unexpected radial cycles, voltage transitions, and normalized capacity. Return all issues rather than stopping at the first. Flex output status must be one of `review`, `blocked`, or `not_economic`; include factor values and block reasons; never expose a dispatch action.

- [ ] **Step 4: Run topology, flex, and type tests**

Run: `uv run pytest tests/unit/test_topology.py tests/unit/test_flex.py -v && uv run mypy src/gridbridge`
Expected: tests pass and mypy reports success.

- [ ] **Step 5: Commit domain validation**

```bash
git add src/gridbridge/topology src/gridbridge/flex tests/unit
git commit -m "feat: gate flex advice with network safety checks"
```

### Task 6: End-to-End Pipeline, Replay, CLI, and Airflow DAG

**Files:**
- Create: `src/gridbridge/pipeline/run.py`
- Create: `src/gridbridge/cli.py`
- Create: `airflow/dags/gridbridge_onboarding.py`
- Create: `docker-compose.yml`
- Create: `Dockerfile`
- Test: `tests/e2e/test_demo.py`
- Test: `tests/integration/test_replay.py`
- Test: `tests/integration/test_airflow_dag.py`

**Interfaces:**
- Consumes: all shared functions from Tasks 1-5.
- Produces: `run_demo(workspace: Path, config_path: Path, seed: int = 42, parent_run_id: str | None = None) -> PipelineSummary`; Typer commands `generate`, `demo`, `replay`, `benchmark`; Airflow DAG ID `gridbridge_utility_onboarding`.

- [ ] **Step 1: Write failing end-to-end, replay, and DAG-structure tests**

```python
def test_demo_reconciles_all_sources_and_is_idempotent(tmp_path: Path) -> None:
    first = run_demo(tmp_path, Path("config/pipeline.yml"))
    second = run_demo(tmp_path, Path("config/pipeline.yml"))
    assert first.reconciliation_balanced
    assert second.total_inserted == 0
    assert first.report_path.exists()

def test_dag_defines_expected_stage_order() -> None:
    source = Path("airflow/dags/gridbridge_onboarding.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "gridbridge_utility_onboarding" in source
    assert any(isinstance(node, ast.FunctionDef) and node.name == "onboard" for node in ast.walk(tree))
```

- [ ] **Step 2: Run tests and verify orchestration failures**

Run: `uv run pytest tests/e2e/test_demo.py tests/integration/test_replay.py tests/integration/test_airflow_dag.py -v`
Expected: tests fail because the composite pipeline, CLI, and DAG do not exist.

- [ ] **Step 3: Implement pipeline composition and CLI**

The first `demo` generates sources when absent, lands run-scoped copies, executes stages, and writes a JSON summary. A repeated identical demo records a new audit run but inserts no duplicate domain facts. `replay --parent-run-id` validates the parent and records lineage. CLI errors must exit nonzero with a plain-language stage and evidence path.

- [ ] **Step 4: Implement Airflow and Docker demonstration**

Use TaskFlow tasks named `land`, `profile_validate`, `load_transform`, `validate_topology`, `recommend_flex`, `reconcile`, and `report`. The Docker stack uses an official pinned Airflow image, a PostgreSQL metadata service, health checks, and `.env.example` values without credentials intended for production.

- [ ] **Step 5: Run end-to-end and CLI tests**

Run: `uv run pytest tests/e2e tests/integration/test_replay.py tests/integration/test_airflow_dag.py -v && uv run gridbridge demo --workspace work/demo`
Expected: tests pass; CLI prints the run ID, balanced source counts, quarantine count, warehouse path, and report path.

- [ ] **Step 6: Commit execution paths**

```bash
git add src/gridbridge/pipeline/run.py src/gridbridge/cli.py airflow docker-compose.yml Dockerfile tests
git commit -m "feat: orchestrate end-to-end utility onboarding"
```

### Task 7: Static Report and Checked-In Reviewer Sample

**Files:**
- Create: `src/gridbridge/report/__init__.py`
- Create: `src/gridbridge/report/render.py`
- Create: `src/gridbridge/report/templates/report.html.j2`
- Create: `docs/assets/gridbridge-report.png`
- Create: `docs/examples/example-report.html`
- Test: `tests/unit/test_report.py`
- Test: `tests/e2e/test_report_contract.py`

**Interfaces:**
- Consumes: `PipelineSummary`, profiles, reconciliation, quarantine counts, topology results, and flex recommendations.
- Produces: `render_report(summary: PipelineSummary, output_path: Path) -> Path` and a standalone HTML file with no remote scripts, fonts, trackers, or stylesheets.

- [ ] **Step 1: Write failing report contract tests**

```python
def test_report_is_standalone_and_contains_evidence(summary: PipelineSummary, tmp_path: Path) -> None:
    report = render_report(summary, tmp_path / "report.html")
    html = report.read_text(encoding="utf-8")
    assert "Source reconciliation" in html
    assert "Topology findings" in html
    assert "Flex advisory" in html
    assert "https://" not in html
```

- [ ] **Step 2: Run test and verify missing renderer failure**

Run: `uv run pytest tests/unit/test_report.py tests/e2e/test_report_contract.py -v`
Expected: collection fails because the report renderer does not exist.

- [ ] **Step 3: Implement accessible standalone report**

Render semantic HTML with system fonts, responsive CSS, a restrained navy/cyan/amber palette, accessible tables, visible statuses, and explanatory copy. Show counts and rates with text as well as bars. Include the synthetic/advisory disclaimer in the header and footer.

- [ ] **Step 4: Generate sample report and screenshot**

Run: `uv run gridbridge demo --workspace work/reviewer-sample`
Expected: `docs/examples/example-report.html` is copied from the verified demo result; capture `docs/assets/gridbridge-report.png` at desktop width after visual inspection.

- [ ] **Step 5: Run report and accessibility contract tests**

Run: `uv run pytest tests/unit/test_report.py tests/e2e/test_report_contract.py -v`
Expected: all report tests pass.

- [ ] **Step 6: Commit reviewer report**

```bash
git add src/gridbridge/report tests docs/assets docs/examples/example-report.html
git commit -m "feat: render utility onboarding evidence report"
```

### Task 8: Documentation, Security Evidence, CI, and Benchmark

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `SECURITY.md`
- Create: `CONTRIBUTING.md`
- Create: `docs/architecture.md`
- Create: `docs/source-to-target-mapping.md`
- Create: `docs/data-dictionary.md`
- Create: `docs/client-onboarding-questionnaire.md`
- Create: `docs/data-quality-catalogue.md`
- Create: `docs/operator-runbook.md`
- Create: `docs/security-control-mapping.md`
- Create: `docs/production-evolution.md`
- Create: `docs/interview-talking-points.md`
- Create: `docs/benchmark.md`
- Create: `src/gridbridge/benchmark.py`
- Create: `.github/workflows/ci.yml`
- Test: `tests/unit/test_benchmark.py`
- Test: `tests/test_documentation.py`

**Interfaces:**
- Consumes: the finished CLI, pipeline evidence, and report assets.
- Produces: `run_meter_benchmark(output_dir: Path, rows: int = 1_000_000, seed: int = 42) -> BenchmarkResult`, a reproducible benchmark JSON file, and the complete reviewer documentation set.

- [ ] **Step 1: Write failing benchmark and documentation tests**

```python
def test_benchmark_generates_requested_rows(tmp_path: Path) -> None:
    result = run_meter_benchmark(tmp_path, rows=10_000, seed=42)
    assert result.rows == 10_000
    assert result.rows_per_second > 0

def test_readme_links_required_evidence() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    for path in REQUIRED_DOCS:
        assert path in readme
```

- [ ] **Step 2: Run tests and verify missing benchmark/docs failures**

Run: `uv run pytest tests/unit/test_benchmark.py tests/test_documentation.py -v`
Expected: tests fail because benchmark code and documentation do not exist.

- [ ] **Step 3: Implement streamed deterministic benchmark**

Generate interval partitions in bounded batches, process them through the meter validation and DuckDB load path, query a feeder/day aggregation, and record Python/platform/CPU context, rows, elapsed seconds, rows per second, accepted/quarantined counts, database bytes, and query milliseconds. Do not commit bulk Parquet or DuckDB files.

- [ ] **Step 4: Write documentation with evidence-safe claims**

README must lead with the completed outcome, screenshot, architecture/data-flow Mermaid diagrams, quick start, sample defects, commands, test evidence, and role mapping. Security documentation labels mappings as `control-inspired`; interview notes state exactly what is synthetic, implemented, benchmarked, optional, and out of scope.

- [ ] **Step 5: Implement CI and repository policy files**

CI runs Ruff, mypy, pytest, dbt build, DAG AST/import checks, package build, and Docker build on supported events. Pin action major versions and grant read-only default permissions. Add MIT license, responsible disclosure instructions, contribution commands, and Dependabot configuration if it does not add unsupported ecosystem claims.

- [ ] **Step 6: Run million-row benchmark and record observed results**

Run: `uv run gridbridge benchmark --rows 1000000 --output work/benchmark`
Expected: command exits zero, generated data remains ignored, and `docs/benchmark.md` is updated only with truthful observed machine context and metrics.

- [ ] **Step 7: Run full local verification**

Run: `uv sync --all-groups && uv run ruff format --check . && uv run ruff check . && uv run mypy src/gridbridge && uv run pytest -v && uv run dbt build --project-dir dbt --profiles-dir dbt && uv build`
Expected: every command exits zero.

- [ ] **Step 8: Commit portfolio documentation and automation**

```bash
git add README.md LICENSE SECURITY.md CONTRIBUTING.md docs src/gridbridge/benchmark.py .github tests pyproject.toml
git commit -m "docs: complete GridBridge reviewer experience"
```

### Task 9: Clean-Checkout Verification and GitHub Publication

**Files:**
- Modify: only files required by verification findings.

**Interfaces:**
- Consumes: the completed repository and authenticated GitHub CLI session.
- Produces: public repository `https://github.com/SkinnyFatBoy05/gridbridge`, pushed `main`, and a verified GitHub Actions run.

- [ ] **Step 1: Verify repository hygiene and secret absence**

Run: `git status --short && git ls-files | rg -i '(\.env$|\.duckdb$|\.parquet$|credential|secret)' && git diff --check`
Expected: clean status; only intentional small sample Parquet files, if any, are tracked; no `.env`, credentials, generated warehouse, or bulk benchmark data is tracked; diff check is clean.

- [ ] **Step 2: Run the reviewer journey from a fresh temporary clone**

Run: clone the local repository into a temporary directory, install with `uv sync`, run `uv run gridbridge demo --workspace work/clean-demo`, then run the full test suite.
Expected: demo and tests exit zero without relying on untracked files from the development checkout.

- [ ] **Step 3: Create and push the public repository**

Run: `gh repo create SkinnyFatBoy05/gridbridge --public --source . --remote origin --push --description "Synthetic utility data onboarding control plane for meter, GIS, SCADA, DER and flex-market integration"`
Expected: GitHub returns the repository URL and `main` tracks `origin/main`.

- [ ] **Step 4: Verify remote metadata and CI**

Run: `gh repo view SkinnyFatBoy05/gridbridge --json nameWithOwner,url,visibility,description,defaultBranchRef && gh run list --repo SkinnyFatBoy05/gridbridge --limit 5`
Expected: repository is PUBLIC, default branch is `main`, metadata is accurate, and the current workflow is passing or actively running.

- [ ] **Step 5: Fix remote-only failures and push final verification commit if necessary**

Inspect failed job logs with `gh run view --log-failed`, reproduce locally, add a regression test, apply the smallest fix, rerun the full verification command, commit, and push.

- [ ] **Step 6: Record final evidence**

Run: `git status --short --branch && git log --oneline --decorate -10 && gh run list --repo SkinnyFatBoy05/gridbridge --limit 3`
Expected: clean tracked branch, coherent commit history, and passing remote checks.
