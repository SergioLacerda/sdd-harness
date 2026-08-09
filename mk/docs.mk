##@ Docs

docs-link-check: ## Check internal relative links in docs
docs-link-fix: ## Apply deterministic internal-link rewrites

DOCS_TASKS := docs-link-check docs-link-fix

.PHONY: $(DOCS_TASKS)
$(DOCS_TASKS):
	$(PYTHON) tools/maintenance/make_tasks.py $@

.PHONY: docs-build docs-serve
docs-build: build-web ## Build composed site (Astro + MkDocs + Selector)
	$(PYTHON) -m mkdocs build --strict
	@# selector_compiler_cli uses a relative import (needs -m, so it can't
	@# self-insert its own sys.path like tools/maintenance/lint_all.py does) —
	@# export PYTHONPATH so it resolves without sdd_wizard/sdd_core being
	@# uv-sync-installed as editables first. See WORKSPACE_PYTHONPATH above.
	PYTHONPATH="$(WORKSPACE_PYTHONPATH)$${PYTHONPATH:+:$$PYTHONPATH}" \
	  $(PYTHON) -m sdd_wizard.orchestration.wizard.selector_compiler_cli --output-dir build/site/selector

docs-serve: docs-build ## Build full site (docs + selector) and serve on http://localhost:8000/sdd-harness/
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

# --- Namespaced aliases (additive, non-breaking — see proposal.md Decision D2) ---
.PHONY: docs.build docs.serve docs.link-check docs.link-fix
docs.build: docs-build
docs.serve: docs-serve
docs.link-check: docs-link-check
docs.link-fix: docs-link-fix
