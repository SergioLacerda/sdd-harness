# 🛡️ SDD Harness

> **Executable Governance for the Agentic Era.**
> Transform architectural specifications into living contracts. Compile, validate, and audit agent behavior at runtime with industrial-grade determinism.

<div align="center">

| **Pipeline Status** | **Quality Gates** | **Ecosystem** |
|:---:|:---:|:---:|
| [![Health](https://github.com/SergioLacerda/sdd-harness/actions/workflows/health.yml/badge.svg?branch=main)](https://github.com/SergioLacerda/sdd-harness/actions/workflows/health.yml) | [![CodeQL](https://github.com/SergioLacerda/sdd-harness/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/SergioLacerda/sdd-harness/actions/workflows/codeql.yml) | [![Built with uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |
| [![Validation](https://github.com/SergioLacerda/sdd-harness/actions/workflows/sdd-validation.yml/badge.svg?branch=main)](https://github.com/SergioLacerda/sdd-harness/actions/workflows/sdd-validation.yml) | [![Release](https://github.com/SergioLacerda/sdd-harness/actions/workflows/release.yml/badge.svg)](https://github.com/SergioLacerda/sdd-harness/actions/workflows/release.yml) | [![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/) |
| [![Docs](https://github.com/SergioLacerda/sdd-harness/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/SergioLacerda/sdd-harness/actions/workflows/docs.yml) | [![Governance: SDD](https://img.shields.io/badge/governance-SDD-blueviolet)](docs/spec/canonical/core/) | [![License: CC BY-NC 4.0](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey)](LICENSE) |
| | [![Coverage](https://codecov.io/gh/SergioLacerda/sdd-harness/branch/main/graph/badge.svg)](https://codecov.io/gh/SergioLacerda/sdd-harness) | |

**[GitHub Pages](https://sergiolacerda.github.io/sdd-harness/)** • **[Onboarding](#-onboarding--govern-your-project-with-sdd)** • **[CLI Reference](#-cli-reference)** • **[Examples](examples/)** • **[Contributing](#-contributing)**

</div>

---

## 💎 Why SDD Harness?

> Without it, AI agents quietly violate their own mandates — specs rot into suggestions, contracts drift undetected, and compliance becomes a post-incident narrative instead of a runtime guarantee.

Spec-Driven Development (SDD) Harness is not just a tool—it's a **Governance Orchestrator**. It bridges the gap between static Markdown documentation and dynamic runtime enforcement for AI Agents.

- **📜 Specs as Code**: Your `docs/spec/` is the Single Source of Truth (SSoT). Human-readable, agent-executable.
- **⛓️ Execution Contracts**: Compiles mandates into versioned artifacts with cryptographic-grade fingerprints.
- **🛡️ Zero-Drift CI**: Automated contract tests (Golden Files) prevent accidental schema or logic evolution.
- **🤖 Agent-Agnostic**: Designed to govern any agentic framework through a unified CLI and runtime API.

---

## 🚀 Onboarding — Govern Your Project with SDD

> For teams and developers who want to add SDD governance to an existing project.

**Prerequisite:** [uv](https://docs.astral.sh/uv) must be installed on your machine.

This installation path works on Linux, macOS, and Windows and does not require cloning this repository.

```bash
# 1) Install the SDD CLI globally
uv tool install sdd-cli
```

```bash
# Alternative (legacy / Unix shell)
# Use this only when `uv` is unavailable.
curl -fsSL https://raw.githubusercontent.com/SergioLacerda/sdd-harness/main/install.sh | sh
```

```bash
# 2) Navigate to your project and run the interactive wizard
cd your-project
sdd wizard run
```

The wizard walks you through 4 phases: template generation → customization → compile → project structure.

First-run onboarding is zero-state aware:

- If `generated/` (or `generated/client/build/`) does not exist, the wizard bootstraps the minimum structure automatically.
- It creates `generated/client/build/docs-meta/`, `phase-1-choices/`, and `phase-2-input/` for Phase 1/2 flow.
- This step prepares templates and project scaffold only. Runtime activation still happens in the next step.

```bash
# 3) Bootstrap governance runtime in your project
sdd init --type client --name <your-project> --force
sdd governance generate --full-bootstrap
sdd skills --full-bootstrap --regenerate-seeds
```

```bash
# 4) Verify everything is healthy
sdd runtime status
sdd governance validate
```

**Paste this prompt into your AI agent after setup:**

```text
Read AGENTS.md, .sdd/agent-instructions.md, .sdd/source/governance-core.json,
and .sdd/source/mandates/mandates.md. Confirm:
1) active mandates loaded  2) current fingerprint  3) any drift/blockers
4) next governed action using sdd-* commands only.
```

Full onboarding guide and troubleshooting: [`docs/guides/CLIENT_ONBOARDING.md`](docs/guides/CLIENT_ONBOARDING.md)

---

## 🛠️ Local Setup — Contributing to SDD Harness

> For developers working on the SDD Harness codebase itself.

**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv), Git.

```bash
# 1) Clone and install all workspace dependencies (includes dev/test deps)
git clone https://github.com/SergioLacerda/sdd-harness.git
cd sdd-harness
make install
source .venv/bin/activate
```

```bash
# 2) Bootstrap local governance runtime
sdd init --type client --name local-dev --force
make hooks-install          # SDD hooks + pre-commit
make governance-bootstrap   # compile + generate + sign artifacts
```

```bash
# 3) Regenerate skills, commands and seeds
sdd skills --full-bootstrap --regenerate-seeds
```

```bash
# 4) Verify environment health
sdd runtime status --force
sdd governance validate
```

CLI reference: [`docs/spec/reference/commands/cli.md`](docs/spec/reference/commands/cli.md)

---

## 🛡️ Security & Trust

SDD Harness implements a **fail-closed** security model. Governance artifacts must be cryptographically signed to ensure integrity.

1. **Key Generation**: Create your identity key in `.sdd/trust/`.

    ```bash
    sdd governance keygen --key-id my-org-01
    ```

2. **Signing**: Sign artifacts before deployment.

    ```bash
    sdd governance sign --key-id my-org-01
    ```

3. **Audit**: Verify the security posture of your workspace.

    ```bash
    sdd governance audit --verbose
    ```

> [!IMPORTANT]
> Use `SDD_SIGNATURE_MODE=strict` in production to block any execution with invalid or missing signatures.

---

## 📋 CLI Reference

| Command | Description |
|:---|:---|
| `sdd governance audit` | Perform a Security Audit of the workspace |
| `sdd governance keygen`| Generate Ed25519 keys for signing |
| `sdd governance sign`  | Sign compiled artifacts with a private key |
| `sdd governance validate` | Validate compiled artifacts against source specs |
| `sdd governance compile`  | Compile mandates into msgpack artifacts |
| `sdd governance generate --full-bootstrap` | Compile + generate + keygen + sign + handshake |
| `sdd skills --full-bootstrap --regenerate-seeds` | Generate skills/commands/seeds artifacts and reconcile local managed seeds with `.sdd` registries |
| `sdd runtime status` | Holistic health check and "Doctor Score" |
| `sdd audit` | Summarize governance telemetry, top drift events, and token input/output ratios |
| `sdd skills list` | List capability-oriented governed skills |
| `sdd test run` | Execute unit, integration, and contract test suites |
| `sdd governance score` | Audit the project's compliance level |
| `sdd tools run` | Execute maintenance tools (uv-powered) |
| `sdd tools list` | List available maintenance tools |

### Agent Onboarding After Governance Activation

Once governance is active, agents can discover and run governed skills:

```bash
# List all available governed skills
sdd skills list

# Inspect a specific skill contract
sdd skills describe sdd-validate-governance

# Execute a governed skill
sdd skills run sdd-validate-governance
```

### Output Modes

```bash
# Structured output for automation
sdd --json runtime status | jq '.state,.drift'

# Governance validation in JSON
sdd --json governance validate | jq '.ok,.checks'

# Verbose mode (global)
sdd --verbose runtime status
```

## 🔌 Runtime API & Framework Integration

For integration with external orchestration frameworks (LangGraph, CrewAI, AutoGen), see:

- [`docs/guides/RUNTIME_API_INTEGRATION.md`](docs/guides/RUNTIME_API_INTEGRATION.md)

---

## 📂 Project Blueprint

```text
├── docs/spec/          <-- Canonical mandates, policies, and rules
├── packages/           <-- Modularized toolchain (core, compiler, cli, wizard)
├── tools/              <-- Maintenance and snapshot orchestration scripts
├── tests/              <-- Multi-layered testing (Contract, Integration, Unit)
└── generated/          <-- Immutable compiled artifacts (Git-ignored)
```

---

## 🤝 Contributing

We maintain a **World Class Engineering** environment where Humans and AI Agents collaborate under strict governance.

### 📜 The Golden Rule (P003)
>
> **"Agents propose, Humans dispose."**

Every change made by an AI Agent must pass the **Pre-Delivery Quality Gate (P004)** and be explicitly signed by a human using their Ed25519 auditor key. This cryptographic proof is enforced by the CI/CD pipeline and the `compliance.py` tool.

### Development Workflow

1. **Code**: Propose changes in `packages/` or `docs/spec/`.
2. **Verify**: Run `make pre-delivery` to satisfy all quality gates.
3. **Snapshot**: If spec changes are intentional, run `make update-golden-snapshots`.
4. **Review**: Submit changes for Human Review. **Agents are forbidden from git commits/pushes.**

---

## 📄 License

This project is licensed under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.

You may use, study, modify, and replicate this project for non-commercial purposes, provided that attribution to the original author is preserved.
Commercial use, resale, or commercialization requires prior written authorization from the copyright holder.

- **Repository:** <https://github.com/SergioLacerda/sdd-harness>
- **Docs (GitHub Pages):** <https://sergiolacerda.github.io/sdd-harness/>
- **Full license text:** [`LICENSE`](LICENSE)
