# RETRIEVAL BEFORE REASONING

## Objective

Ensure grounding artifacts are loaded before architectural reasoning.

## MUST

- Retrieve affected files before proposing changes.
- Retrieve relevant mandates and path constraints.
- Retrieve related tests and runtime context.

## MUST NOT

- Speculate design changes before retrieval.
- Expand scope heuristically without evidence.
- Infer contract behavior from memory alone.

## INVALID

- Any architectural decision made without explicit grounding references.
- Any fix proposed sem leitura mínima do escopo afetado.

## Escalation/Recovery

- If evidence is missing, pause execution and load only required artifacts.
- If retrieval conflicts exist, prioritize canonical sources and reconcile drift.
