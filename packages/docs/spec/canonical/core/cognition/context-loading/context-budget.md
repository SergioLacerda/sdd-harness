# Context Budget

## Purpose

- Preserve reasoning quality by keeping context load bounded and relevant.

## Budget Targets

- PATH A/B: keep task context compact and local.
- PATH C: load cross-layer context incrementally.
- PATH D: enforce per-thread budgets independently.
- PATH E: minimum emergency context only.
- PATH F: scoped structural context only.

## 30/70 Rule

- Reserve enough reasoning space; avoid overloading docs and code.
- Prefer progressive loading over full corpus loading.

## Compression Techniques

- Functional skeletonizing for neighbor files.
- Semantic pruning by loading only relevant sections.
- Layer masking: interfaces before implementations.

## Budget Breach Protocol

- Decompose oversized tasks.
- Flush stale exploration context.
- Reload only mandatory artifacts for next step.

## Anti-Patterns

- Loading complete canonical trees without path need.
- Carrying stale experiments into final execution.
- Ignoring explicit path budgets.
