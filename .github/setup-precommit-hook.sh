#!/usr/bin/env bash
# SDD Hook Setup
# Installs SDD shell hooks and pre-commit framework hooks for this repository.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_SRC="${REPO_ROOT}/tools/scripts/git-hooks"
HOOKS_DEST="${REPO_ROOT}/.git/hooks"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"

if [ ! -d "${REPO_ROOT}/.git" ]; then
    echo "ERROR: .git directory not found. Run this script from inside a git clone."
    exit 1
fi

if [ ! -d "${HOOKS_SRC}" ]; then
    echo "ERROR: Hook source directory not found: ${HOOKS_SRC}"
    exit 1
fi

PRE_COMMIT_BIN=""
PRE_COMMIT_USE_UV_RUN="0"
PRE_COMMIT_USE_UVX="0"
if command -v pre-commit >/dev/null 2>&1; then
    PRE_COMMIT_BIN="$(command -v pre-commit)"
elif [ -x "${REPO_ROOT}/.venv/bin/pre-commit" ]; then
    PRE_COMMIT_BIN="${REPO_ROOT}/.venv/bin/pre-commit"
elif command -v uv >/dev/null 2>&1; then
    if uv run pre-commit --version >/dev/null 2>&1; then
        PRE_COMMIT_BIN="uv"
        PRE_COMMIT_USE_UV_RUN="1"
    else
        PRE_COMMIT_BIN="uvx"
        PRE_COMMIT_USE_UVX="1"
    fi
else
    echo "ERROR: 'pre-commit' not found in PATH, .venv/bin/pre-commit, or via uv."
    echo "Install hint: uv tool install pre-commit  (or: pip install pre-commit)"
    exit 1
fi

echo "Installing SDD shell hooks from ${HOOKS_SRC}"
for hook_name in pre-commit pre-push commit-msg post-merge; do
    src="${HOOKS_SRC}/${hook_name}"
    dest="${HOOKS_DEST}/${hook_name}"

    if [ ! -f "${src}" ]; then
        echo "ERROR: Missing hook file: ${src}"
        exit 1
    fi

    if [ -e "${dest}" ] || [ -L "${dest}" ]; then
        backup="${dest}.backup-sdd-${TIMESTAMP}"
        mv "${dest}" "${backup}"
        echo "WARN: Backed up existing hook ${dest} -> ${backup}"
    fi

    ln -s "${src}" "${dest}"
    chmod +x "${src}" "${dest}"
    echo "OK: Installed ${hook_name}"
done

echo "Installing pre-commit framework hook"
if [ "${PRE_COMMIT_USE_UV_RUN}" = "1" ]; then
    "${PRE_COMMIT_BIN}" run pre-commit install --install-hooks
elif [ "${PRE_COMMIT_USE_UVX}" = "1" ]; then
    "${PRE_COMMIT_BIN}" pre-commit install --install-hooks
else
    "${PRE_COMMIT_BIN}" install --install-hooks
fi

echo ""
echo "SDD hooks installed successfully."
echo "Verification:"
echo "  ls -la .git/hooks/pre-commit .git/hooks/pre-push .git/hooks/commit-msg .git/hooks/post-merge"
echo "  pre-commit run --all-files"
