# Decision Model: Knowledge Gap Quiz

**Purpose:** Prevent "Hallucination" or "Guessing" by forcing the agent to verify its information state before implementation.

---

## ❓ The Knowledge Quiz

Before starting any implementation, the agent must answer these 3 questions:

### 1. The Source Test
>
> **"Do I know the exact canonical rule for this component, or am I assuming a default?"**

- [ ] I have read the specific file in `spec/canonical/`.
- [ ] I am assuming based on general knowledge. (**STOP: Read the spec.**)

### 2. The Dependency Test
>
> **"Do I have the interface/contract of all functions I am about to call?"**

- [ ] I have the code for all direct dependencies.
- [ ] I only have the names, not the signatures. (**STOP: Load signatures.**)

### 3. The Side-Effect Test
>
> **"Do I know the top 3 modules that will be affected by this change?"**

- [ ] I can name them and I have checked their `reality/` status.
- [ ] I am unsure if this touches other modules. (**STOP: Run impact analysis.**)

---

## 🚦 Score & Action

- **3/3 Passed**: Proceed to Implementation.
- **2/3 Passed**: Warning. Spend 1 iteration filling the gap before coding.
- **<2 Passed**: **CRITICAL ERROR.** Pause execution and perform deeper context loading.

---

## ⚖️ Rationale

Agents often rush into coding to "solve" the problem quickly. This quiz forces a pause, ensuring that the **Quality of Information** is high enough to produce **World-Class Code**.
