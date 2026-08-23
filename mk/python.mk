##@ Python

# Targets that are pure `make_tasks.py <name>` pass-throughs share one recipe.
# `test` is excluded (forwards $(ARGS)); `check` supplies its recipe here but
# keeps its `golden-status` prerequisite declared separately below.
golden-policy-check: ## Check golden-file policy compliance
golden-policy-check-strict: ## Check golden-file policy compliance (strict)
test-fast: ## Run packages/tests with -x --ff (no perf tests)
test-perf: ## Run performance/benchmark tests (excluded from other test targets)
test-unit: ## Run unit-family tests only (everything not integration/contract/golden/perf)
test-integration: ## Run integration-family tests only (-m integration)
test-contract: ## Run contract-family tests only (-m contract)
test-golden: ## Run golden/snapshot-drift tests only (-m golden)
coverage: ## Run tests with HTML coverage report
coverage-strict: ## Per-layer coverage gates (core 90%, features 70%, interfaces 70%)
update-golden-snapshots: ## Update contract test golden files
generate-schemas: ## Regenerate JSON Schema files from Pydantic models
clean: ## Remove temporary files
check: ## Run CI-safe tests (unit + integration + contract, no perf)

PYTHON_TASKS := golden-policy-check golden-policy-check-strict \
  test-fast test-perf test-unit test-integration test-contract test-golden \
  coverage coverage-strict update-golden-snapshots \
  generate-schemas clean check

.PHONY: $(PYTHON_TASKS)
$(PYTHON_TASKS):
	$(PYTHON) tools/maintenance/make_tasks.py $@

check: golden-status

.PHONY: golden-status
golden-status: ## Check golden-file git status (informational; used by `check`)
	@# Informational only, by design: golden-fixture drift is already enforced as
	@# blocking in CI (reusable-test.yml's `check_golden_policy.py --mode block`,
	@# release.yml/release-dry-run.yml's `--mode strict`). This target is a fast,
	@# local heads-up for `make check`, not the enforcement point — see
	@# `tools/maintenance/make_tasks.py:run_check()` for the matching rationale.
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

.PHONY: test
test: ## Run full multi-layer test pipeline with unified coverage gate
	$(PYTHON) tools/maintenance/make_tasks.py test $(ARGS)

.PHONY: mutation-python
mutation-python: ## Run Python mutation testing on registered critical modules (scheduled, not per-PR)
	$(PYTHON) tools/testing/run_mutation_python.py

.PHONY: lock
lock: ## Regenerate uv.lock
	uv lock

.PHONY: install install-docs
install: build-compiler ## Install all workspace dependencies (dev)
	uv sync --all-groups --all-packages --extra test

install-docs: ## Install documentation dependencies (mkdocs)
	uv sync --group docs

# --- Namespaced aliases (additive, non-breaking — see proposal.md Decision D2) ---
.PHONY: py.install py.install-docs py.lock py.clean py.generate-schemas \
  test.check test.all test.fast test.perf test.coverage test.coverage-strict \
  test.golden-status test.golden-policy-check test.golden-policy-check-strict \
  test.update-golden-snapshots test.mutation-python
py.install: install
py.install-docs: install-docs
py.lock: lock
py.clean: clean
py.generate-schemas: generate-schemas
test.check: check
test.all: test
test.fast: test-fast
test.perf: test-perf
test.coverage: coverage
test.coverage-strict: coverage-strict
test.golden-status: golden-status
test.golden-policy-check: golden-policy-check
test.golden-policy-check-strict: golden-policy-check-strict
test.update-golden-snapshots: update-golden-snapshots
test.mutation-python: mutation-python
