# Agent Tools & Scripts

This folder contains executable tools for agent onboarding and validation.

## 📝 Available Scripts

### `validate_quiz.py` — Validation Quiz Runner

**Purpose**: Interactive quiz to verify ia-rules.md understanding

**Usage**:
```bash
python packages/.sdd-wizard/SCRIPTS/validate_quiz.py
```

**What it does**:
1. Asks 5 questions (multiple choice)
2. Gives immediate feedback
3. Shows score
4. Logs result to tracking file
5. Tells you if you passed (≥80%)

**Output**:
- Terminal: Pass/fail, score, next steps
- File: `/.sdd/current-system-state/_quiz_tracking.json` (appended)

**Exit codes**:
- `0` = Passed (≥80%)
- `1` = Failed (<80%)

**For CI/CD**:
```bash
python packages/.sdd-wizard/SCRIPTS/validate_quiz.py && echo "✅ Agent validated" || echo "❌ Agent needs re-training"
```

---

### `validate_governance.py` — Governance Validator ⭐ NEW

**Purpose**: Verify ia-rules.md and governance files are intact

**Usage**:
```bash
python packages/.sdd-wizard/SCRIPTS/validate_governance.py
```

**What it checks**:
1. ✓ All required governance files exist
   - ia-rules.md
   - GOVERNANCE_RULES.md
   - RUNTIME_STATE.md
   - specs/constitution.md
2. ✓ ia-rules.md has 8+ core protocols (Never bypass ports, Thread isolation, Async-first, etc.)
3. ✓ Governance files haven't been gutted (min size checks)
4. ⚠️ Warns if files are suspiciously small

**Exit codes**:
- `0` = All governance checks pass
- `1` = Governance violation detected

**For CI/CD**:
```bash
python packages/.sdd-wizard/SCRIPTS/validate_governance.py || exit 1
```

---

### `validate_adrs.py` — ADR Validator ⭐ NEW

**Purpose**: Verify all 6 ADRs exist and have required sections

**Usage**:
```bash
python packages/.sdd-wizard/SCRIPTS/validate_adrs.py
```

**What it checks**:
1. ✓ All 6 ADRs exist:
   - ADR-001: Clean Architecture 8-Layer
   - ADR-002: Async-First No Blocking
   - ADR-003: Ports & Adapters Pattern
   - ADR-004: Vector Index Strategy
   - ADR-005: Thread Isolation Mandatory
   - ADR-006: Append-Only Storage
2. ✓ Each ADR has required sections:
   - Status
   - Context
   - Decision
   - Consequences
   - Alternatives Considered
   - Current Implementation Status
3. ✓ ADR quality metrics (rationale, consequences, review dates)

**Exit codes**:
- `0` = All ADRs valid
- `1` = ADR violation detected

**For CI/CD**:
```bash
python packages/.sdd-wizard/SCRIPTS/validate_adrs.py || exit 1
```

---

## 📊 Tracking File

Results are logged to:
```
/.sdd/current-system-state/_quiz_tracking.json
```

Format: JSON Lines (one entry per line)

```json
{
  "session_id": "uuid-here",
  "timestamp": "2026-04-18T10:30:00Z",
  "score": 5,
  "total": 5,
  "percentage": 100,
  "passed": true,
  "attempt_number": 1,
  "time_minutes": 4.2,
  "questions_correct": [1, 2, 3, 4, 5],
  "questions_incorrect": []
}
```

---

## 📈 Analyzing Results

**Show summary**:
```bash
cat .sdd/current-system-state/_quiz_tracking.json | jq -s 'group_by(.passed) | map({passed: .[0].passed, count: length})'
```

**Show pass rate on first attempt**:
```bash
cat .sdd/current-system-state/_quiz_tracking.json | \
  jq -s '[.[] | select(.attempt_number == 1) | .passed] | {total: length, passed: map(select(. == true)) | length, rate: (map(select(. == true)) | length) / length * 100}'
```

**Show most failed questions**:
```bash
cat .sdd/current-system-state/_quiz_tracking.json | \
  jq -s '[.[] | .questions_incorrect[]?] | group_by(.) | sort_by(-length) | map({question: .[0], failures: length})'
```

---

## 🔧 Future Scripts (Planned)

- `validate_tests.py` — Verify test coverage in key modules
- `validate_conventions.py` — Check naming conventions compliance
- `validate_layers.py` — Verify 8-layer architecture compliance

---

## ⚡ Using Validators in CI/CD

### GitHub Actions Example

```yaml
- name: Validate Governance
  run: python packages/.sdd-wizard/SCRIPTS/validate_governance.py

- name: Validate ADRs
  run: python packages/.sdd-wizard/SCRIPTS/validate_adrs.py

- name: Validate Quiz
  run: python packages/.sdd-wizard/SCRIPTS/validate_quiz.py
```

### Local Validation Run

```bash
# Run governance validations locally
python packages/.sdd-wizard/SCRIPTS/validate_governance.py
python packages/.sdd-wizard/SCRIPTS/validate_adrs.py
python packages/.sdd-wizard/SCRIPTS/validate_quiz.py
```

---

**Created**: 2026-04-18
**Maintenance**: Update as new validation tools are added
