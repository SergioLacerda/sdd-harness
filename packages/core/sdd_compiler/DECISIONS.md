# SDD Compiler — Decision Log

**Module:** `packages/core/sdd_compiler`
**Purpose:** Parse DSL specs (mandate.spec, guidelines.dsl), compile to MessagePack artifacts
**Owner:** @SergioLacerda

---

## DEC-2026-001: Regex-Based Parsing (Not Full Parser) (2026-01-15)

**Decision:** Use regex for mandate/guideline parsing, not a proper tokenizer/AST builder

**Rationale:**
- Specs are Markdown, loosely formatted, not strict DSL
- Regex is simple, readable, low maintenance
- 99% of real-world specs match the patterns
- Parser would add complexity, dependencies, build step
- Can upgrade to proper parser later if needed (Phase 6+)

**Trade-offs:**
- Pro: Fast, simple, no deps
- Con: Fragile with edge cases, hard to extend to complex DSL

**Patterns:**
- Mandate: `^\s*-\s*\[([MP]\d{3})\].*` (MD list item with ID)
- Guideline: `guideline\s+(G\d+)\s*\{(.*?)\}` (loose struct syntax)

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** DSLValidator, DSLParser in dsl_compiler.py

**Future:** If specs become more complex, design real parser (Phase 6)

---

## DEC-2026-002: MessagePack Over JSON (2026-02-01)

**Decision:** Serialize compiled artifacts as MessagePack binary, not JSON

**Rationale:**
- Speed: 3-4× faster deserialization vs JSON
- Size: ~50% smaller binary (less storage, faster download)
- Format: Msgpack-python is stable, well-tested
- Backward compat: Can always convert to JSON if needed

**Consequence:** Artifacts are binary (.bin), not human-readable

**Implementation:** DSLCompiler outputs msgpack_encoder.encode()

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** DSLCompiler.compile(), msgpack_encoder.py

**Alternative rejected:** Protobuf — over-engineered, adds build complexity

**Future consideration:** ADR-0001 (Phase 5.4) considers upgrade to Protobuf for versioning

---

## DEC-2026-003: String Deduplication Pool (2026-02-15)

**Decision:** Extract repeated strings into pool, store indices instead of full strings

**Rationale:**
- Compression: Strings like "description:", "category:" repeated 1000+ times
- Size reduction: 30-40% less space for typical specs
- Memory: Pool lookup is O(1), efficient
- Observable: Can measure compression ratio

**Example:**
```
Before: [{"id": "M001", "title": "Mandate 1", "description": "..."},
         {"id": "M002", "title": "Mandate 2", "description": "..."}]
After:  {"strings": ["M001", "Mandate 1", "...", "M002", "Mandate 2", ...],
         "items": [{"id_idx": 0, "title_idx": 1, "desc_idx": 2},
                   {"id_idx": 3, "title_idx": 4, "desc_idx": 2}]}
```

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** StringPool in dsl_compiler.py

---

## DEC-2026-004: Compile Subprocess with 15s Timeout (2026-03-01)

**Decision:** Each compile (mandate, guidelines) runs in subprocess with 15 second timeout

**Rationale:**
- Safety: Malformed spec can't hang the main process
- Isolation: Compile errors don't crash integrator
- Observable: Can measure compile time
- Margin: 15s = 300× safety margin for typical specs (50ms)

**Consequence:** Timeout → catch, log, mark as failed, continue

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** SDDIntegrator.compile_mandate(), compile_guidelines()

**Tuning:** If large specs timeout, increase to 30s or split spec

---

## DEC-2026-005: Mandatory Validation, Optional Compilation (2026-03-10)

**Decision:** Always validate syntax; compilation proceeds only if validation passes

**Rationale:**
- Fast-fail: Catch errors early before msgpack encoding
- Two-phase: Validation errors ≠ compiler errors
- Recovery: User can fix spec incrementally
- Testing: Can test validation without full compile

**Consequence:** Invalid spec → no artifacts generated, explicit error message

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** DSLValidator.validate_dsl()

---

