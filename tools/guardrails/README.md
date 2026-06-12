# Guardrails Framework

A unified, multi-dimension code analysis framework for Python packages, replacing the
previously duplicated `tools/analysis/analyze_sdd_*.py` scripts (see
`.analysis/pending/guardrails-framework-design.md` for the architectural design).

## Layout

```
tools/guardrails/
├── core/           # GuardrailAnalyzer, AnalysisDimension, PatternRegistry, FileMetrics, config, discovery
├── analyzers/      # Concrete analyzers (RuntimeAnalyzer, TelemetryAnalyzer)
├── reporters/      # ReportTemplate, shared markdown rendering helpers
├── cli.py          # CLI entry point
└── analysis.yaml   # Default configuration
```

## Usage

Run an analyzer via the CLI:

```bash
uv run python -m tools.guardrails.cli --analyzer runtime
uv run python -m tools.guardrails.cli --analyzer telemetry
uv run python -m tools.guardrails.cli --analyzer all
```

Each analyzer writes four files under `.analysis/pending/<analyzer-name>/`:

- `discovery.md` — file inventory with per-dimension scores
- `analysis.md` — detailed per-file findings, grouped by dimension
- `recommendations.md` — worst-scoring files per dimension
- `analysis.json` — raw structured data

### Options

- `--analyzer {runtime,telemetry,all}` — which analyzer(s) to run (default: `all`)
- `--config PATH` — path to a YAML config file (default: `tools/guardrails/analysis.yaml`)
- `--output-dir PATH` — override the output directory (default: `.analysis/pending/<analyzer-name>`)
- `--target-dir PATH` — override the package directory to analyze

## Configuration

`analysis.yaml` holds all configurable thresholds and file-discovery patterns. Copy it, edit the
thresholds, and pass the new file via `--config`:

```yaml
analysis:
  refactoring:
    max_file_lines: 200
    max_function_lines: 30
    max_function_parameters: 5
  performance:
    max_nested_loops: 2
    max_append_operations: 50

file_discovery:
  include_patterns:
    - "**/*.py"
  exclude_patterns:
    - "tests/"
    - "venv/"
    - "__pycache__/"
```

## Migration from the old scripts

The standalone analysis scripts have been replaced by this framework (hard cutover, per Q4 in
`.analysis/pending/guardrails-framework-design.md`) and archived under
`tools/analysis/deprecated/`:

| Old invocation | New invocation |
|---|---|
| `python tools/analysis/analyze_sdd_runtime.py` | `uv run python -m tools.guardrails.cli --analyzer runtime` |
| `python tools/analysis/analyze_sdd_telemetry.py` | `uv run python -m tools.guardrails.cli --analyzer telemetry` |

Output file names and locations (`.analysis/pending/<analyzer-name>/{discovery,analysis,recommendations}.md`
and `analysis.json`) are unchanged.

`tools/analysis/evaluate_pending_completion.py` is **not** part of this migration. It was
investigated for a Phase 4 migration but found architecturally incompatible with this framework
(it classifies and moves filesystem items rather than performing AST-based analysis). It remains
the canonical, runnable implementation — see "Phase 4 — Open Question (Deferred)" in
`.analysis/pending/guardrails-framework-design.md`.
