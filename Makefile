# Cross-platform note: on Windows use Git Bash or WSL to run make targets.
# All shell commands are POSIX-compatible within a bash/sh context.
#
# Use uv run if uv is available; fall back to direct execution (e.g. inside Docker)
VENV_PYTHON := $(firstword $(wildcard .venv/bin/python .venv/Scripts/python.exe))
UV := $(shell command -v uv 2>/dev/null)

ifeq ($(strip $(VENV_PYTHON)),)
  ifeq ($(strip $(UV)),)
    PYTHON := $(shell echo 'ERROR: no .venv found and uv is not installed. Run `make install` first.' >&2; echo false)
  else
    PYTHON := uv run python
  endif
else
  PYTHON := $(VENV_PYTHON)
endif

.PHONY: check ci-pr ci-pr-full test test-fast test-perf lint pre-delivery lock clean coverage coverage-strict docs-build docs-serve docs-link-check docs-link-fix docker-build release-dry-run install install-docs update-golden-snapshots generate-schemas hooks-install governance-bootstrap help golden-policy-check golden-policy-check-strict enforcement-ladder-consistency enforcement-ladder-digest enforcement-threshold-signoff signoff-draft core-compiler-runtime-contract observability-contract-check release-readiness-v1-check runbook-hardening-check build-compiler test-compiler-go lint-go install-web build-web lint-web test-web cover-web

help:
	@echo "SDD Architecture Development"
	@echo "==========================="
	@echo "install         - Install all workspace dependencies (dev)"
	@echo "install-docs    - Install documentation dependencies (mkdocs)"
	@echo "check           - Run CI-safe tests (unit + integration + contract, no perf)"
	@echo "ci-pr           - Run fast artifact/golden CI parity gates before promotion/push"
	@echo "ci-pr-full      - Run ci-pr plus strict coverage gates"
	@echo "test            - Run full multi-layer test pipeline with unified coverage gate"
	@echo "test-fast       - Run packages/tests with -x --ff (no perf tests)"
	@echo "test-perf       - Run performance/benchmark tests (excluded from other test targets)"
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
	@echo "docs-build      - Build composed site (Astro + MkDocs + Selector)"
	@echo "docs-serve      - Build full site (docs + selector) and serve on http://localhost:8000/sdd-harness/"
	@echo "docs-link-check - Check internal relative links in docs"
	@echo "docs-link-fix   - Apply deterministic internal-link rewrites"
	@echo "docker-build    - Build Docker image"
	@echo "release-dry-run - Validate version, changelog, and tags before release"
	@echo "clean           - Remove temporary files"
	@echo "install-web     - Install apps/landing dependencies (npm ci)"
	@echo "build-web       - Build the landing app (apps/landing) into build/site/"
	@echo "lint-web        - Run landing app diagnostics (astro check)"
	@echo "test-web        - Run landing app tests (vitest)"
	@echo "cover-web       - Run landing app coverage (vitest, 70% gate on src/lib)"

build-compiler:
	go build -C tools/sdd-compile -o "bin/sdd-compile$$(go env GOEXE)" .

test-compiler-go:
	go test -C tools/sdd-compile ./tests/ -count=1

lint-go:
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run ./tools/sdd-compile/...; \
	else \
		echo "golangci-lint not installed — skipping Go lint"; \
	fi

install-web:
	cd apps/landing && npm ci

build-web: install-web
	cd apps/landing && npm run build

lint-web: install-web
	cd apps/landing && npm run lint

test-web: install-web
	cd apps/landing && npm run test

cover-web: install-web
	cd apps/landing && npm run cover

install: build-compiler
	uv sync --all-groups --all-packages --extra test

install-docs:
	uv sync --group docs

check: golden-status
	$(PYTHON) tools/maintenance/make_tasks.py check

ci-pr:
	$(PYTHON) tools/maintenance/make_tasks.py ci-pr

ci-pr-full: ci-pr
	$(MAKE) coverage-strict

golden-policy-check:
	$(PYTHON) tools/maintenance/make_tasks.py golden-policy-check

golden-policy-check-strict:
	$(PYTHON) tools/maintenance/make_tasks.py golden-policy-check-strict

enforcement-ladder-consistency:
	$(PYTHON) tools/maintenance/make_tasks.py enforcement-ladder-consistency

enforcement-ladder-digest:
	$(PYTHON) tools/maintenance/make_tasks.py enforcement-ladder-digest

enforcement-threshold-signoff:
	$(PYTHON) tools/maintenance/make_tasks.py enforcement-threshold-signoff

signoff-draft:
	$(PYTHON) tools/maintenance/make_tasks.py signoff-draft

core-compiler-runtime-contract:
	$(PYTHON) tools/maintenance/make_tasks.py core-compiler-runtime-contract

observability-contract-check:
	$(PYTHON) tools/maintenance/make_tasks.py observability-contract-check

release-readiness-v1-check:
	$(PYTHON) tools/maintenance/make_tasks.py release-readiness-v1-check

runbook-hardening-check:
	$(PYTHON) tools/maintenance/make_tasks.py runbook-hardening-check

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
	$(PYTHON) tools/maintenance/make_tasks.py test-fast

test-perf:
	$(PYTHON) tools/maintenance/make_tasks.py test-perf

coverage:
	$(PYTHON) tools/maintenance/make_tasks.py coverage

coverage-strict:
	$(PYTHON) tools/maintenance/make_tasks.py coverage-strict

update-golden-snapshots:
	$(PYTHON) tools/maintenance/make_tasks.py update-golden-snapshots

generate-schemas:
	$(PYTHON) tools/maintenance/make_tasks.py generate-schemas

hooks-install:
	bash .github/setup-precommit-hook.sh

governance-bootstrap:
	$(PYTHON) tools/maintenance/make_tasks.py governance-bootstrap

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

docs-build: build-web
	$(PYTHON) -m mkdocs build --strict
	$(PYTHON) -m sdd_wizard.orchestration.wizard.selector_compiler_cli --output-dir build/site/selector

docs-serve: docs-build
	@# The Astro landing app is built with base: '/sdd-harness/' (astro.config.mjs)
	@# for GitHub Pages sub-path deployment, so every href/asset it emits is
	@# prefixed with /sdd-harness/. Serving build/site directly at the server
	@# root breaks those references (unstyled CSS, /sdd-harness/selector/ 404s).
	@# Mount build/site under that same prefix locally so it matches production.
	@# Guard against a partial build/site/ (e.g. a selector-compiler regression)
	@# being served silently — fail loudly instead of a confusing 404 at runtime.
	@test -f build/site/selector/index.html || { \
		echo "ERROR: build/site/selector/index.html missing — selector compiler did not run. Run 'make docs-build' and check its output."; \
		exit 1; \
	}
	@mkdir -p build/serve-root
	@ln -sfn ../site build/serve-root/sdd-harness
	@echo "Serving at http://localhost:8000/sdd-harness/"
	$(PYTHON) -m http.server 8000 --directory build/serve-root

docs-link-check:
	$(PYTHON) tools/maintenance/make_tasks.py docs-link-check

docs-link-fix:
	$(PYTHON) tools/maintenance/make_tasks.py docs-link-fix

docker-build:
	cp infrastructure/docker/.dockerignore .dockerignore
	docker build -t sdd-harness -f infrastructure/docker/Dockerfile .

release-dry-run:
	$(PYTHON) tools/maintenance/make_tasks.py release-dry-run

clean:
	$(PYTHON) tools/maintenance/make_tasks.py clean
