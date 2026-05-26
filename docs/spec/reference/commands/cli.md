# SDD CLI Reference (v3.1)

The sdd command is the main entry point for framework operations.

## Profile Detection

The SDD CLI operates in one of two profiles: **master** (framework development) or **client** (project instance). The profile is auto-detected using the following priority:

1. `--profile` flag (highest priority)
2. `SDD_PROFILE` environment variable
3. `.sdd/profile` (`[sdd] type = master|client`)
4. If workspace is not initialized, fail with actionable message (`sdd init`)

```bash
# Use explicit profile override
sdd --profile master governance compile
sdd --profile client wizard run

# Or set via environment
SDD_PROFILE=master sdd governance compile
```

The current profile is inferred automatically in most cases. Profile affects which operations are permitted:

| Command | master | client |
|---------|--------|--------|
| `governance compile` | ✅ | ✅ |
| `governance load/validate` | ✅ | ✅ |
| `wizard run` | ⚠️ warn | ✅ |
| `release build` | ✅ | ❌ blocked |
| `doctor run` | ✅ | ✅ |
| `docs update/deploy` | ✅ | ✅ |

## Essential Commands

## Global Flags

- `--json`: emit structured JSON payloads for commands that support machine-readable output.
- `--verbose` / `-v`: enable detailed output for commands that support verbose mode.

Examples:

```bash
sdd --json runtime status
sdd --json governance validate
sdd --verbose runtime status
```

### Project Setup

- sdd setup run: Initializes workspace dependencies and local tooling.

### Testing and Validation

- sdd test run: Runs the full test pipeline and shows project coverage summary by default.
- sdd test ci-validate: Runs CI-oriented validations.
- sdd lint run: Runs static quality checks.

Coverage options for sdd test run:

```bash
# Default coverage output
sdd test run

# Disable coverage
sdd test run --no-coverage

# Customize report style
sdd test run --cov-report term

# Enforce minimum percentage
sdd test run --cov-fail-under 80
```

### Governance Management

- sdd governance load: Shows loaded governance summary.
- sdd governance validate: Validates structure, file access, and fingerprints.
- sdd governance generate: Generates agent seeds from governance rules.
- sdd governance compile: Compiles governance artifacts (mandates + guidelines → msgpack binaries).
- sdd governance sign: Signs compiled artifacts or source specs (`--source`) with Ed25519.
- sdd governance audit: Performs a security audit of the workspace and signatures.
- sdd governance keygen: Generates Ed25519 key pairs for signing.

### Compliance Audit

- `sdd audit`: Governance drift + telemetry summary (existing behavior).
- `sdd audit view --since YYYY-MM-DD --event-type VIOLATION`: filtered event viewer for compliance events.
- `sdd audit export --format=csv > compliance_report.csv`: deterministic CSV export to stdout, plus evidence manifest via `--manifest-file` (default `.sdd/runtime/compliance-export.manifest.json`).
- `sdd audit legacy-check [--phase-date YYYY-MM-DD]`: staged legacy policy enforcement (Q3 2026 warn, Q4 2026 block).
- `sdd audit bootstrap-check`: validates AGENTS/CLAUDE bootstrap contract drift against `.sdd` authority model.
- `sdd audit compliance-pack --out-dir .sdd/runtime/compliance-pack`: generates external-review evidence bundle.

### Maintenance and Tooling

- sdd tools list: Lists available maintenance tools in `tools/`.
- sdd tools run <category>/<name>: Executes a tool with automatic environment isolation (uv-powered).

### Governance Query (Ask)

Entry point for governed queries and skill routing. Loads compiled governance context before any agent response.

- `sdd ask "<query>"` — minimal governance context (fingerprint + mandates). Use for quick queries and skill routing decisions.
- `sdd ask-full "<query>"` — full governance context with telemetry. Use when confidence or drift information is needed.

Both commands emit:

```
=== SDD Governance Context ===
query_hash      : <hash>
context_source  : compiled
fingerprint     : <hash>
mandates_loaded : <n>
trust_source    : canonical
degraded        : no

SDD GOVERNANCE: drift=<status> | governance=<status> | profile=<profile>
```

If `drift=detected` or `governance=partial`, run `sdd governance compile` before retrying.

