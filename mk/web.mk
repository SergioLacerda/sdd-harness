##@ Web (apps/landing)

.PHONY: install-web build-web test-web cover-web
install-web: ## Install apps/landing dependencies (npm ci)
	$(PYTHON) tools/maintenance/make_tasks.py install-web

build-web: install-web ## Build the landing app (apps/landing) into build/site/
	$(PYTHON) tools/maintenance/make_tasks.py build-web

test-web: install-web ## Run landing app tests (vitest)
	$(PYTHON) tools/maintenance/make_tasks.py test-web

cover-web: install-web ## Run landing app coverage (vitest, 70% gate on src/lib)
	$(PYTHON) tools/maintenance/make_tasks.py cover-web

# --- Namespaced aliases (additive, non-breaking; see proposal.md Decision D2) ---
.PHONY: web.install web.build web.test web.coverage
web.install: install-web
web.build: build-web
web.test: test-web
web.coverage: cover-web