## DEC-2026-006: Profile-Separated Compiled Artifact Directories (2026-05-17)

**Decision:** Compiled artifacts are written to the directory matching the active profile:
- `master` profile → `generated/master/compiled/`
- `client` profile (default) → `generated/client/compiled/`

The active profile is resolved from `.sdd/profile` or the `SDD_PROFILE` env var.
`sdd governance compile --profile master` forces master output without mutating the workspace profile.

**Rationale:**
- Clear separation: master artifacts are framework-level (immutable); client artifacts are instance-level (mutable/customizable)
- Default behavior (profile=client) compiles to `generated/client/compiled/`, matching the typical developer workflow
- Master compilation is an explicit, intentional operation (requires `--profile master`)
- Runtime consumers (`sdd ask`, `GovernanceLoader`) automatically read from the correct directory based on the active profile

**Previous decision (2026-03-15):** All artifacts in `generated/master/compiled/` — superseded because it conflated framework artifacts with per-instance artifacts.

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** GovernanceOrchestrator.__init__, GovernanceLoader.__init__, sdd governance compile --profile

---

## DEC-2026-007: Metadata.json Audit Trail (2026-03-20)

**Decision:** Generate metadata-core.json with: source hashes, compilation timestamp, audit trail

**Rationale:**
- Reproducibility: Can compare source hash to verify no changes
- Traceability: When was this artifact compiled?
- Integrity: Audit trail shows who built it
- Integration: Runtime loads metadata to validate artifact

**Fields:**
- version: "3.0.0"
- compiled_at: ISO timestamp
- source: {mandate_spec_hash, guidelines_dsl_hash}
- statistics: {mandates_count, guidelines_count}
- artifacts: {mandate_bin, guidelines_bin} (exists? flags)
- audit_trail: [{timestamp, action, status}]

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** SDDIntegrator.generate_metadata()

---

## DEC-2026-008: Incremental Compilation with .compile-state.json (2026-05-11)

**Decision:** Skip compilation if source hashes unchanged and artifacts exist

**Rationale:**
- Performance: 60% of builds have unchanged specs
- Savings: Skip 20ms compile per no-op build
- Cache: .compile-state.json tracks source hashes
- Safety: Verify artifacts exist before skipping

**Implementation:** check_incremental_compilation(), CompileState class

**Consequence:** Second build with same spec → instant (artifact reused)

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** Phase 5.3 Incremental Compilation

---

## DEC-2026-009: Category Mapping (Semantic IDs) (2026-04-05)

**Decision:** Map category names to numeric IDs (architecture=1, security=4, etc.)

**Rationale:**
- Compression: Store 1 byte instead of 15 bytes ("architecture")
- Normalization: Typos caught (unknown category → error)
- Query: Can filter by category ID efficiently
- Extensible: Add new categories without breaking format

**Category Map:**
- 1: architecture
- 2: general
- 3: performance
- 4: security
- 5: git
- 6: documentation
- 7: testing
- 8: naming
- 9: code-style

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-010: Compression Ratio Metrics (2026-05-01)

**Decision:** Track and report compression ratio: (input_size - output_size) / input_size

**Rationale:**
- Observability: Know if string pool/deduplication working
- Optimization: Data for tuning compression
- Quality: Typical ratio is 35-40% (good signal)
- Regression: If ratio drops below 30%, investigate

**Example:**
```
Input: 1.8 MB mandate.spec
Output: 24 KB msgpack artifact
Ratio: (1.8 - 0.024) / 1.8 = 98.7% (excellent compression)
```

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** CompilationMetrics.compression_ratio

---

## DEC-2026-011: Telemetry: Mandates/Guidelines Compiled Count (2026-03-15)

**Decision:** Emit telemetry event: number of mandates and guidelines compiled

**Rationale:**
- Observability: Monitor spec growth (should increase predictably)
- Alert: If count suddenly drops, investigate
- Analytics: Trends in mandate/guideline count
- Quality: Ensure compilation didn't lose items

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** Phase 3 Token Economy, CompilationMetrics

---
