#!/usr/bin/env python3
"""Print the installed typer version.

Invoked as a subprocess (script path, not `-c`) by make_tasks.py's venv guard,
since SafeProcessRunner blocks inline `python -c` execution by policy.
"""

import typer

print(typer.__version__)
