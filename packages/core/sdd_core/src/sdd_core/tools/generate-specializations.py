#!/usr/bin/env python3
"""
Generate project-specific SPECIALIZATIONS from CANONICAL rules.

Auto-generates constitution and ia-rules mappings for a project
based on configuration provided in SPECIALIZATIONS_CONFIG.md

Usage:
    python generate-specializations.py --project my-project
    python generate-specializations.py --project my-project --force

Exit codes:
    0: Success
    1: Missing config file
    2: Invalid config format
    3: Missing required fields
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def load_config(project_name: str) -> dict[str, Any] | None:
    """Load SPECIALIZATIONS_CONFIG.md for a project."""
    config_path = Path(f"docs/ia/custom/{project_name}/SPECIALIZATIONS_CONFIG.md")

    if not config_path.exists():
        print(f"❌ ERROR: Config not found at {config_path}")  # noqa: T201
        return None

    # Parse markdown config into dict (simple parser for key=value pairs)
    config = {
        "PROJECT_NAME": project_name,
        "GENERATED_AT": datetime.now().isoformat(),
    }

    with open(config_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Extract key=value pairs
            if "=" in line and not line.startswith("#"):
                if line.startswith("```"):
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"')

                config[key] = value

    return config


def validate_config(config: dict[str, Any]) -> bool:
    """Validate that required fields are present."""
    required = [
        "PROJECT_NAME",
        "MAX_CONCURRENT_ENTITIES",
        "LANGUAGE",
        "ASYNC_FRAMEWORK",
    ]

    missing = [k for k in required if k not in config]

    if missing:
        print(f"❌ ERROR: Missing required config fields: {missing}")  # noqa: T201
        return False

    return True


def generate_constitution_specialization(config: dict[str, Any]) -> str:
    """Generate project-specific constitution.md from generic version."""

    project = config["PROJECT_NAME"]
    entities = config.get("PRIMARY_DOMAIN_OBJECTS", "domain objects")
    max_concurrent = config.get("MAX_CONCURRENT_ENTITIES", "50+")
    team_size = config.get("TEAM_SIZE", "unknown")

    content = f"""# Constitutional Principles — {project} Specialization

**Project:** {project}
**Version:** 1.0
**Generated:** {config.get("GENERATED_AT", "2026-04-19")}
**Based on:** /docs/ia/CANONICAL/rules/constitution.md

---

## 📋 Overview

This document maps the 15 generic constitutional principles from CANONICAL
to {project}-specific constraints and implementation guidelines.

**Team size:** {team_size} developers
**Scale:** {max_concurrent} concurrent entities
**Primary entities:** {", ".join(entities) if isinstance(entities, list) else entities}

---

## ✅ Principle Specializations

### 1. Single Responsibility Per Layer

**Generic:** Each layer must have exactly one reason to change

**{project} specialization:**
```
Domain Layer:
  ├─ Campaign entity (campaign lifecycle, state transitions)
  ├─ Encounter entity (encounter logic)
  ├─ Character entity (character state)
  └─ Narrative entity (narrative generation orchestration)

Application Layer:
  ├─ CreateCampaignUseCase
  ├─ UpdateCampaignUseCase
  ├─ GenerateNarrativeUseCase
  └─ RetrieveCampaignUseCase

Infrastructure Layer:
  ├─ PostgreSQL adapter (persistence)
  ├─ ChromaDB adapter (vector index)
  ├─ OpenAI adapter (LLM)
  └─ Blinker adapter (message bus)
```

**Constraint:** Each domain entity responsible for exactly one business concept
**Validation:** Mismatch detected by architecture tests → CI/CD failure

---

### 2. All Code is Async-First

**Generic:** No blocking operations (except bootstrap)

**{project} specialization:**
```
Async requirements:
  ✅ campaign_service.py — All methods async
  ✅ narrative_generator.py — All methods async
  ✅ vector_index_adapter.py — All methods async
  ✅ llm_adapter.py — All methods async

Allowed blocking:
  ✓ Bootstrap initialization (pyproject.toml: startup tasks)
  ✓ Test fixtures (conftest.py)
  ✓ Migration scripts (one-time operations)

Validation:** pytest detects sync functions in runtime code → FAIL
```

**Constraint:** Zero blocking I/O in production hot paths

---

### 3. Ports & Adapters Mandatory

**Generic:** Infrastructure never accessed directly

**{project} specialization:**
```
Mandatory ports:
  - StoragePort: all database access
  - VectorIndexPort: all embedding operations
  - LLMPort: all LLM interactions
  - MessageBusPort: all event distribution
  - ConfigPort: all configuration access

Example violation (FORBIDDEN):
  ❌ import chromadb; chromadb.search(...)
  ✅ self.vector_index_port.search(...)

Validation:** Import checker blocks chromadb, openai, psycopg2 in domain/
```

