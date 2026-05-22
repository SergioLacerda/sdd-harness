#!/usr/bin/env python
"""
SDD v3.0 Compiler - Entry Point & Orchestrator

Main entry point for the SDD v3.0 compilation pipeline. This is the "seed"
of the compiler that orchestrates the complete workflow:
  1. Read SOURCE (core/*.spec/*.dsl)
  2. Validate syntax
  3. Compile to MessagePack binary (.bin)
  4. Deploy to runtime/
  5. Generate metadata.json with audit trail

Usage:
  From repository root:
    python compiler/compiler.py     ← MAIN ENTRY POINT
    python -m compiler

  from sdd_compiler/:
    python -m src
    python compiler.py

  As library:
    from sdd_compiler.src.integrate import SDDIntegrator
    integrator = SDDIntegrator()
    integrator.run()
"""

import importlib.util
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Load integrate module from src/ to avoid naming conflicts
    src_dir = Path(__file__).parent / "src"
    integrate_path = src_dir / "integrate.py"

    # Use importlib to load the module by name
    spec = importlib.util.spec_from_file_location("integrate", integrate_path)
    if spec is None or spec.loader is None:
        logger.error("Failed to load module spec from %s", integrate_path)
        sys.exit(1)
    integrate_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(integrate_module)

    # Run from repository root
    repo_root = Path(__file__).parent.parent
    integrator = integrate_module.SDDIntegrator(repo_root)
    success = integrator.run()
    sys.exit(0 if success else 1)
