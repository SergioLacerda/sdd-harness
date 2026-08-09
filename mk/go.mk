##@ Go Compiler (tools/sdd-compile)

.PHONY: build-compiler test-compiler-go
build-compiler: ## Build the sdd-compile Go binary
	go build -C tools/sdd-compile -o "bin/sdd-compile$$(go env GOEXE)" .

test-compiler-go: ## Run sdd-compile Go tests
	go test -C tools/sdd-compile ./tests/ -count=1

# --- Namespaced aliases (additive, non-breaking — see proposal.md Decision D2) ---
.PHONY: go.build go.test
go.build: build-compiler
go.test: test-compiler-go
