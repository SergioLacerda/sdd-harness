# Cross-platform note: on Windows use Git Bash or WSL to run make targets.
# All shell commands are POSIX-compatible within a bash/sh context.
#
# No implicit suffix rules are used in this Makefile.
MAKEFLAGS += --no-builtin-rules --no-builtin-variables
#
# Use uv run if uv is available; fall back to direct execution (e.g. inside Docker)
VENV_PYTHON := $(firstword $(wildcard .venv/bin/python .venv/Scripts/python.exe))
DOCKER_BUILD_FLAGS ?=
UV := $(shell command -v uv 2>/dev/null)

ifeq ($(strip $(VENV_PYTHON)),)
  ifeq ($(strip $(UV)),)
    PYTHON = $(error no .venv found and uv is not installed. Run `make install` first)
  else
    PYTHON := uv run python
  endif
else
  PYTHON := $(VENV_PYTHON)
endif

.DEFAULT_GOAL := help

# Targets are grouped by affinity into mk/*.mk, included below. Each file
# declares its own .PHONY list and documents its targets with a trailing
# `## description` comment, picked up by `help`'s self-documenting scan.
# See .analysis/refined/20260809-makefile-worldclass-refactor/design.md.
include mk/python.mk
include mk/lint.mk
include mk/docs.mk
include mk/web.mk
include mk/go.mk
include mk/release.mk
include mk/docker.mk
include mk/misc.mk

.PHONY: help
help: ## Show this help
	@echo "SDD Architecture Development"
	@echo "==========================="
	@awk 'BEGIN {FS = ":.*##"} \
	  /^##@/ { printf "\n%s\n", substr($$0, 5) } \
	  /^[a-zA-Z0-9_.-]+:.*##/ { printf "  %-28s %s\n", $$1, $$2 }' \
	  $(MAKEFILE_LIST)
	@echo ""
	@echo "Most targets above also have a namespaced alias in their group,"
	@echo "e.g. 'make test.fast' == 'make test-fast', 'make docker.build' == 'make docker-build'."
