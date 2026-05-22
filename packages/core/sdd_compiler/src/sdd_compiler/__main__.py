"""
SDD Compiler Main Module - Entry point for: python -m src
"""

import sys

if __name__ == "__main__":
    # Direct import from current package
    from .integrate import SDDIntegrator

    # Run integrator (will auto-detect repo root)
    integrator = SDDIntegrator()
    success = integrator.run()
    sys.exit(0 if success else 1)
