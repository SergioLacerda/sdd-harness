# ADR-007: Implementation Guardrails - Design First, Code Follows

## Status
- **Accepted** ✅
- Proposed: 2026-04-21
- Accepted: 2026-04-21
- Review Date: 2026-10-21

---

## Context

**Problem**:
Previous implementations experienced gaps between planning, documentation, and code execution:
- Vague planning without written specifications
- Documentation interpreted by agents (error-prone)
- Code didn't match original intent
- Rework required due to ambiguity
- Architects couldn't verify alignment without extensive review

**Scale**: v3.1-beta.1 and all future releases (v3.0-v3.2+)

**Impact**:
- Must ensure zero ambiguity
- Must enable architect/product owner verification
- Must support multiple agents working in parallel
- Must prevent scope creep during implementation

---

## Decision

**Implement 5 Implementation Guardrails (MANDATORY for all features)**:

### GUARDRAIL 1: Design Review (Before Code)

```
Step 1: Design Document (Written First)
  ├─ File: FEATURE_DESIGN_<name>.md
  ├─ Location: EXECUTION/spec/guides/design/
  ├─ Content:
  │  ├─ Problem statement (what are we solving?)
  │  ├─ Proposed solution (how will we solve it?)
  │  ├─ Architecture diagram (visual context)
  │  ├─ Data flow (how data moves)
  │  ├─ Dependencies (what it needs)
  │  ├─ Edge cases (what can go wrong?)
  │  └─ Backward compatibility notes
  └─ Status: DRAFT

Step 2: Architect Review (Owner Approval)
  ├─ Architect reads design
  ├─ Architect confirms: "This matches intention?"
  ├─ Architect signals: APPROVED ✅ or REVISE ❌
  └─ No code starts until ✅

Step 3: Specification Lock
  ├─ Design marked: LOCKED
  ├─ Changes during implementation require approval
  ├─ Prevents scope creep
  └─ Ensures alignment stays intact
```

### GUARDRAIL 2: Specification Document (Technical Spec)

```
Spec Document MUST include:

1. DATA STRUCTURES
   ├─ Input format (type, validation rules)
   ├─ Output format (type, validation rules)
   └─ Internal representations

2. ALGORITHMS
   ├─ Steps in order
   ├─ Complexity analysis
   ├─ Edge case handling
   └─ Error scenarios

3. INTEGRATION POINTS
   ├─ What calls this?
   ├─ What does this call?
   ├─ Dependencies
   └─ State management

4. TEST CASES (Written Before Code!)
   ├─ Happy path
   ├─ Edge cases
   ├─ Error cases
   └─ Performance requirements

5. REFERENCE IMPLEMENTATION
   ├─ Pseudo-code or working example
   └─ Demonstrates correctness

File: docs/specs/COMPONENT_<name>.md
```

### GUARDRAIL 3: Code Matches Design

```
Code Review Checklist (Before Merge):

[ ] Code implements DESIGN as specified
[ ] Code implements SPEC as specified
[ ] No features added beyond scope
[ ] All edge cases handled
[ ] All error paths tested
[ ] No ambiguity in logic
[ ] Architecture layers respected
    ├─ MANDATE layer unchanged?
    ├─ GUIDELINES layer customizable?
    ├─ OPERATIONS layer stateful?
[ ] No breaking changes to APIs
[ ] Documentation updated
[ ] Tests all passing (111/111+)
[ ] No new warnings or errors
```

### GUARDRAIL 4: Tests Verify Decisions

```
For each DESIGN DECISION, there's a TEST:

Design says:     "MANDATE is immutable"
         ↓
Test:            test_mandate_immutability()
         ↓
Validates:       MANDATE cannot be changed at runtime

Design says:     "RTK patterns match 50+ types"
         ↓
Test:            test_rtk_pattern_coverage()
         ↓
Validates:       All 50+ patterns work correctly

Test Convention:
  FEATURE_DESIGN_<name>.md → test_design_<name>.py
```

### GUARDRAIL 5: Documentation Updated with Code

```
WHEN CODE CHANGES:

1. Design doc updated (if design changed)
2. Spec updated (if spec changed)
3. API_REFERENCE.md updated (if API changed)
4. Code updated with comments
5. Tests updated to match new behavior
6. User guide updated (if user-facing)
7. CHANGELOG.md updated (for release)

NO DOCUMENTATION LEFT BEHIND!
```

---

## Implementation Workflow

```
Feature Request Received
    ↓
1. DESIGN PHASE (Agent + Architect)
   ├─ Write FEATURE_DESIGN_<name>.md
   ├─ Include diagrams, data flow
   ├─ Architect reviews & approves
   └─ Design LOCKED
    ↓
2. SPEC PHASE (Agent)
   ├─ Write COMPONENT_<name>.md
   ├─ Include data structures, algorithms
   ├─ Include test cases (before code!)
   └─ Ready for implementation
    ↓
3. DEVELOPMENT PHASE (Agent)
   ├─ Implement exactly to spec
   ├─ Code comments reference design
   ├─ Write tests from spec
   ├─ All tests green (111/111+)
   └─ Code review against design
    ↓
4. DOCUMENTATION PHASE (Agent)
   ├─ Update all docs together
   ├─ Add examples if applicable
   ├─ Update CHANGELOG
   ├─ Verify documentation complete
   └─ Ready for review
    ↓
5. ARCHITECT REVIEW (Architect/Owner)
   ├─ Verify implementation matches design
   ├─ Verify tests pass
   ├─ Verify documentation complete
   ├─ Sign off: APPROVED or REVISE
   └─ NO AUTO-COMMIT until approval
```

---

## Why Mandatory?

1. **Zero Ambiguity**
   - Everything written before code
   - Architect can verify alignment early
   - No surprises at integration

2. **Architect Control**
   - Can catch scope creep
   - Can prevent architectural drift
   - Can ensure consistency

3. **Reversibility**
   - If design changes, easy to revert
   - Can backup critical files before implementation
   - Can rollback to known-good state

4. **Parallel Work**
   - Multiple agents can work on different features
   - Design approval is the sync point
   - No conflicts if design is clear

5. **Quality**
   - Tests written from spec
   - Code verified against design
   - Documentation not forgotten

---

## Consequences

### Positive ✅
- Zero ambiguity between design and code
- Architect can control scope and quality
- Early detection of design flaws
- Easy rollback to known-good state
- Support for parallel agent work
- No surprises at integration time
- Clear handoff points for review

### Negative ⚠️
- Slower initial startup (design phase)
- More documentation upfront
- Requires discipline to follow
- Can't start coding immediately

---

## Implementation Status

✅ v3.1-beta.1: All 5 guardrails apply
✅ v3.0: Design/spec phases applied retrospectively
⏳ v3.2+: Automated enforcement via CI/CD

---

## Related Decisions

- ADR-008: Code Review Governance (Architect reviews before commit)
- ADR-001: Clean Architecture (Design must respect 8-layer model)
- ADR-003: Ports-Adapters (Design must specify adaptation boundaries)

---

## See Also

- EXECUTION/spec/guides/design/ (design templates)
- EXECUTION/spec/guides/operational/ (spec templates)
- IMPLEMENTATION_GUARDRAILS.md (detailed process guide)