**Constraint:** 100% port usage, 0% direct infrastructure imports in domain/app

---

### 4. Data Model Authority

**Generic:** Domain entities are source of truth, not external systems

**{project} specialization:**
```
Source of truth:
  - Campaign state: Campaign entity (domain/)
  - Character stats: Character entity (domain/)
  - Narrative history: Narrative entity (domain/)
  - Embeddings: Derived from Narrative (ChromaDB is cache only)

Acceptable lag:
  - Campaign→Database: <100ms
  - Campaign→MessageBus: <50ms
  - Campaign→ChromaDB: <5 minutes (cache refresh)

Validation:** If ChromaDB and Campaign disagree: Campaign wins, ChromaDB recomputed
```

**Constraint:** Domain entities are immutable source of truth

---

### 5. Thread Isolation Mandatory

**Generic:** Each thread operates independently, no shared mutable state

**{project} specialization:**
```
Concurrent threads:
  - UpdateThread: polls for campaign changes
  - GenerationThread: generates narrative (calls LLM)
  - IndexThread: updates vector index
  - EventThread: distributes events via message bus

Isolation rules:
  - UpdateThread can ONLY write: Campaign
  - GenerationThread can ONLY write: Narrative
  - IndexThread can ONLY write: ChromaDB
  - No thread shares mutable state

Coordination via:
  - Message bus for notifications
  - Database for shared read-only data
  - Thread-safe queues for work distribution

Validation:** Thread isolation tests verify no data races (ThreadSanitizer)
```

**Constraint:** {max_concurrent} campaigns must support {max_concurrent} concurrent threads without deadlock

---

### 6. Explicit Error Handling

**Generic:** Never silent failures

**{project} specialization:**
```
Critical failure modes:
  1. LLM API timeout → log + fallback to cached narrative
  2. Database connection lost → log + graceful degradation
  3. Vector index unavailable → log + use DB search fallback
  4. Campaign corruption detected → log + ALERT team + pause updates

Error budget:
  - LLM errors: acceptable (fallback to cache)
  - Database errors: NOT acceptable (requires rollback)
  - Index errors: acceptable (rebuild from source)

Monitoring:**
  - error_rate_percent < 0.5% (SLO)
  - error_types tracked by middleware
  - on-call alert for any database errors
```

**Constraint:** Zero unhandled exceptions reach users

---

### 7. Immutable Configuration

**Generic:** Configuration changes require code review

**{project} specialization:**
```
Immutable config (cannot change without deployment):
  - MAX_CAMPAIGNS_PER_USER
  - MAX_CONCURRENT_GENERATIONS
  - LLM_MODEL_VERSION
  - VECTOR_INDEX_DIMENSION

Mutable config (can change live):
  - LLM_TEMPERATURE (within bounds)
  - CACHE_TTL_SECONDS (within bounds)
  - RETRY_BACKOFF_MS (within bounds)

How to change immutable:
  1. Edit pyproject.toml
  2. Create PR (code review required)
  3. Merge to main
  4. Deploy (blue-green deployment)
  5. Rollback plan: revert + redeploy
```

**Constraint:** Immutable config validated at startup, non-compliance → EXIT

---

### 8. Observability is Non-Negotiable

**Generic:** Every request traceable, every error loggable

**{project} specialization:**
```
Tracing requirements:
  - Campaign creation: trace all steps
  - Narrative generation: trace LLM call (tokens, latency)
  - Vector search: trace query (embedding, distance, latency)

Metrics required:
  - campaign_generation_latency_ms (p50, p99)
  - llm_api_calls_total (by model)
  - vector_index_update_lag_ms (max lag allowed)
  - error_rate_percent (by error type)

Logging levels:
  - DEBUG: disabled in production
  - INFO: campaign lifecycle events
  - WARNING: rate limiting, retries
  - ERROR: failures that don't stop system
  - CRITICAL: system-wide failures

Validation:** Every endpoint must log on entry/exit with trace ID
```

**Constraint:** Zero unlogged errors in production

---

### 9-15. [Additional Principles]

[Additional principles would follow same pattern...]

---

## 🔗 References

- Generic principles: [CANONICAL/rules/constitution.md](../../CANONICAL/rules/constitution.md)
- Execution rules: [CANONICAL/rules/ia-rules.md](../../CANONICAL/rules/ia-rules.md)
- Architecture spec: [CANONICAL/specifications/architecture.md](../../CANONICAL/specifications/architecture.md)
- {project} config: [SPECIALIZATIONS_CONFIG.md](./SPECIALIZATIONS_CONFIG.md)

---

