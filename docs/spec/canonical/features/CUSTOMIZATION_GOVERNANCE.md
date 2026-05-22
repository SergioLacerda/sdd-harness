# Governance: Constitution Customization

**Type:** IMMUTABLE CORE
**Category:** Governance / Architecture

---

## 🏗️ Stability Levels

### ✅ Immutable Core (DO NOT CHANGE)
These 5 principles must remain in every SDD implementation to maintain framework integrity:
1. **Clean Separation of Concerns**: Business logic isolated from infrastructure.
2. **Explicit Governance**: Rules documented and enforced, not implicit.
3. **Traceability**: Decisions linked to implementation via ADRs.
4. **Context Isolation**: Project boundaries strictly enforced.
5. **Validation First**: Tests/Quizzes define completion.

---

## 🚀 Flexible Customizations (The User Choice)
Users may customize the following based on project needs:
- **Number of Layers**: 4, 6, or 8 layers depending on complexity.
- **Async Strategy**: Waive "Async-First" for embedded or sequential CLI tools.
- **Testing Depth**: Adjust thresholds based on project risk.
- **Port Definitions**: Customize adapter contracts for specific tech stacks.

---

## 🔁 Customization Process

1. **Choose Baseline**: ULTRA-LITE, LITE, or FULL.
2. **Identify Constraints**: Scale, I/O patterns, and team size.
3. **Document Deviations**: Explain *What*, *Why*, and *How* the deviation is implemented.
4. **Automated Validation**: Ensure the custom rules are testable.

---

## 🚨 Red Flags
- ❌ Skipping tests because they are "inconvenient".
- ❌ Removing all validation steps.
- ❌ Hiding technical debt to make a status look green.
