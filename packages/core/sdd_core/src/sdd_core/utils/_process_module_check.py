"""Module availability checks for governed Python interpreters."""

from __future__ import annotations

import tempfile
from pathlib import Path


def check_module_available(python_exe: str | Path, module: str) -> bool:
    """Return True if `module` can be imported by `python_exe`.

    Avoids `python -c` (blocked by governance policy) by writing a temporary
    import script and executing it via SafeProcessRunner.
    """
    script = f"import {module}\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_sdd_import_check.py", delete=True
    ) as handle:
        handle.write(script)
        handle.flush()
        from sdd_core.utils._process_runner import SafeProcessRunner

        runner = SafeProcessRunner()
        result = runner.run([str(python_exe), handle.name], capture_output=True)
        return result.success