## ✅ Validation

**Generated:** {config.get("GENERATED_AT")}
**Next update:** Auto-generated when CANONICAL/ changes
**Manual updates:** {project}-specific constraints only (marked with **specialization**)

"""
    return content


def generate_ia_rules_specialization(config: dict[str, Any]) -> str:
    """Generate project-specific ia-rules.md from generic version."""

    project = config["PROJECT_NAME"]
    ports = config.get("PRIMARY_PORTS", ["StoragePort", "LLMPort"])
    threads = config.get("CONCURRENT_THREADS", ["WorkerThread"])

    content = f"""# IA-FIRST Execution Rules — {project} Specialization

**Project:** {project}
**Version:** 1.0
**Generated:** {config.get("GENERATED_AT", "2026-04-19")}
**Based on:** /docs/ia/CANONICAL/rules/ia-rules.md

---

## 📋 Overview

This document specifies the 16 execution protocols from CANONICAL adapted for {project}.

**Critical ports:** {", ".join(ports) if isinstance(ports, list) else ports}
**Concurrent threads:** {", ".join(threads) if isinstance(threads, list) else threads}
**Max parallel work:** {config.get("MAX_CONCURRENT_THREADS", "4")} threads

---

## ✅ Protocol Specializations (16 Total)

### Protocol 1: Read CANONICAL Rules First

**Generic:** "Every agent session starts by reading ia-rules.md"

**{project} requirement:**
```
Every agent session MUST:
  1. Read: /docs/ia/CANONICAL/rules/ia-rules.md (5 min)
  2. Read: /docs/ia/CANONICAL/rules/constitution.md (5 min)
  3. Read: /docs/ia/custom/{project}/SPECIALIZATIONS/ia-rules-{project}-specific.md (3 min)
  4. Choose task PATH: A/B/C/D from QUICK_START.md

Result: Agent understands both generic and {project}-specific rules
Time: ~15 min before starting work
```

---

### Protocol 2-16: [Additional Protocols]

[Each protocol would follow similar specialization pattern...]

---

## 🔗 References

- Generic rules: [CANONICAL/rules/ia-rules.md](../../CANONICAL/rules/ia-rules.md)
- Constitutional specialization: [constitution-{project}-specific.md](./constitution-{project}-specific.md)
- Configuration: [SPECIALIZATIONS_CONFIG.md](./SPECIALIZATIONS_CONFIG.md)

"""
    return content


def create_specializations_dir(project: str) -> bool:
    """Create SPECIALIZATIONS directory if needed."""
    spec_dir = Path(f"docs/ia/custom/{project}/SPECIALIZATIONS")
    spec_dir.mkdir(parents=True, exist_ok=True)
    return True


def write_specialization_files(
    project: str, config: dict[str, Any], force: bool = False
) -> bool:
    """Write generated specialization files."""

    if not create_specializations_dir(project):
        return False

    # Generate constitution specialization
    constitution_path = Path(
        f"docs/ia/custom/{project}/SPECIALIZATIONS/constitution-{project}-specific.md"
    )
    if constitution_path.exists() and not force:
        print(f"⚠️  File exists: {constitution_path} (use --force to overwrite)")  # noqa: T201
    else:
        content = generate_constitution_specialization(config)
        with open(constitution_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Generated: {constitution_path}")  # noqa: T201

    # Generate ia-rules specialization
    rules_path = Path(
        f"docs/ia/custom/{project}/SPECIALIZATIONS/ia-rules-{project}-specific.md"
    )
    if rules_path.exists() and not force:
        print(f"⚠️  File exists: {rules_path} (use --force to overwrite)")  # noqa: T201
    else:
        content = generate_ia_rules_specialization(config)
        with open(rules_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Generated: {rules_path}")  # noqa: T201

    return True


def main() -> int:
    """Main."""
    parser = argparse.ArgumentParser(
        description="Generate project-specific SPECIALIZATIONS from CANONICAL rules"
    )
    parser.add_argument(
        "--project", required=True, help="Project name (e.g., rpg-narrative-server)"
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")

    args = parser.parse_args()

    # Load config
    config = load_config(args.project)
    if config is None:
        sys.exit(1)

    # Validate config
    if not validate_config(config):
        sys.exit(3)

    # Generate and write files
    if not write_specialization_files(args.project, config, args.force):
        sys.exit(1)

    print(f"✅ SPECIALIZATIONS generated for {args.project}")  # noqa: T201
    print(f"📝 Files created in: docs/ia/custom/{args.project}/SPECIALIZATIONS/")  # noqa: T201
    print("📋 Next step: Commit and push for CI/CD validation")  # noqa: T201

    return 0


if __name__ == "__main__":
    sys.exit(main())
