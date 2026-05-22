# Cross-platform note: on Windows use Git Bash or WSL to run make targets.
# All shell commands are POSIX-compatible within a bash/sh context.
#
# Use uv run if uv is available; fall back to direct execution (e.g. inside Docker)
VENV_PYTHON := $(wildcard .venv/bin/python)
UV := $(shell command -v uv 2>/dev/null)

ifeq ($(strip $(VENV_PYTHON)),)
  ifeq ($(strip $(UV)),)
    PYTHON := python3
  else
    PYTHON := uv run python
  endif
else
  PYTHON := $(VENV_PYTHON)
endif

.PHONY: check test lint pre-delivery lock clean coverage coverage-strict docs-build docs-serve docker-build release-dry-run install install-docs update-golden-snapshots generate-schemas hooks-install governance-bootstrap help

help:
	@echo "SDD Architecture Development"
	@echo "==========================="
	@echo "install         - Install all workspace dependencies (dev)"
	@echo "install-docs    - Install documentation dependencies (mkdocs)"
	@echo "check           - Run all tests (unit + integration + contract)"
	@echo "test            - Run full multi-layer test pipeline with unified coverage gate"
	@echo "coverage        - Run tests with HTML coverage report"
	@echo "coverage-strict - Per-layer coverage gates (core 90%, features 70%, interfaces 70%)"
	@echo "lint            - Run linters (ruff check + format, mypy, bandit)"
	@echo "lint-fix        - Auto-fix Python linting issues with ruff (local development)"
	@echo "pre-delivery    - [P004] Pre-Delivery Quality Gate: lint + test (run before handoff)"
	@echo "lock            - Regenerate uv.lock"
	@echo "update-golden-snapshots - Update contract test golden files"
	@echo "generate-schemas        - Regenerate JSON Schema files from Pydantic models"
	@echo "hooks-install  - Install local git hooks (SDD shell hooks + pre-commit)"
	@echo "governance-bootstrap - Generate full governance artifacts for local workspace"
	@echo "docs-build      - Build MkDocs site (strict mode)"
	@echo "docs-serve      - Serve MkDocs docs locally"
	@echo "docker-build    - Build Docker image"
	@echo "release-dry-run - Validate version, changelog, and tags before release"
	@echo "clean           - Remove temporary files"

install:
	uv sync --all-groups --all-packages --extra test

install-docs:
	uv sync --group docs

check: golden-status
	$(PYTHON) -m pytest tests packages \
		--cov=packages \
		--cov-report=term-missing:skip-covered

golden-status:
	@echo "🔍 Checking golden file status..."
	@if git status --porcelain tests/contract/fixtures/*.golden.json 2>/dev/null | grep -q .; then \
		echo "⚠️  Golden files have uncommitted changes:"; \
		git status --porcelain tests/contract/fixtures/*.golden.json; \
		echo ""; \
		echo "If intentional, commit them with: git add tests/contract/fixtures/"; \
		echo "If accidental, revert with: git checkout tests/contract/fixtures/"; \
	else \
		echo "✓ Golden files are in sync with git"; \
	fi

test:
	$(PYTHON) tools/maintenance/make_tasks.py test $(ARGS)

test-fast:
	$(PYTHON) -m pytest -x --ff packages/ tests/

coverage:
	$(PYTHON) -m pytest tests packages --cov=packages --cov-report=html --cov-report=term-missing:skip-covered
	@echo "HTML report: build/coverage/html/index.html"

coverage-strict:
	@echo "=== core packages (threshold: 90%) ==="
	$(PYTHON) -m pytest packages/core --cov=packages/core --cov-fail-under=90 -q --tb=short
	@echo "=== feature packages (threshold: 70%) ==="
	$(PYTHON) -m pytest packages/features --cov=packages/features --cov-fail-under=70 -q --tb=short
	@echo "=== interface packages (threshold: 70%) ==="
	$(PYTHON) -m pytest packages/interfaces --cov=packages/interfaces --cov-fail-under=70 -q --tb=short

update-golden-snapshots:
	$(PYTHON) tools/testing/update-golden-snapshots.py

generate-schemas:
	$(PYTHON) tools/testing/generate-schemas.py

hooks-install:
	bash .github/setup-precommit-hook.sh

governance-bootstrap:
	$(PYTHON) -m sdd_cli governance generate --full-bootstrap

lint:
	$(PYTHON) tools/maintenance/make_tasks.py lint

lint-fix:
	$(PYTHON) tools/maintenance/make_tasks.py lint-fix

# P004 Pre-Delivery Quality Gate — run this before every agent handoff
# See: docs/spec/canonical/core/policies/P004_PRE_DELIVERY_QUALITY_GATE.md
pre-delivery: lint test
	@echo "[PDQG] ✅ Pre-Delivery Quality Gate PASSED — ready for human review"

lock:
	uv lock

docs-build:
	$(PYTHON) -m mkdocs build --strict

docs-serve:
	$(PYTHON) -m mkdocs serve

docker-build:
	cp infrastructure/docker/.dockerignore .dockerignore
	docker build -t sdd-harness -f infrastructure/docker/Dockerfile .

release-dry-run:
	$(PYTHON) tools/maintenance/make_tasks.py release-dry-run

clean:
	$(PYTHON) tools/maintenance/make_tasks.py clean
