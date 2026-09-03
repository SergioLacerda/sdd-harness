##@ Go Compiler (tools/sdd-compile)

.PHONY: build-compiler test-compiler-go
build-compiler: ## Build the sdd-compile Go binary
	$(PYTHON) tools/maintenance/make_tasks.py build-compiler

test-compiler-go: ## Run sdd-compile Go tests
	$(PYTHON) tools/maintenance/make_tasks.py test-compiler-go

# gremlins version pinned (doc 04/03 policy: no @latest in any build/test path).
.PHONY: mutation-go
mutation-go: ## Run Go mutation testing on signing + parser (scheduled, not per-PR)
	$(PYTHON) tools/maintenance/make_tasks.py mutation-go

# --- Namespaced aliases (additive, non-breaking; see proposal.md Decision D2) ---
.PHONY: go.build go.test go.mutation
go.build: build-compiler
go.test: test-compiler-go
go.mutation: mutation-go
