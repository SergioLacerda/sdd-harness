"""Template builders for .sdd/source/README.md and .sdd/runtime/README.md."""

from __future__ import annotations

from ._runtime_readme_template import build_runtime_readme
from ._source_readme_template import build_source_readme

__all__ = ["build_runtime_readme", "build_source_readme"]
