# REFACTOR_NOTES — sdd_cli module decomposition
# Started: 2026-06-08

## Baseline Metrics (Wave 0)

### Test suite
- **Unit tests**: 1347 passed, 14 skipped (tests/unit/)
- **Full suite** (unit + sdd_cli): 2001 passed, 15 skipped
- Coverage: not measured at baseline

### Source files > 300 lines

| File | Lines |
|------|-------|
| commands/_ask_backend.py | 1377 |
| commands/governance.py | 1098 |
| commands/audit.py | 951 |
| commands/skills.py | 862 |
| commands/runtime.py | 541 |
| commands/lint.py | 433 |
| commands/telemetry.py | 418 |
| commands/test.py | 412 |
| commands/metrics.py | 395 |
| generators/_prompt_commands.py | 385 |
| extensions/framework/extension_framework.py | 349 |
| services/governance_config_handlers.py | 348 |
| utils/profile.py | 333 |
| generators/_shared.py | 319 |
| main.py | 303 |

**Total source lines: 14787**

### External consumers of sdd_cli (public API surface)

Files outside the package that import from `sdd_cli.*`:
- packages/core/sdd_core/tests/cli/test_ask_command.py
- packages/core/sdd_core/tests/cli/test_ask_security.py
- tests/conftest.py
- tests/contract/conftest.py
- tests/contract/test_execution_gate.py
- tests/contract/test_governance_schema.py
- tests/integration/cli/test_onboarding_flow.py
- tests/unit/cli/* (multiple)

## Gaps & Bugs Log

### Wave 1 — ask_backend decomposition
<!-- Populated as refactoring proceeds -->

## Wave Progress

| Wave | Status | Tests after |
|------|--------|-------------|
| 0 — Baseline | ✅ done | 2001 passed |
| 1 — ask_backend split | pending | — |
| 2 — governance.py split | pending | — |
| 3 — audit.py split | pending | — |
| 4 — skills.py split | pending | — |
| 5 — remaining commands | pending | — |
| 6 — generators/extensions/utils | pending | — |
| 7 — test realignment | pending | — |
| 8 — gap remediation | pending | — |
