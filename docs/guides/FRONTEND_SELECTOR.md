# Frontend Selector

The frontend selector is a static HTML/JS UI that lets you choose mandates and
guidelines before running the interactive wizard. It runs entirely in the browser
with no server or CDN dependency.

## Purpose

Use the selector to build a `selector-selection.json` artifact that narrows which
mandates and guidelines are emitted by **Phase 1** of the wizard.

> **Contract clarification**: the selector output feeds **Phase 1**
> (`phase1_generator.py`), not Phase 3. Phase 3 reads the markdown produced by
> Phase 1 after the user has reviewed and edited it.

## Flow

```
Selector UI → selector-selection.json
                      │
                      ▼
              Phase 1 (phase1_generator.py)
              Filters mandates and guidelines to selected IDs
              Writes phase-1-choices/{category}.md
                      │
                      ▼
              User reviews and edits markdown (status: required/optional)
                      │
                      ▼
              Phase 3 (phase3_compiler.py)
              Compiles final governance artifacts
```

## Available Commands

| Command | What it does |
|---------|--------------|
| `make selector-build` | Build selector assets into `docs/selector/` (a generated, gitignored directory inside the MkDocs `docs_dir`) |
| `make docs-build` | Runs `selector-build`, then `mkdocs build --strict`. MkDocs copies `docs/selector/` into `build/site/selector/` as a static asset |
| `make docs-serve` | Runs `selector-build`, then `mkdocs serve`. The selector UI is served at `/selector/` alongside the rest of the docs |
| `python -m sdd_wizard.orchestration.wizard.selector_compiler --output-dir <dir>` | Standalone compiler; `--repo-root` defaults to `.` |

## Build and Open

```bash
make selector-build
# then open docs/selector/index.html in a browser
```

Or build the full site (selector included at `build/site/selector/`):

```bash
make docs-build
# then open build/site/selector/index.html
```

Or serve docs and selector together, live:

```bash
make docs-serve
# then open http://127.0.0.1:8000/selector/
```

## Workflow

1. Run `make selector-build` (or `make docs-build` / `make docs-serve`).
2. Open `docs/selector/index.html` (or `build/site/selector/index.html`, or
   `http://127.0.0.1:8000/selector/` when serving) in a browser.
3. Select the mandates (M-IDs) and guidelines (G-IDs) you want to keep.
   - Cards with a **blue left border** are mandates.
   - Cards with a **green left border** are guidelines.
4. Click **Export JSON** to download `selector-selection.json`.
5. Copy the file to `generated/client/build/selector-selection.json`.
6. Run the interactive wizard — Phase 1 will apply the filter automatically.
7. Use **Import JSON** to restore a previous selection.

## Export Contract — `selector-selection.json`

```json
{
  "version": "1.0",
  "selected_ids": ["M001", "G01"],
  "resolved_ids": ["M001", "M002", "G01"]
}
```

| Field | Description |
|-------|-------------|
| `selected_ids` | IDs explicitly checked by the user |
| `resolved_ids` | All IDs consumed by Phase 1, including auto-resolved dependencies |

Consumed by: `interactive_mode.py` → `Phase1Generator._apply_selector_selection()`

## Item Types

The selector lists two kinds of items, each with a visual indicator:

- **Mandate** (blue pill, blue left border) — hard governance rules identified by `M`-prefixed IDs (e.g. `M001`).
- **Guideline** (green pill, green left border) — advisory rules identified by `G`-prefixed IDs (e.g. `G01`).

## Constraints

- The wizard works without a `selector-selection.json` — all mandates and guidelines are included.
- Unknown IDs in `resolved_ids` cause Phase 1 to fail fast with a descriptive error rather than producing partial templates.
- An empty `resolved_ids` list is treated as "no filter" — all items are kept.
- No CDN or network dependency is required by the selector runtime.
