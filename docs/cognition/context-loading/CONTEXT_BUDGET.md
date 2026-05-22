# Context Management: Token Budgeting

**Purpose:** Ensure the agent has enough "mental space" (context window) for reasoning by strictly limiting the amount of documentation and code loaded at once.

---

## ⚖️ The 30/70 Rule

For any given task, the context window should ideally be distributed as follows:

| Component | Target % | Purpose |
|---|---|---|
| **System Instructions** | 5% | Core behavior and safety rules |
| **Context (Docs/Spec)** | 25% | The "What" and "Why" (from PATH routing) |
| **Execution Area (Code)** | 40% | The "Where" (affected files and local neighbors) |
| **Reasoning Space** | 30% | Empty space for the model to think and solve |

> ⚠️ **Danger Zone:** If Docs + Code > 70%, the model's reasoning ability degrades exponentially ("Lost in the Middle").

---

## 📉 Compression Techniques

When approaching the budget limit:

### 1. Functional Skeletonizing
Instead of loading full files, load only signatures:
```python
# ❌ Full file (300 lines)
# ✅ Skeleton (15 lines)
class Processor:
    def process(data: dict) -> Result: ...
    def validate(id: str) -> bool: ...
```

### 2. Semantic Pruning
Only load the specific Markdown sections relevant to the task, not the whole file. Use `#` anchors.

### 3. Layer Masking
If working in the `Service` layer, load `Repository` interfaces but NOT `Repository` implementations.

---

## 🚨 Budget Breach Protocol

If the required context for a task exceeds 70% of the window:

1. **De-scale the Task**: Break the task into smaller sub-tasks (Switch to PATH D or sub-tasks of C).
2. **Aggressive Skeletonizing**: Convert all "neighbor" files to signatures only.
3. **Context Flushing**: Drop all research notes and previous trial-and-error logs before the final implementation attempt.

---

## 📏 Benchmark
- **PATH A/B**: Total context should be < 10k tokens.
- **PATH C**: Total context should be < 50k tokens.
- If context > 100k tokens, the agent is likely suffering from **Cognitive Overload**.

---

## References
- Anti-pattern: [`COGNITIVE_OVERLOAD.md`](../anti-patterns/COGNITIVE_OVERLOAD.md)
- Routing: [`path-routing.md`](./path-routing.md)
