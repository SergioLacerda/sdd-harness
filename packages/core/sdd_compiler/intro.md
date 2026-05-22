# 🔨 SDD Binary Compiler (Core)

> **System Role:** Industrial-grade compiler for governance artifacts.

## 🎯 Overview

The `sdd-compiler` is the "Forge" of the SDD framework. It is responsible for **Phase 2** of the compilation pipeline: taking structured governance data (JSON) and transforming it into highly optimized, tamper-evident binary artifacts (MessagePack).

## 🛠️ Core Capabilities

1.  **Binary Compilation**: Converts DSL/JSON structures into MessagePack format, providing 65%+ size reduction and 3-4x faster parsing for AI agents.
2.  **Optimization Layer**:
    *   **String Deduplication**: Uses a centralized `StringPool` to eliminate redundant text, drastically reducing token footprint.
    *   **Lexical Validation**: Ensures DSL files (`.spec`, `.dsl`) strictly follow architectural syntax.
3.  **Governance Ingestion**: Capable of importing governance items from structured Markdown and legacy formats.
4.  **DSL Generation**: Provides programmatic tools to generate `.spec` and `.dsl` source files from code.
5.  **Integrity & Security**:
    *   **Fingerprinting**: Generates SHA-256 hashes for all artifacts to detect "drift" or manual tampering.
    *   **SALT Implementation**: Uses core fingerprints as salt for client-level governance to ensure hierarchical consistency.
4.  **RTK (Runtime Telemetry Kit)**: Integrated sub-layer for advanced pattern deduplication.

## 🚀 Pipeline Integration

This package is orchestrated by `sdd-core` as the final stage of the build process:

1.  **Phase 1 (Pipeline)**: `sdd-integration` builds the initial JSON structure.
2.  **Phase 2 (Compiler)**: `sdd-compiler` (this package) generates the final binary artifacts.
3.  **Outcome**: Ready-to-deploy `.msgpack` files in `.sdd/runtime/`.

## 📂 Architecture

```
sdd_compiler/
├── dsl_compiler.py        # Core parser and lexical analyzer
├── governance_compiler.py  # Orchestrator for multi-artifact builds
├── msgpack_encoder.py     # Binary serialization logic
└── runtime_telemetry_kit/ # Telemetry optimization engine
```

---
**Standard:** World Class Engineering - v3.0
**Status:** Mandatory Core Component
