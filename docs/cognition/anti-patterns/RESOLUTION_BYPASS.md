# Anti-Pattern: Resolution Bypass

**Also known as:** Dependency Hacking, Import Patching, Path Manipulation

---

## ❌ The Problem

Manipulating the language runtime's module/dependency resolution mechanism at execution time — instead of declaring dependencies correctly through the language's package management system.

This is a "make it work" trick that creates invisible, fragile coupling between runtime behavior and the physical file system layout.

---

## 🔍 Universal Symptoms

- Import/require paths that contain `..` more than once
- Code that modifies the runtime's module search path (any form of `PATH=`, `*_PATH=`, etc.)
- Dependencies that only work when the process is started from a specific directory
- "It works on my machine" issues related to imports
- Environment variables being set inside source code to influence resolution

---

## 💣 Why It's Dangerous

| Risk | Consequence |
|---|---|
| **File system coupling** | Code breaks when directory structure changes |
| **Environment sensitivity** | Works locally, fails in CI/CD or Docker |
| **Hidden dependencies** | Static analysis tools can't see what you're really importing |
| **Deployment fragility** | Requires specific working directory or env setup |
| **Transitive failures** | Downstream consumers inherit the broken resolution |

---

## ✅ The Universal Cure

> **Declare dependencies explicitly through the language's package system. Never manipulate resolution at runtime.**

1. **If you need to import something** → it must be a declared dependency in your package manifest
2. **If it's shared code** → extract it into a proper package/module
3. **If it's internal** → restructure so the import path is natural, not hacked

---

## 🌐 Language-Specific Guides

| Language | Specific Patterns & Cures |
|---|---|
| Python | [`lang/PYTHON_RESOLUTION_BYPASS.md`](lang/PYTHON_RESOLUTION_BYPASS.md) |
| Go | [`lang/GO_RESOLUTION_BYPASS.md`](lang/GO_RESOLUTION_BYPASS.md) |
| Node / TypeScript | [`lang/NODE_RESOLUTION_BYPASS.md`](lang/NODE_RESOLUTION_BYPASS.md) |
| Java | [`lang/JAVA_RESOLUTION_BYPASS.md`](lang/JAVA_RESOLUTION_BYPASS.md) |

---

## 📏 Benchmark

Run a static analysis tool on your codebase. If it can't resolve all imports without running the program first → you have a resolution bypass somewhere.

---

## References
- Anti-pattern (root cause): [`SYMPTOM_FIXING.md`](./SYMPTOM_FIXING.md)
- Impact assessment: [`cognition/decision-models/IMPACT_ASSESSMENT.md`](../decision-models/IMPACT_ASSESSMENT.md)
