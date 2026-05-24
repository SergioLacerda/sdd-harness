#!/usr/bin/env sh
# SDD CLI installer — requires uv (https://docs.astral.sh/uv)
set -eu

REPO="https://github.com/SergioLacerda/sdd-harness"
CLI_SUBDIR="packages/interfaces/sdd_cli"

echo "→ Checking for uv..."
if ! command -v uv > /dev/null 2>&1; then
    echo "ERROR: uv not found."
    echo "Install it first: https://docs.astral.sh/uv"
    exit 1
fi
echo "  uv $(uv --version) found."

echo "→ Installing SDD CLI from source..."
uv tool install "git+${REPO}#subdirectory=${CLI_SUBDIR}" --force

echo "→ Verifying installation..."
sdd --version

echo ""
echo "✓ SDD CLI installed. Run: sdd wizard"
