# 🧠 Decision Model — Task Classification & Progressive Task Decomposition (PTD)

## 🎯 Purpose

Classify tasks before execution and aggressively enforce **Progressive Task Decomposition** to prevent cognitive overload ("Lost in the Middle") and token budget breaches.

---

## 🔀 Classification & Budgets

- **Bug** → PATH A (~17K tokens)
- **Simple feature** → PATH B (~21K tokens)
- **Complex** → PATH C (~35K tokens) — *Requires Decomposition*
- **Parallel** → PATH D (~15K tokens/thread)

---

## 🔒 Progressive Task Decomposition (PTD) Rules

The SDD framework mandates that no agent should execute complex reasoning loops spanning massive context.

1. **Mandatory Decomposition:** Any task classified as **PATH C (Complex)** MUST NOT be executed in a single session. The agent MUST decompose it into a tree of **PATH A**, **PATH B**, or **PATH D** sessions.
2. **Retroactive Decomposition:** If a **PATH B** task expands in scope during execution (e.g., unexpected architectural dependencies), the agent MUST halt, reclassify as **PATH C**, and recursively decompose the remainder of the work.
3. **Decomposition Depth:** The maximum allowed tree depth (`decomposition_level`) is **3**. If level 3 is reached and the task is still too broad, escalate to a human checkpoint.
4. **Session Hierarchy:** Decomposed tasks must share the parent's `work_item_id` and explicitly declare their `parent_session_id` to ensure telemetry can aggregate costs effectively.

---

## 🚨 Execution Block

Agent **MUST** classify the task and formulate a PTD tree (if PATH C) **BEFORE** loading significant context.
