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

.PHONY: check ci-pr ci-pr-full test lint pre-delivery lock clean coverage coverage-strict docs-build docs-serve docs-link-check docs-link-fix docker-build release-dry-run install install-docs update-golden-snapshots generate-schemas hooks-install governance-bootstrap help golden-policy-check golden-policy-check-strict enforcement-ladder-consistency enforcement-ladder-digest enforcement-threshold-signoff core-compiler-runtime-contract observability-contract-check release-readiness-v1-check runbook-hardening-check

help:
	@echo "SDD Architecture Development"
	@echo "==========================="
	@echo "install         - Install all workspace dependencies (dev)"
	@echo "install-docs    - Install documentation dependencies (mkdocs)"
	@echo "check           - Run all tests (unit + integration + contract)"
	@echo "ci-pr           - Run fast artifact/golden CI parity gates before promotion/push"
	@echo "ci-pr-full      - Run ci-pr plus strict coverage gates"
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
	@echo "docs-link-check - Check internal relative links in docs"
	@echo "docs-link-fix   - Apply deterministic internal-link rewrites"
	@echo "docker-build    - Build Docker image"
	@echo "release-dry-run - Validate version, changelog, and tags before release"
	@echo "clean           - Remove temporary files"

install:
	uv sync --all-groups --all-packages --extra test

install-docs:
	uv sync --group docs

check: golden-status
	$(PYTHON) tools/ci/check_golden_policy.py --mode warn
	$(PYTHON) -m pytest tests packages \
		--cov=packages \
		--cov-report=term-missing:skip-covered

ci-pr:
	$(PYTHON) -m pytest -q \
		tests/contract/test_governance_schema.py::TestGovernanceCoreGoldenFile::test_structure_matches_golden
	$(PYTHON) tools/ci/check_golden_policy.py --mode block
	$(PYTHON) tools/ci/check_core_compiler_runtime_contract.py --mode enforce

ci-pr-full: ci-pr
	$(MAKE) coverage-strict

golden-policy-check:
	$(PYTHON) tools/ci/check_golden_policy.py --mode block

golden-policy-check-strict:
	$(PYTHON) tools/ci/check_golden_policy.py --mode strict

enforcement-ladder-consistency:
	$(PYTHON) tools/ci/check_enforcement_ladder_consistency.py

enforcement-ladder-digest:
	$(PYTHON) tools/ci/enforcement_ladder_digest.py \
		--json-out .artifacts/enforcement_ladder_digest.json \
		--md-out .artifacts/enforcement_ladder_digest.md

enforcement-threshold-signoff:
	$(PYTHON) tools/ci/check_enforcement_threshold_signoff.py

core-compiler-runtime-contract:
	$(PYTHON) tools/ci/check_core_compiler_runtime_contract.py --mode enforce

observability-contract-check:
	$(PYTHON) tools/ci/check_observability_contract.py

release-readiness-v1-check:
	$(PYTHON) tools/ci/check_release_readiness_v1.py

runbook-hardening-check:
	$(PYTHON) tools/ci/check_runbook_hardening_protocol.py

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

docs-link-check:
	$(PYTHON) tools/docs/check_links.py --mode ci

docs-link-fix:
	$(PYTHON) tools/docs/check_links.py --mode fix

docker-build:
	cp infrastructure/docker/.dockerignore .dockerignore
	docker build -t sdd-harness -f infrastructure/docker/Dockerfile .

release-dry-run:
	$(PYTHON) tools/maintenance/make_tasks.py release-dry-run

clean:
	$(PYTHON) tools/maintenance/make_tasks.py clean
