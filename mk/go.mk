##@ Go Compiler (tools/sdd-compile)

.PHONY: build-compiler test-compiler-go
build-compiler: ## Build the sdd-compile Go binary
	go build -C tools/sdd-compile -o "bin/sdd-compile$$(go env GOEXE)" .

test-compiler-go: ## Run sdd-compile Go tests
	go test -C tools/sdd-compile ./tests/ -count=1

# gremlins version pinned (doc 04/03 policy: no @latest in any build/test path —
# see docs/adr for the supply-chain rationale already applied to govulncheck).
# Scope is the two "critical module" categories doc 04 names for Go
# (parsers, assinatura/signing) — not the whole compiler, matching mutation
# testing's own "Agendado/release, block em módulos críticos" cadence, not a
# per-PR gate. internal/parser currently has no _test.go file at all, so it
# reports 0% mutator coverage by design, not tool failure — that gap is
# itself the finding, not something to hide by excluding the package.
.PHONY: mutation-go
mutation-go: ## Run Go mutation testing on signing + parser (scheduled, not per-PR)
	cd tools/sdd-compile && go run github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0 unleash ./internal/signing
	cd tools/sdd-compile && go run github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0 unleash ./internal/parser

# --- Namespaced aliases (additive, non-breaking — see proposal.md Decision D2) ---
.PHONY: go.build go.test go.mutation
go.build: build-compiler
go.test: test-compiler-go
go.mutation: mutation-go
