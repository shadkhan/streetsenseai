# StreetSense AI — Python API

FastAPI backend for the StreetSense AI platform. Consumes UK open government
data (Street Manager, OS Data Hub) to provide corridor disruption risk scoring,
underground asset strike risk, non-compliance analytics, and an AI copilot.

## Quick Start

```bash
# Install dependencies
uv sync

# Start local services (PostgreSQL + Redis)
docker-compose -f ../../infra/docker-compose.yml up -d

# Run database migrations
uv run alembic upgrade head

# Start the dev server
uv run uvicorn main:app --reload
```

## Running Tests

```bash
uv run pytest                          # all tests
uv run pytest -k "synthetic"           # synthetic data tests only
uv run pytest -k "corridor"            # corridor tests only
uv run mypy .                          # type checking
uv run ruff check .                    # linting
```

---

## Synthetic Data

StreetSense AI uses synthetic Street Manager permit data during development,
before connecting to the live API. See **ADR-022** in `DECISIONS.md` for the
full rationale.

### Why synthetic data first?

The live Street Manager API requires DfT verification (5-10 working days) and
sandbox access requires prior approval. Synthetic data lets us:

- Build and test all Phase 1-2 features with realistic, schema-conformant records
- Run deterministic CI pipelines (same seed -> same fixture, always)
- Generate edge cases (overruns, corridor clusters, cancelled permits) on demand
- Avoid hitting rate limits during development

### Canonical fixture

The pre-generated fixture lives at:

```
tests/fixtures/works_2026.json
```

- **5,045 permits** (5,000 base + 45 corridor cluster)
- **Seed:** 42 (deterministic)
- **Date window:** 2026-01-01 to 2026-12-31
- **Corridors:** A38 Birmingham, M42 Jn 3-4, A1 Leeds North (15 permits each)
- **Edge cases:** overrun, modified, cancelled injected (~5% of records each)
- **File size:** ~3.5 MB

### Reproducing the canonical fixture

```bash
uv run python -m scripts.generate_fixtures \
    --count 5000 \
    --start 2026-01-01 \
    --end 2026-12-31 \
    --output tests/fixtures/works_2026.json \
    --seed 42 \
    --include-edge-cases overrun,modified,cancelled \
    --critical-corridors "A38 Birmingham,M42 Jn 3-4,A1 Leeds North"
```

### CLI reference

```
uv run python -m scripts.generate_fixtures [OPTIONS]

Options:
  --count INT                  Number of base permits (default: 1000)
  --start YYYY-MM-DD           Window start date (default: 2026-01-01)
  --end YYYY-MM-DD             Window end date (default: 2026-12-31)
  --output PATH                Output JSON file (default: tests/fixtures/works_2026.json)
  --seed INT                   RNG seed for determinism (default: 42)
  --include-edge-cases LIST    Comma-separated: overrun,modified,cancelled,
                               weekend_only,school_term_peak
  --critical-corridors LIST    Comma-separated corridor names for concurrent-works clusters
  --corridor-cluster-size INT  Permits per corridor cluster (default: 15)
```

### Adding a new edge case type

Edge cases are injected in `services/synthetic/generator.py` via the
`inject_edge_cases` method. To add a new type:

1. Add an `_inject_<type>` private method that receives the works list and
   returns a modified copy. Target ~5% of records and use `model_copy(update={})`
   rather than mutating in place.

2. Add the new key to the dispatch dict inside `inject_edge_cases`:
   ```python
   _INJECTORS = {
       "overrun":           self._inject_overrun,
       "modified":          self._inject_modified,
       "cancelled":         self._inject_cancelled,
       "weekend_only":      self._inject_weekend_only,
       "school_term_peak":  self._inject_school_term_peak,
       "your_new_type":     self._inject_your_new_type,   # add here
   }
   ```

3. Add a test in `tests/services/test_synthetic.py` verifying that at least
   one record shows the expected mutation after injection.

### Reference data

Synthetic permits are built from three JSON files in `services/synthetic/refs/`:

| File | Contents |
|------|----------|
| `authorities.json` | 41 English highway authorities with geographic centres, USRN prefixes, and relative work volume weights |
| `promoters.json` | 57 UK utility and highway promoters with licence numbers and type-affinity weighting |
| `work-types.json` | 8 Street Manager work categories with duration ranges and traffic management defaults |

To extend coverage (e.g. add Welsh authorities), edit these JSON files -- no
generator code changes are needed.
