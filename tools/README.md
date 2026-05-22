# Sovereign Factory: Support Tools (`tools/`)

Developer and CI utilities for the SDD monorepo.
These tools follow the **Sovereign Factory** pattern: they are self-contained, deterministic, and environment-agnostic via **PEP 723**.

---

## Execution Standards

All tools should be executed via **uv** to ensure dependency isolation and cross-platform (Windows/Linux) parity.

### 1. Unified CLI (Recommended)
The SDD CLI provides a discovery layer for all tools:
```bash
sdd tools list                 # List available tools
sdd tools run <category>/<name> # Execute a tool (e.g. maintenance/lint_all)
```

### 2. Direct Execution (PEP 723)
Tools can be run directly using `uv`, which will automatically manage the script's dependencies:
```bash
uv run python tools/maintenance/lint_all.py
```

---

## Directory Map

```
tools/
├── architecture/
│   ├── validate_imports.py   Layer isolation validator
│   └── score.py              Architecture health score
│
├── governance/
│   ├── compliance.py         [Hardened] Ed25519 source governance validator (P003)
│   └── seedling_loader.py    Auto-load and activate governance seedlings
│
├── health/
│   └── health_check.py       Portable health engine (uv-powered)
│
├── maintenance/
│   └── lint_all.py           Orchestrated monorepo linting (ruff, mypy, arch)
│
├── testing/
│   ├── diagnostics.py        14-check diagnostic suite
│   ├── run-all-tests.py      Parallelized multi-layer pytest runner (xdist)
│   └── update-golden-snapshots.py Update contract test fixtures
│
└── verify_mkdocs_paths.py    Verify nav paths in mkdocs.yml
```

---

## Core Workflows

### Testing (Parallel & Layered)
```bash
# Run all tests in parallel
make test

# Run tests for a specific layer (e.g. core)
uv run python tools/testing/run-all-tests.py --layer core

# Pass extra arguments to pytest
make test ARGS="-- -k test_compliance"
```

### Linting & Auto-fix
```bash
# Run all quality checks (ruff, mypy, architecture)
make lint

# Apply all safe auto-fixes
make lint-fix
```

### Hardened Governance (P003)
To comply with the "Human-in-the-loop" mandate (P003), governance changes must be signed with an Ed25519 key:
```bash
# 1. Generate your auditor key (one-time)
sdd governance keygen --key-id human-sergio

# 2. Sign the source governance configuration
sdd governance sign --source --key-id human-sergio
```

---

## Tool Status (Sovereign Factory Ready)

| Tool | Engine | Status | Notes |
|---|---|---|---|
| `lint_all.py` | PEP 723 | ✅ NEW | Orchestrates ruff + mypy + arch |
| `run-all-tests.py` | PEP 723 | ✅ UPGRADED | Parallel execution + full coverage |
| `compliance.py` | PEP 723 | ✅ HARDENED | Validates Ed25519 signatures |
| `health_check.py` | PEP 723 | ✅ ACTIVE | Core CI/CD gate |

---

## Agent Skills (`tools/skills/`)

This directory contains instructions that allow AI Agents (like Antigravity) to operate the SDD ecosystem with high fidelity.

- **sdd-harness**: Maps `.github/prompts/*.prompt.md` to operational workflows.
  - *Status*: Operational
  - *Mandate*: Enforces the P003 "Human-in-the-loop" sign-off and mandatory footers.