```bash
# Route a request through governed context
sdd ask "diagnose failing tests"

# Full telemetry (confidence gate, drift check)
sdd ask-full "implementar plano: .sdd/skills/sdd-ask/skill.yaml"
```

### Capability Layer (Skills)

Skills are V6-schema governed capabilities (`schema_version: 1.1.0`). Each skill has explicit `triggers`, `forbidden` actions, `fallback_to`, and `idempotent` flag.

- `sdd skills list` — list all registered skills with category and risk score.
- `sdd skills describe <name>` — return full skill metadata including V6 fields.
- `sdd skills run <name>` — execute governed skill pipeline.
- `sdd skills export` — export skill definitions to `json/openai/langchain/crewai/autogen`.
- `sdd skills --full-bootstrap` — regenerate all `skill.yaml` files and `registry.json` from the canonical Python `_REGISTRY`. **Overwrites** any manual edits to `.sdd/skills/` — V6 fields must be set in `_REGISTRY` (`packages/core/sdd_runtime/src/sdd_runtime/skills.py`) to survive bootstrap.
- `sdd skills learning-candidates` — generate/list supervised `RuleCandidate` entries from `FailureLedger`.
- `sdd skills learning-approve <candidate-id> --rationale ... [--ttl-days N]` — human approval path; activates rule in registry.
- `sdd skills learning-reject <candidate-id> --rationale ...` — human rejection path; keeps candidate history without activation.
- `sdd skills learning-rules` — list active supervised rules.
- `sdd skills learning-impact <rule-id> --rework-delta X --false-block-rate Y --escalation-delta Z [--rollback-flag]` — record impact and optionally trigger rollback (negative learning).
- `sdd skills learning-status [--window-days N]` — summarize candidate/rule/impact health in a recent time window.

Built-in skills (registry `schema_version: 1.1.0`):

| Skill | Category | Risk | Idempotent | Fallback |
|-------|----------|------|------------|---------|
| `sdd-ask` | orchestrator | controlled | no | — |
| `sdd-diagnose` | analysis | low | yes | — |
| `sdd-correct` | correction | medium | no | sdd-diagnose |
| `sdd-converge` | convergence | high | no | sdd-correct |
| `sdd-stabilize` | operations | medium | yes | sdd-diagnose |
| `sdd-review-architecture` | architecture | high | yes | sdd-diagnose |
| `sdd-validate-governance` | governance | medium | yes | — |
| `sdd-compress-context` | economy | low | yes | — |

JSON minimum contract for skills:

- `state`, `profile`, `skill`, `policy_result`, `exit_code`, `reason`, `governance_footer`.

Canonical envelope (contract-first, preferred for new consumers):

- `status`: `ok | error`
- `command`: canonical command id (e.g. `runtime status`, `skills run`)
- `ok`: boolean success flag
- `error`: `null` or `{code, message}`
- `data`: command payload (authoritative fields)

Skill output schema (`skill_output.schema.yaml`):

- `status`: `ok | error | degraded`
- `confidence.overall`: float `[0.0, 1.0]`
- `error.category`: taxonomy key (see `.sdd/skills/contracts/skill_output.schema.yaml`)
- `next_skill`: id of recommended next skill, or `null`

Governance footer contract:

- `SDD GOVERNANCE: drift=<status> | governance=<status> | profile=<profile>`

JSON automation examples:

```bash
sdd --json governance compile | jq '.data.summary'
sdd --json governance load --path runtime | jq '.data.summary'
sdd --json governance validate | jq '.ok,.data.preflight'
sdd skills list
sdd skills describe sdd-ask
sdd --json skills learning-status | jq '.data.status'
sdd --json skills learning-candidates | jq '.data.created_count,.data.candidates | length'
sdd --json skills run sdd-diagnose | jq '.data.artifacts.diagnosis_attestation'
sdd --json skills run sdd-converge | jq '.data.artifacts.freeze_mode_state'

```

Supervised learning workflow (safe default):

```bash
# 1) Observe candidates derived from recurring failures
sdd --json skills learning-candidates

# 2) Human decision
sdd --json skills learning-approve rc-abc123 --rationale "validated recurrence" --ttl-days 30
# or
sdd --json skills learning-reject rc-abc123 --rationale "insufficient evidence"

# 3) Measure impact
sdd --json skills learning-impact rr-def456 \
  --rework-delta -0.12 \
  --false-block-rate 0.04 \
  --escalation-delta 0.01

# 4) Detect degradation and rollback
sdd --json skills learning-impact rr-def456 \
  --rework-delta 0.22 \
  --false-block-rate 0.38 \
  --escalation-delta 0.19 \
  --rollback-flag
```

