# Resolution Bypass — Python

> Parent: [`RESOLUTION_BYPASS.md`](../RESOLUTION_BYPASS.md)

---

## ❌ Python-Specific Hacks

### 1. `sys.path` Manipulation

```python
# ❌ The most common Python hack
import sys
sys.path.insert(0, '../')
sys.path.append('/absolute/path/to/project')

from my_module import something
```

**Why:** The module wasn't installed as a proper package, so the developer forces Python to look in a different directory.

---

### 2. `PYTHONPATH` Injection in Source Code

```python
# ❌ Setting environment variable inside the code
import os
os.environ['PYTHONPATH'] = '/path/to/my/libs'
```

**Why:** Same root cause — the package isn't declared, so env vars are used as a workaround.

---

### 3. `importlib` Path Patching

```python
# ❌ Dynamically loading modules from arbitrary paths
import importlib.util
spec = importlib.util.spec_from_file_location(
    "my_module", "/some/random/path/my_module.py"
)
```

**Why:** Bypasses the entire package system entirely. The module becomes invisible to static analysis, type checkers, and IDEs.

---

### 4. Relative Import Chains

```python
# ❌ Chains of relative imports going up the tree
from ....utils.helpers import something
```

**Why:** Deep relative imports signal that the package boundary is wrong, not that relative imports are the answer.

---

## ✅ Python Cures

### Cure 1: Editable Install (`pip install -e .`)

For internal packages in a monorepo:

```toml
# pyproject.toml
[project]
name = "my_package"
dependencies = ["other_internal_package"]

# Install once, import anywhere
```

```bash
pip install -e ./packages/my_package
pip install -e ./packages/other_internal_package
# Now: from my_package import something  ✅
```

### Cure 2: Proper Package Structure

```
packages/
└── my_feature/
    ├── pyproject.toml      ← declares the package
    └── src/
        └── my_feature/
            ├── __init__.py
            └── core.py
```

### Cure 3: Workspace Tools (`uv`, `pip-tools`)

```bash
# uv workspaces automatically resolve cross-package imports
uv sync
```

### Cure 4: `__init__.py` Barrel Exports

```python
# packages/my_feature/src/my_feature/__init__.py
from .core import MyClass, my_function  # clean public API
```

---

## 🔍 Detection

```bash
# Find all sys.path manipulations in your codebase
grep -rn "sys\.path" --include="*.py" .

# Find os.environ PYTHONPATH manipulation
grep -rn "PYTHONPATH" --include="*.py" .
```

---

## 📏 Rule
>
> If you find yourself writing `sys.path` anywhere outside of a `conftest.py` or test bootstrap file → stop. Fix the package structure instead.
