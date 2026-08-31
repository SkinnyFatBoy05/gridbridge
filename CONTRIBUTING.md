# Contributing

Contributions should preserve the synthetic-only and advisory-only boundaries.

## Setup

```bash
uv sync --frozen
uv run gridbridge demo --workspace work/contributor-demo
```

## Before opening a pull request

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src/gridbridge
uv run pytest
uv build
```

Add a failing test before changing behaviour. Keep source adapters isolated from canonical logic, add stable reason codes for new validation failures, and document new fields in the mapping and data dictionary. Never add real utility or personal data, secrets, generated warehouses or bulk benchmark files.

