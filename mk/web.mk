##@ Web (apps/landing)

.PHONY: install-web build-web test-web cover-web
install-web: ## Install apps/landing dependencies (npm ci)
	cd apps/landing && npm ci

build-web: install-web ## Build the landing app (apps/landing) into build/site/
	cd apps/landing && npm run build

test-web: install-web ## Run landing app tests (vitest)
	cd apps/landing && npm run test

cover-web: install-web ## Run landing app coverage (vitest, 70% gate on src/lib)
	cd apps/landing && npm run cover

# --- Namespaced aliases (additive, non-breaking — see proposal.md Decision D2) ---
.PHONY: web.install web.build web.test web.coverage
web.install: install-web
web.build: build-web
web.test: test-web
web.coverage: cover-web
