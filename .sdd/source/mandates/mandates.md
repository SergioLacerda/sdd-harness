# Mandates - SDD v3.0

⚡ IA-FIRST DESIGN NOTICE
- **Status**: Architecture-level governance rules
- **Optimization**: Optimized for AI agent parsing
- **Version**: 3.0
- **Language**: Python
- **Generated**: 2026-06-14T09:05:01.575589

## Core Mandates

Mandatory rules that CANNOT be customized or skipped.

## M001: Clean Architecture

**Criticality**: high
**Customizable**: No

Domain and application layers must be strictly separated from infrastructure adapters and external frameworks. Dependencies always point inward; nothing in the domain layer imports from adapters or infrastructure.

## M002: Test-Driven Development (TDD)

**Criticality**: high
**Customizable**: No

All production code must be preceded or accompanied by failing tests. Coverage thresholds are enforced in CI; merges are blocked when coverage drops below the declared minimum for the target language profile.

## M003: Context Awareness & Task Caching

**Criticality**: medium
**Customizable**: No

Agents must leverage cached workspace context to avoid redundant reads and re-derivation. Context state is invalidated when underlying files or governance artifacts change; agents must not assume stale context is valid.

## M005: Token Economy Enforcement

**Criticality**: medium
**Customizable**: No

AI agent interactions must minimize token consumption. Prompts must be concise, reusable results must be cached, and agents must not re-derive information already present in the active context window.

## M006: RFC Process Mandate

**Criticality**: high
**Customizable**: No

Any change that could require users to update their code, configuration, or governance artifacts must follow a documented RFC process. Breaking changes shipped without an approved RFC are a governance violation.

## M007: Telemetry Enforcement

**Criticality**: high
**Customizable**: No

All components must emit structured telemetry events for key operations. Telemetry pipelines must be queryable, reliable, and must not silently drop events under load or during shutdown.

## M008: Audit Integrity

**Criticality**: high
**Customizable**: No

All governance decisions, agent actions, and enforcement events must be recorded immutably. Audit logs cannot be truncated, filtered, or overwritten without an approved and explicitly recorded policy exception.

## M009: OpenTelemetry Compliance

**Criticality**: high
**Customizable**: No

All services must instrument with OpenTelemetry spans, metrics, and logs following the declared schema. Proprietary telemetry SDKs may not replace OpenTelemetry without an approved architectural decision record.

## M010: Delivery Hygiene Enforcement

**Criticality**: high
**Customizable**: No

Workspaces are treated as potentially shared between parallel agents and developers. Destructive git operations require explicit authorization; agents may not commit, push, reset, or stash without confirmed user approval.

## M011: English Language Standard

**Criticality**: high
**Customizable**: No

All governance artifacts, technical documentation, code comments, and CI outputs must be authored in English. Non-English content is permitted only on contextual surfaces explicitly declared as non-canonical by the workspace language policy.

## M015: Bidirectional Agent Handshake

**Criticality**: medium
**Customizable**: No

Before any mutating operation, the agent must announce its governance state and obtain user confirmation. Agents that bypass the handshake protocol or proceed without confirmation are non-compliant with this mandate.

## M016: Guardrail Non-Regression

**Criticality**: high
**Customizable**: No

Governance guardrails may not be removed, weakened, or bypassed. Any reduction in enforcement coverage requires an approved architectural decision record; unilateral guardrail removals are treated as compliance failures.

## M017: Analysis Plugin Compliance

**Criticality**: medium
**Customizable**: No

Analysis plugins must implement the declared plugin interface contract. Plugins that deviate from the contract schema or bypass declared hooks are blocked from the analysis pipeline without exception.

## M018: Code Quality Baseline

**Criticality**: high
**Customizable**: No

All code must pass the declared quality gates for the target language: static analysis, type checking, and linting. Quality thresholds are defined per language profile and enforced without exception in CI; no merge is allowed with failing quality gates.

## M019: Governance Federation

**Criticality**: medium
**Customizable**: No

Multiple governance domains may federate under a unified root authority. Federated domains must declare their scope explicitly; federated mandates may not override core mandates without a federation-level approval record.

## M020: Governed Compact Logging

**Criticality**: medium
**Customizable**: No

All log output must follow the compact logging format: structured JSON, bounded payload size, no PII, no secrets in log values. Verbose or free-form logging is permitted only in explicitly scoped debug builds.
