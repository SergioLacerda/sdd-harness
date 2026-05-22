# 📚 Adoption Guides — SDD Implementation Paths

**Quick Navigation for Getting Started with SDD**

---

## 🚀 Choose Your Path

### ⚡ [ULTRA-LITE Adoption](./ULTRA-LITE-ADOPTION.md) — 5 Minutes
**For:** Solo developers, prototypes, MVPs, 2-person teams
**What You Get:**
- 5 core principles
- 3 essential rules
- 5 DoD checkpoints
- Single `.ai-constitution.md` file
- Zero external setup

**Best for:** Solo dev, rapid prototyping, learning core concepts

→ **Ultra-minimal start:** [ULTRA-LITE-ADOPTION.md](./ULTRA-LITE-ADOPTION.md)

---

### 🟢 [LITE Adoption](./LITE-ADOPTION.md) — 15 Minutes
**For:** Experimenting, small teams, learning
**What You Get:**
- 10 core principles
- 5 essential rules
- 10 DoD criteria
- Pre-commit basics
- Easy upgrade to FULL

**Best for:** Learning SDD, side projects, < 5 person teams

→ **Start here if unsure:** [LITE-ADOPTION.md](./LITE-ADOPTION.md)

---

### 🔵 [FULL Adoption](./FULL-ADOPTION.md) — 40 Minutes
**For:** Production teams, regulatory requirements
**What You Get:**
- 15 complete principles
- 16 mandatory rules
- 45 DoD criteria (comprehensive)
- 7-phase workflow
- Full AI agent integration
- Complete auditability

**Best for:** Production systems, large teams, mission-critical

→ **Ready for the real deal:** [FULL-ADOPTION.md](./FULL-ADOPTION.md)

---

### 🔄 [LITE → FULL Migration](./LITE-TO-FULL-MIGRATION.md) — 30 Minutes
**For:** Teams outgrowing LITE
**What It Covers:**
- When to upgrade
- Step-by-step migration
- Configuration changes
- Team communication
- Rollback plan
- Troubleshooting

**Best for:** Scaling from experimentation to production

→ **Ready to upgrade:** [LITE-TO-FULL-MIGRATION.md](./LITE-TO-FULL-MIGRATION.md)

---

### 🌍 [Multi-Language Exploration](./MULTI-LANGUAGE-EXPLORATION.md) — Read
**For:** Planning future multi-language support
**What It Covers:**
- v3.0 Roadmap (Q4 2026)
- Node.js + Go + Rust implementations (planned)
- Language-agnostic principles
- Architecture for each language
- Implementation timeline
- Current Python focus (v2.1)

**Best for:** Understanding long-term vision

→ **Future roadmap:** [MULTI-LANGUAGE-EXPLORATION.md](./MULTI-LANGUAGE-EXPLORATION.md)

---

## 🎯 For Project Integration

**Before you choose adoption, you need to understand your project's intention.**

→ **[INTEGRATION/STEP_6.md](../../INTEGRATION/STEP_6.md)** — Intention Detection Guide
- Answer 5 questions about your project
- Questions reveal whether you need LITE or FULL
- Determines adoption level for your project

**Typical Flow:**
1. Integrate your project (STEP 1-5, same for everyone)
2. Detect your intention (STEP 6, 5 questions)
3. Choose LITE or FULL based on answers
4. Start implementing with your level

---

| Aspect | ULTRA-LITE | LITE | FULL |
|--------|-------------|------|------|
| **Setup Time** | 5 min | 15 min | 40 min |
| **Principles** | 5 | 10 | 15 |
| **Rules** | 3 | 5 | 16 |
| **DoD Criteria** | 5 | 10 | 45 |
| **Phases** | — | 3 | 7 |
| **Best For** | Solo/Prototype | Learning | Production |
| **Upgrade Path** | → LITE | → FULL | — |

---

## 🎯 Decision Tree

```
┌──────────────────────────────────────┐
│ "I want to try SDD"                  │
└───────────────┬──────────────────────┘
                │
        ┌───────┴─────┬──────────┐
        │             │          │
    (ULTRA-LITE) (LITE)      (FULL)
      5 min      15 min      40 min
        │             │          │
     Solo/MVP   Learning    Production
     Prototype  Experiment  Mission-Critical
     2-person   Small team  Regulated
        │             │          │
        └───────┬─────┴──────────┘
                │
          [Start coding]
                │
        ┌───────┴──────┐
        │              │
    (Outgrow)    (Scale)
    LITE→FULL    v3.0+
    Migration  Multi-lang
        │              │
        └───────┬──────┘
                │
        [v3.0+ Future]
```

---

## 📋 Implementation Timeline

### Now (v2.1)
- ✅ LITE Adoption ready (15 min setup)
- ✅ FULL Adoption ready (40 min setup)
- ✅ Migration path documented
- ✅ Python + FastAPI focus

### Soon (v2.2 — Q2 2026)
- ⏳ Real metrics published
- ⏳ Case studies available
- ⏳ Community feedback incorporated
- ⏳ v3.0 planning complete

### Future (v3.0 — Q4 2026)
- ⏳ Node.js support (sdd-nodejs)
- ⏳ Go support (sdd-go)
- ⏳ Rust support (sdd-rust)
- ⏳ Unified multi-language governance

---

## ✅ Your First Steps

1. **Read this page** (5 min)
2. **Choose LITE or FULL** based on your needs
3. **Follow the setup guide** (15-40 min)
4. **Build your first feature** (1-2 hours)
5. **Provide feedback** → shapes the roadmap

---

## 💡 Pro Tips

### For Team Leads
→ Start with **LITE** to validate buy-in
→ Migrate to **FULL** when team is ready
→ Use metrics to prove value to stakeholders

### For Individual Developers
→ **LITE** if learning on your own
→ **FULL** if building production code
→ Ask if unsure → [FAQ](../reference/FAQ.md)

### For AI Agents
→ Both LITE and FULL supported
→ All rules explicit in constitution
→ Autonomous execution possible
→ See [.ai-index.md](../../.ai-index.md)

---

## 🆘 Need Help?

**Can't decide LITE vs FULL?**
→ Start with LITE (easy, reversible)

**Migration questions?**
→ [LITE-TO-FULL-MIGRATION.md](./LITE-TO-FULL-MIGRATION.md)

**General FAQ?**
→ [FAQ](../reference/FAQ.md)

**Emergency?**
→ [Emergency Guide](../emergency/)

**Something broken?**
→ File issue (GitHub) or reach out in discussions

---

## 🗺️ File Organization

```
adoption/
├── INDEX.md (you are here)
├── LITE-ADOPTION.md (15 min setup)
├── FULL-ADOPTION.md (40 min setup)
├── LITE-TO-FULL-MIGRATION.md (upgrade path)
├── MULTI-LANGUAGE-EXPLORATION.md (v3.0 roadmap)
└── [future: language-specific guides]
```

---

## What's Not Here (Yet)

- ❌ Example projects (coming v2.2)
- ❌ Video tutorials (coming v2.2)
- ❌ Language-specific setup (coming v3.0)
- ❌ Real metrics (coming v2.2)

**But:** Documentation is comprehensive. You can start today.

---

## Your Feedback Matters

Framework under active development.
Your experience → shapes v2.2 → shapes v3.0.

Share:
- What works well
- What's confusing
- What you'd change
- Ideas for improvements

**Get involved:** Discussions, issues, PRs welcome.

---

**Ready to get started?** Pick LITE or FULL above. See you on the other side! 🚀

*SDD — Specification-Driven Development with Autonomous Governance*
