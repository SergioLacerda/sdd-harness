# 🔄 SPEC Reusability Guide

How to use the SPEC framework (System of Principles and Specifications) across multiple projects while maintaining "world-class" quality.

## 🎯 Principles

1. **CANONICAL/ = Immutable** — All shared rules, architecture, and decisions
2. **custom/ = Specialization** — Each project specializes its own state and execution
3. **DRY = True** — ~30% duplication (acceptable) vs. 100% with the alternatives
4. **Zero Quality Degradation** — All projects = same quality

## 📋 Layers and Reusability

### CANONICAL/ ✅ Reuse: 100%

**All projects use it EXACTLY THE SAME**

```
/EXECUTION/spec/CANONICAL/
├── rules/                 # Applies to ALL projects
├── specifications/        # Applies to ALL projects
└── decisions/            # History shared by ALL projects
```

**What you CAN do:**

- ✅ Add new rules/specs to CANONICAL/ (everyone inherits them)
- ✅ Create a new ADR in CANONICAL/ (applies globally)
- ✅ Expand sections (e.g., observability.md to cover more projects)

**What you CANNOT do:**

- ❌ Modify CANONICAL/ for a specific project
- ❌ Have "exceptions" in one project
- ❌ Create different versions of the same file

### custom/ 🎨 Reuse: ~70%

**Each project specializes as needed**

```
/EXECUTION/spec/custom/
├── _TEMPLATE/           # Template for new projects (100% reusable)
└── [PROJECT_NAME]/      # Project-specific implementation
    ├── development/     # Active execution state (changes frequently)
    └── reality/         # Observed state of the project
```

**What you CAN do:**

- ✅ Create a new project by copying `_TEMPLATE/`
- ✅ Specialize `reality/` according to the project's state
- ✅ Specialize `development/` according to active work

**What you CANNOT do:**

- ❌ Contradict CANONICAL/
- ❌ Copy files instead of reusing the template
- ❌ Create dependencies between projects

### ARCHIVE/ 📚 Reuse: 0% (read-only)

**History. Consult, do not modify.**

```
docs/spec/ARCHIVE/
├── working-sessions/     # Completed analyses
├── deprecated-decisions/ # Old ADRs
└── project-migrations/   # Integration history
```

## 🚀 How to Start a New Project

### Step 1: Create the structure (2 min)

```bash
cp -r docs/ia/custom/_TEMPLATE docs/ia/custom/my-new-project
```

### Step 2: Fill in metadata (5 min)

```bash
# Edit:
# - docs/ia/custom/my-new-project/README.md (name, description)
# - docs/ia/custom/my-new-project/INTEGRATION_RESULTS.md
```

### Step 3: Document the current state (2-4 hours)

```bash
# Document:
# - reality/current-system-state/ (how it is today)
# - reality/limitations/ (what doesn't work)
# - development/execution-state/_current.md (active work)
```

### Step 4: Validate inheritance (30 min)

```bash
# Check:
# - All CANONICAL/ files are present and identical
# - Paths in ia-rules.md point to the correct project
# - _INDEX.md lists the new project
```

**Total time:** ~4 hours (documentation is the bulk of it)

## 📊 Reuse Matrix

| Component | Reuse | Level | Project A | Project B | Project C |
|-----------|-------|-------|----------|----------|----------|
| ADRs | 100% | CANONICAL | ✅ Same | ✅ Same | ✅ Same |
| Architecture | 100% | CANONICAL | ✅ Same | ✅ Same | ✅ Same |
| Definition of Done | 100% | CANONICAL | ✅ Same | ✅ Same | ✅ Same |
| Testing patterns | 100% | CANONICAL | ✅ Same | ✅ Same | ✅ Same |
| Services description | ~30% | custom/ | ⚠️ Similar | ⚠️ Similar | ⚠️ Similar |
| Limitations | ~20% | custom/ | ❌ Different | ❌ Different | ❌ Different |
| Current work | 0% | custom/ | 🔄 Active | ⚠️ Paused | ❌ Stopped |

## 🔐 Enforcement Rules

### Rule 1: CANONICAL is immutable

```
❌ DON'T: git rm CANONICAL/rules/constitution.md
✅ DO: Extend constitution.md with new sections
```

### Rule 2: Each project has its own custom/

```
❌ DON'T: custom/[PROJECT_NAME]/reality/another-project-notes.md
✅ DO: custom/[PROJECT_NAME]/reality/ ONLY for [PROJECT_NAME]
```

### Rule 3: The template is sacred

```
❌ DON'T: Modify custom/_TEMPLATE/ for testing
✅ DO: Use custom/_TEMPLATE/ as a model (cp -r)
```

### Rule 4: ARCHIVE never receives a mutation push

```
❌ DON'T: git push with changes under ARCHIVE/
✅ DO: Move files from DEVELOPMENT/ → ARCHIVE/ (only completed work)
```

### Rule 5: Improvements go to CANONICAL first

```
❌ DON'T: Add observability.md under custom/[PROJECT_NAME]/
✅ DO: Add CANONICAL/specifications/observability.md (everyone inherits it)
```

## 🎓 Example: Step-by-Step Integration

### New project: "[PROJECT_NAME]"

#### 1. Setup

```bash
cd /home/my-projects/[PROJECT_NAME]

# Copy SPEC
cp -r /home/[PROJECT_NAME]/docs/ia /docs/ia

# Structure for reuse
mkdir -p /EXECUTION/spec/custom/_TEMPLATE/{development,reality}
```

#### 2. Inherit CANONICAL

```bash
# CANONICAL is 100% shared (do not change it!)
ls /EXECUTION/spec/CANONICAL/
# rules/ specifications/ decisions/
```

#### 3. Specialize custom/

```bash
# Document project-specific state
echo "Game Master API - Services..." > /EXECUTION/spec/custom/_TEMPLATE/reality/current-system-state/services.md

# Document active work
echo "Thread 1: Implement..." > /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/_current.md
```

#### 4. Validate

```bash
# Check that CANONICAL is identical
diff /EXECUTION/spec/CANONICAL/ /path/to/[PROJECT_NAME]/EXECUTION/spec/CANONICAL/
# Result: should be identical!
```

## ⚡ World-Class Improvements (Roadmap)

When improvements are implemented in CANONICAL/, all projects inherit them automatically:

- 🔄 Observability: `CANONICAL/specifications/observability.md` (new)
- 🔒 Security: `CANONICAL/rules/security-model.md` (new)
- ⚡ Performance: `CANONICAL/specifications/performance.md` (new)
- ✅ Compliance: `CANONICAL/specifications/compliance.md` (new)

**All projects get this for free!**

## 📞 Support

### "I have a question about an ADR"

→ See `CANONICAL/decisions/ADR-*.md`

### "I need to extend the architecture"

→ Read `CANONICAL/specifications/architecture.md` first

### "I found a bug/limitation"

→ Document it under `custom/[PROJECT_NAME]/reality/limitations/`

### "I have a global improvement"

→ Propose an ADR under `CANONICAL/decisions/` (applies to everyone)

---

**Framework:** SPEC v1.0
**Authority:** ADR + CANONICAL
**Last review:** 2026-04-19
