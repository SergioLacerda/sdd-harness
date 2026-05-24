# 📋 ADDING_NEW_PROJECT — Scaling Guide

**For:** Team leads adding a new project to the SPEC framework
**Time:** 30-45 minutes per new project
**Complexity:** Medium (config creation + validation)
**Prerequisites:** AGENT_HARNESS completion + understand SPECIALIZATIONS pattern

---

## 🎯 Quick Navigation

| Step | Task | Time | Status |
|------|------|------|--------|
| **1** | Create project folder structure | 5 min | Create `/EXECUTION/spec/custom/PROJECT_NAME/` |
| **2** | Write SPECIALIZATIONS_CONFIG.md | 10 min | Define project parameters |
| **3** | Run generate-specializations.py | 5 min | Auto-generate specializations |
| **4** | Validate output files | 5 min | Review generated constitution + ia-rules |
| **5** | Create project threads | 5 min | Create thread tracking files |
| **6** | Add to CI/CD | 5 min | Update spec-enforcement.yml |
| **7** | Team kickoff | 5 min | Communicate structure to team |

**Total:** 40 minutes (if no complications)

---

## 📁 Step 1: Create Project Folder Structure (5 min)

```bash
# Create main project directory
mkdir -p docs/ia/custom/PROJECT_NAME

# Create subdirectories
mkdir -p docs/ia/custom/PROJECT_NAME/development/threads
mkdir -p docs/ia/custom/PROJECT_NAME/reality/current-system-state
mkdir -p docs/ia/custom/PROJECT_NAME/reality/limitations
mkdir -p docs/ia/custom/PROJECT_NAME/archive

# Verify structure
tree docs/ia/custom/PROJECT_NAME/
# Output should be:
# docs/ia/custom/PROJECT_NAME/
# ├── development/
# │   └── threads/
# ├── reality/
# │   ├── current-system-state/
# │   └── limitations/
# └── archive/
```

**What each folder is for:**

