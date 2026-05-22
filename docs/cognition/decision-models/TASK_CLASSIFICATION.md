# Decision Model: Task Classification

**Purpose:** Classify any incoming task before loading context or writing code. Wrong classification = wrong PATH = wasted effort.

---

## 🧭 Classification Tree

```
Incoming Task
│
├── Is production broken RIGHT NOW?
│   └── YES → PATH E (Hotfix)
│
├── Does something fail that previously worked?
│   └── YES → PATH A (Bugfix)
│
├── Is the scope bounded to 1-2 files with no API contract change?
│   └── YES → PATH B (Simple)
│
├── Does it touch multiple domain layers OR require an architectural decision?
│   └── YES → PATH C (Complex)
│
├── Are there 2+ independent work streams that don't share state?
│   └── YES → PATH D (Parallel)
│
└── Does the code work but needs cleanup with zero behavior change?
    └── YES → PATH F (Refactor)
```

---

## ⚖️ Classification Rules

### Rule 1: Classify by IMPACT, not by effort
A one-line change that touches a public API = PATH C (not PATH A).

### Rule 2: When in doubt, choose the SAFER path
Unsure between B and C? → Use C. The extra steps protect you.

### Rule 3: PATH E trumps everything
If production is down, no other PATH is relevant.

### Rule 4: Never run PATH F and PATH B simultaneously
Refactoring + new feature = untestable chaos. Separate them.

---

## 🔁 Re-classification Trigger
If during execution you discover the actual scope exceeds your classification:
→ **Stop. Re-classify. Switch PATH.**
Never continue on the wrong PATH once you know it's wrong.
