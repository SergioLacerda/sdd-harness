##@ Lint

lint: ## Run linters (ruff check + format, mypy, bandit)
lint-fix: ## Auto-fix Python linting issues with ruff (local development)

LINT_TASKS := lint lint-fix

.PHONY: $(LINT_TASKS)
$(LINT_TASKS):
	$(PYTHON) tools/maintenance/make_tasks.py $@

.PHONY: lint-go lint-fix-go
lint-go: ## Run golangci-lint on tools/sdd-compile
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run ./tools/sdd-compile/...; \
	else \
		echo "golangci-lint not installed — skipping Go lint"; \
	fi

lint-fix-go: ## Auto-fix Go lint issues (golangci-lint --fix)
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run --fix ./tools/sdd-compile/...; \
	else \
		echo "golangci-lint not installed — skipping Go lint-fix"; \
	fi

.PHONY: lint-web lint-fix-web
lint-web: install-web ## Run landing app diagnostics (astro check)
	cd apps/landing && npm run lint

lint-fix-web: install-web ## Auto-fix landing app lint issues (no-op: astro check has no --fix)
	@echo "lint-fix-web: apps/landing's lint script is 'astro check', a type/diagnostics"; \
	echo "checker with no autofix mode — nothing to auto-fix. Run 'make lint-web' to see diagnostics."

# --- Namespaced aliases (additive, non-breaking — see proposal.md Decision D2) ---
.PHONY: lint.py lint.py-fix lint.go lint.go-fix lint.web lint.web-fix
lint.py: lint
lint.py-fix: lint-fix
lint.go: lint-go
lint.go-fix: lint-fix-go
lint.web: lint-web
lint.web-fix: lint-fix-web