- `development/threads/` → Team coordination files (who's working on what)
- `reality/current-system-state/` → System contracts, services, known issues
- `reality/limitations/` → Known bugs, constraints, tech debt
- `archive/` → Read-only historical records (ADRs, decisions)

---

## 📝 Step 2: Write SPECIALIZATIONS_CONFIG.md (10 min)

**Create:** `docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS_CONFIG.md`

**Content template:**

```markdown
# SPECIALIZATIONS CONFIG — PROJECT_NAME

**Project:** PROJECT_NAME
**Language:** python (or your language)
**Status:** In Development

---

## Project Parameters

```
PROJECT_NAME=my-project
LANGUAGE=python
ASYNC_FRAMEWORK=fastapi
MAX_CONCURRENT_ENTITIES=100
PRIMARY_DOMAIN_OBJECTS=entity1,entity2,entity3
TEAM_SIZE=3
MATURITY_LEVEL=alpha
```

---

## Domain Specialization

**Project purpose:** One paragraph describing what this project does
**Key entities:** List 3-5 primary domain entities
**Scale:** Expected concurrent users/entities
**Performance targets:** Response time SLOs, throughput

**Example:**

```markdown
**Purpose:** Campaign orchestration and management system

**Key entities:**
- Campaign (orchestration root)
- Encounter (encounter management)
- NPC (character/actor management)
- QuestChain (narrative thread)

**Scale:** 200 concurrent active campaigns

**Performance:**
- Campaign updates: < 200ms
- Encounter changes: < 100ms
- NPC interactions: < 150ms
```

---

## Architecture Notes

Document how this project differs from other projects:

```markdown
**Unlike [PROJECT_NAME]:**
- Focus: Campaign orchestration (vs narrative generation)
- Scale: 200 concurrent (vs 50 in rpg-narrative)
- Architecture: Event-driven (vs request-response)
- Data model: Campaign-centric (vs Narrative-centric)
```

---

**Generated:** 2026-04-19
**Status:** Configuration template
```

**Key fields to define:**

| Field | Example | Why |
|-------|---------|-----|
| `PROJECT_NAME` | `[PROJECT_NAME]` | Identifier for generate-specializations |
| `LANGUAGE` | `python` | For language-specific templates |
| `ASYNC_FRAMEWORK` | `fastapi` | For async patterns |
| `MAX_CONCURRENT_ENTITIES` | `200` | For scaling constraints |
| `PRIMARY_DOMAIN_OBJECTS` | `campaigns,npcs,quests` | For layer mapping |
| `TEAM_SIZE` | `3` | For communication strategy |
| `MATURITY_LEVEL` | `alpha` | For feature gate expectations |

---

## 🎯 Step 3: Run generate-specializations.py (5 min)

**Command:**
```bash
python docs/ia/SCRIPTS/generate-specializations.py --project PROJECT_NAME
```

**Expected output:**
```
✅ Generated: docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS/constitution-PROJECT_NAME-specific.md
✅ Generated: docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS/ia-rules-PROJECT_NAME-specific.md
✅ SPECIALIZATIONS generated for PROJECT_NAME
📝 Files created in: docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS/
```

**What this creates:**

1. **constitution-PROJECT_NAME-specific.md**
   - Project-specific constraints (concurrency, entities, scale)
   - Principle specializations for your domain
   - Architecture mapping

2. **ia-rules-PROJECT_NAME-specific.md**
   - Project-specific enforcement rules
   - Thread isolation strategy
   - Integration constraints

**Troubleshooting:**

| Error | Cause | Fix |
|-------|-------|-----|
| `Config not found at docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS_CONFIG.md` | Missing config file | Create SPECIALIZATIONS_CONFIG.md (Step 2) |
| `Invalid status 'X'. Must be: ['Complete', 'WIP', 'Deprecated']` | Config file has bad Status | Fix Status field in SPECIALIZATIONS_CONFIG.md |
| `Missing required config fields: [...]` | Missing key parameters | Add all required fields to config |

---

## ✅ Step 4: Validate Output Files (5 min)

**Check the generated specializations:**

```bash
# View constitution
cat docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS/constitution-PROJECT_NAME-specific.md

# View ia-rules
cat docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS/ia-rules-PROJECT_NAME-specific.md

# Verify line counts (should be ~250+ lines for constitution, ~50+ for ia-rules)
wc -l docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS/*.md
```

**Validation checklist:**

- [ ] Constitution includes project name in header
- [ ] Max concurrent entities mentioned in constraints
- [ ] ia-rules adapted to your scale (not generic)
- [ ] Primary domain objects mapped to layers
- [ ] No syntax errors (valid markdown)
- [ ] Links are correct format `[text](path.md)` (not backticks)

**If generation failed:**

```bash
# Re-run with --force flag
python docs/ia/SCRIPTS/generate-specializations.py --project PROJECT_NAME --force

# Test idempotency (should be identical output)
python docs/ia/SCRIPTS/generate-specializations.py --project PROJECT_NAME --force
```

---

## 🧵 Step 5: Create Project Threads (5 min)

**Create:** `docs/ia/custom/PROJECT_NAME/development/execution-state/_current.md`

**Content:**

```markdown
# Execution State — PROJECT_NAME

**Project:** PROJECT_NAME
**Last Updated:** 2026-04-19
**Team Size:** N developers
**Status:** Initial setup

---

## 🎯 Current Threads

| Thread | Owner | Status | Focus | Priority |
|--------|-------|--------|-------|----------|
| Thread A | [Name] | Not started | Core domain implementation | 🔴 Critical |
| Thread B | [Name] | Not started | Infrastructure setup | 🟠 High |
| (Add more threads as needed) | | | | |

---

## 🚧 Active Blockers

None yet (initial setup phase)

---

## 📋 Checkpoint Protocol

All threads must update this file after each feature:
- What was implemented
- Key decisions made
- Risks discovered
- Next priority

---

**Template for checkpoints:**

```
[2026-04-20 @ developer-name]
**TASK:** Implement campaign domain entity

**DECISIONS:**
- Used immutable dataclass (vs Pydantic model)
- Campaign state machine: Draft → Active → Archived

**QUESTIONS OPEN:**
- Concurrent session handling (needs TBD)

**RISKS:**
- State transitions need validation rules

**STATUS:** Complete, ready for review
```
```

**Create thread tracking files:**

```bash
# Create empty thread files (or update as team members start)
mkdir -p docs/ia/custom/PROJECT_NAME/development/threads

# Create README for threads
cat > docs/ia/custom/PROJECT_NAME/development/threads/README.md << 'EOF'
# Project Threads

Each developer/team works on isolated threads (no cross-thread modifications).

**Thread template:**
- File: THREAD_A.md, THREAD_B.md, etc.
- Owner: [Team member name]
- Focus: What this thread is implementing
- Rules: No modifications outside this thread without approval

See execution-state/_current.md for thread status and blockers.
EOF
```

---

## 🔧 Step 6: Add to CI/CD (5 min)

**Update:** `.github/workflows/spec-enforcement.yml`

**Add your project to the generate-specializations validation job:**

```yaml
- name: Test specializations generation
  run: |
    echo "Testing Project 1: [PROJECT_NAME]"
    python docs/ia/SCRIPTS/generate-specializations.py --project [PROJECT_NAME] --force

    echo "Testing Project 2: [PROJECT_NAME]"
    python docs/ia/SCRIPTS/generate-specializations.py --project [PROJECT_NAME] --force

    echo "Testing Project 3: PROJECT_NAME"  # ← ADD THIS
    python docs/ia/SCRIPTS/generate-specializations.py --project PROJECT_NAME --force

    echo "✅ All projects generated successfully"
```

**Result:** CI/CD now validates your project's specializations on every push.

---

## 📢 Step 7: Team Kickoff (5 min)

**Tell your team:**

```markdown
## PROJECT_NAME Now Lives in SPEC Framework

✅ **Project structure created**
- Location: docs/ia/custom/PROJECT_NAME/
- Specializations: Auto-generated from SPECIALIZATIONS_CONFIG.md
- Threads: See docs/ia/custom/PROJECT_NAME/development/execution-state/_current.md

✅ **Entry point for all team members**
Read: docs/ia/guides/onboarding/AGENT_HARNESS.md

✅ **Your project specializations**
- Constitution: docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS/constitution-*.md
- Rules: docs/ia/custom/PROJECT_NAME/SPECIALIZATIONS/ia-rules-*.md

✅ **Thread assignments**
- Thread A (Core domain): [Owner]
- Thread B (Infrastructure): [Owner]
- See execution-state/_current.md for details

🎯 **Next steps:**
1. Each thread owner reads AGENT_HARNESS (30 min)
2. Review your thread's specializations (15 min)
3. Start coding!

❓ **Questions?**
- Governance: See CANONICAL/rules/ia-rules.md
- Architecture: See SPECIALIZATIONS/constitution-*.md
- Blocked? Add to execution-state/_current.md "Active Blockers"
```

---

## 🔄 Scaling Pattern Validation

**Before adding project 5+, verify:**

✅ Projects 2-3 work successfully (test coverage)
✅ Scaling to different domains works (rpg-narrative + [PROJECT_NAME] demonstrate this)
✅ CANONICAL/constitution.md satisfies all projects
✅ Thread isolation prevents team conflicts
✅ CI/CD validates all projects on every commit

**If any of these fail:**
- Document issue in docs/ia/custom/PROJECT_NAME/reality/limitations/known_issues.md
- Escalate to architecture team
- Consider CANONICAL changes if >3 projects have same issue

---

## 🚨 Common Mistakes

❌ **Mistake 1:** Not defining domain clearly in SPECIALIZATIONS_CONFIG.md
- Result: generate-specializations fails or generates wrong constraints
- Fix: Be explicit about what project does + key entities

❌ **Mistake 2:** Forgetting to update CI/CD
- Result: Project specializations not validated on commits
- Fix: Add to generate-specializations job in spec-enforcement.yml

❌ **Mistake 3:** Not creating thread tracking
- Result: Team doesn't know who's working on what
- Fix: Create execution-state/_current.md with thread assignments

❌ **Mistake 4:** Modifying CANONICAL directly for project-specific needs
- Result: Changes affect all projects (breaks isolation)
- Fix: Use SPECIALIZATIONS instead; CANONICAL stays generic

---

## 📊 Checklist for Successful Project Addition

Before marking "complete":

- [ ] Folder structure created (development/, reality/, archive/)
- [ ] SPECIALIZATIONS_CONFIG.md written with all required fields
- [ ] generate-specializations.py ran successfully
- [ ] Generated files reviewed (constitution + ia-rules valid)
- [ ] Execution state file created with thread assignments
- [ ] CI/CD updated to test new project
- [ ] Team notified of project structure
- [ ] AGENT_HARNESS read by all team members
- [ ] First thread has started work

---

## 🔗 Related Docs

- `SPECIALIZATIONS_CONFIG.md` template (created in the target project root)
- [governance_fetcher.py](../../../../packages/interfaces/sdd_wizard/src/sdd_wizard/orchestration/governance_fetcher.py)
- [AGENT_HARNESS.md](../onboarding/AGENT_HARNESS.md)
- [architecture.md](../../canonical/specifications/architecture.md)

---

**Last Updated:** 2026-04-19
**Status:** Complete (v1.0)
**Tested With:** [PROJECT_NAME] (2 projects, 4x entity scale increase)
