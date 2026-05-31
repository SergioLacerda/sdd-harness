#!/usr/bin/env sh
# SDD CLI installer — requires uv (https://docs.astral.sh/uv)
set -eu

REPO="https://github.com/SergioLacerda/sdd-harness"
CLI_SUBDIR="packages/interfaces/sdd_cli"
TOOL_SPEC="git+${REPO}#subdirectory=${CLI_SUBDIR}"

CHECK_ONLY=0
if [ "${1:-}" = "--check" ]; then
    CHECK_ONLY=1
fi

fail() {
    echo "ERROR: $1" >&2
    exit 1
}

note() {
    echo "→ $1"
}

ok() {
    echo "  ✓ $1"
}

note "Running installer preflight..."

if ! command -v uv >/dev/null 2>&1; then
    fail "uv not found. Install it first: https://docs.astral.sh/uv"
fi
ok "$(uv --version)"

if ! command -v git >/dev/null 2>&1; then
    fail "git not found. Install git and retry."
fi
ok "git $(git --version | sed 's/^git version //') found."

if ! command -v curl >/dev/null 2>&1; then
    fail "curl not found. Install curl and retry."
fi
ok "curl found."

if command -v python3 >/dev/null 2>&1; then
    PY_OK="$(python3 -c 'import sys; print(int(sys.version_info >= (3,10)))')" || fail "unable to evaluate python3 version."
    if [ "$PY_OK" != "1" ]; then
        fail "python3 >= 3.10 is required."
    fi
    PY_VER="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')" || fail "unable to read python3 version string."
    ok "python $PY_VER found."
else
    note "python3 not found in PATH. uv may still provide managed Python."
fi

note "Checking repository reachability..."
if ! curl -fsSLI "$REPO" >/dev/null 2>&1; then
    fail "cannot reach $REPO. Check internet/proxy and retry."
fi
ok "Repository reachable."

if [ "$CHECK_ONLY" -eq 1 ]; then
    echo ""
    echo "✓ Preflight checks passed."
    exit 0
fi

note "Installing SDD CLI from source..."
uv tool install "$TOOL_SPEC" --force

# Common location for uv tool binaries in user installs.
if [ -d "$HOME/.local/bin" ]; then
    case ":$PATH:" in
        *":$HOME/.local/bin:"*) ;;
        *) export PATH="$HOME/.local/bin:$PATH" ;;
    esac
fi

note "Verifying installation..."
if ! command -v sdd >/dev/null 2>&1; then
    fail "sdd executable not found in PATH after install. Add ~/.local/bin to PATH and retry."
fi

sdd version

echo ""
echo "✓ SDD CLI installed. Next: cd <your-project> && sdd wizard run"