### Scaffold

Generate new skills and slash commands from V6-compliant canonical templates.

- `sdd scaffold skill <name>` — create a new skill under `.sdd/skills/<name>/` with `skill.yaml` and `SKILL.md`.
- `sdd scaffold command <name>` — create a new slash command under `.sdd/commands/<name>/` with `command.yaml`.

Options for `sdd scaffold skill`:

| Flag | Default | Description |
|------|---------|-------------|
| `--category` | `operations` | `analysis`, `architecture`, `convergence`, `correction`, `economy`, `governance`, `operations`, `orchestrator` |
| `--risk` | `low` | `low`, `medium`, `high`, `critical`, `controlled` |
| `--description` | auto | One-line skill description |
| `--when-to-use` | `when needed` | Primary trigger phrase |

Generated `skill.yaml` includes all V6 fields (`triggers`, `forbidden`, `fallback_to`, `idempotent`, `context_policy`) with `schema_version: 1.1.0`. Fill in `triggers` and `forbidden` before committing.

```bash
# Create a new read-only analysis skill
sdd scaffold skill my-skill --category analysis --risk low \
  --description "Analyze X for Y"

# Create the matching slash command
sdd scaffold command my-skill --routes-to my-skill
```

Templates live in `.sdd/templates/` (deployed by wizard from `sdd_integration`). To add a skill to the canonical registry so it survives `--full-bootstrap`, add a `SkillDefinition` entry to `packages/core/sdd_runtime/src/sdd_runtime/skills.py`.

### Wizard

- `sdd wizard run` — Runs interactive setup wizard phases (7-phase pipeline). _(client primary; warns in master)_

The wizard now deploys `.sdd/templates/` to the target project, enabling `sdd scaffold skill` in generated workspaces.

### Documentation Artifacts

- sdd docs update: Discovers all markdown in /docs, synthesizes `mandate.spec`, `guidelines.dsl`, and `discovery-index.json` under `generated/client/build/docs-meta/`.
- sdd docs deploy: Deploys MkDocs static site (requires mkdocs installed). Aliases: `sdd docs`, `sdd documentation`.

Options for sdd docs update:

```bash
# Dry run — shows what would be generated without writing files
sdd docs update --dry-run
```

Options for sdd docs deploy:

```bash
# Default — force rebuild and deploy
sdd docs deploy

# Skip force flag
sdd docs deploy --no-force
```

### Release

- sdd release build: Builds release artifacts into `dist/`. _(master only — blocked in client)_

### Version

- sdd version: Shows the installed SDD CLI version.

### Diagnostics

- sdd doctor run: Executes protocol-based diagnostics using integration flow steps.

Runtime JSON example:

```bash
sdd --json runtime status | jq '.data.state,.data.ask_confidence'
```

Ask learning recommendation JSON example:

```bash
sdd --json ask "diagnose recurring correction blocks" \
  | jq '.data.learning_context,.data.learning_recommendations.signals,.data.learning_recommendations.next_actions'
```

Ask decision envelope JSON example:

```bash
sdd --json ask "fix governance drift in runtime" | jq '.data.ask_decision_envelope'
```

## Doctor Modes

The doctor command supports two execution modes:

- isolated (default): runs in a temporary isolated workspace.
- real: runs against the current repository workspace.

Examples:

```bash
# Default (isolated)
sdd doctor run

# Real workspace diagnostics
sdd doctor run --mode real

# Custom protocol file
sdd doctor run --spec packages/features/sdd_integration/src/sdd_integration/protocol/integration_flow.yaml
```

## Notes on Diagnostic Semantics

- Diagnostic status is protocol-step based and returns a score.
- A run only exits successfully when all protocol steps pass.
- The protocol now guards against false-green runs where pytest reports only skipped tests.

## Command Help

Use help per command for authoritative flags:

```bash
sdd --help
sdd doctor --help
sdd governance validate --help
```

## Related Documentation

See the project README and CHANGELOG for additional context.
