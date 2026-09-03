##@ Release / CI Gates

ci-pr: ## Run fast artifact/golden CI parity gates before promotion/push
enforcement-ladder-consistency: ## Verify enforcement ladder consistency
enforcement-ladder-digest: ## Print enforcement ladder digest
enforcement-threshold-signoff: ## Run enforcement threshold signoff
signoff-draft: ## Draft signoff document
core-compiler-runtime-contract: ## Check core/compiler runtime contract
observability-contract-check: ## Check observability contract
release-readiness-v1-check: ## Run release readiness v1 check
runbook-hardening-check: ## Run runbook hardening check
release-dry-run: ## Validate version, changelog, and tags before release

IS_RELEASE_PREPARE := $(filter release-prepare release.prepare,$(MAKECMDGOALS))
ifneq ($(strip $(IS_RELEASE_PREPARE)),)
  RELEASE_VERSION_ARG := $(firstword $(filter-out release-prepare release.prepare,$(MAKECMDGOALS)))
endif
RELEASE_VERSION := $(patsubst v%,%,$(or $(VERSION),$(RELEASE_VERSION_ARG)))

RELEASE_TASKS := ci-pr enforcement-ladder-consistency enforcement-ladder-digest \
  enforcement-threshold-signoff signoff-draft core-compiler-runtime-contract \
  observability-contract-check release-readiness-v1-check runbook-hardening-check \
  release-dry-run

.PHONY: $(RELEASE_TASKS)
$(RELEASE_TASKS):
	$(PYTHON) tools/maintenance/make_tasks.py $@

.PHONY: ci-pr-full
ci-pr-full: ci-pr ## Run ci-pr plus strict coverage gates
	$(MAKE) coverage-strict

.PHONY: release-prepare
release-prepare: ## Insert CHANGELOG.md version header and update README install tag (usage: make release-prepare VERSION=x.y.z)
	$(PYTHON) tools/maintenance/make_tasks.py release-prepare --version "$(RELEASE_VERSION)"

ifneq ($(strip $(RELEASE_VERSION_ARG)),)
.PHONY: $(RELEASE_VERSION_ARG)
$(RELEASE_VERSION_ARG):
	@:
endif

# --- Namespaced aliases (additive, non-breaking — see proposal.md Decision D2) ---
.PHONY: release.ci-pr release.ci-pr-full release.dry-run release.enforcement-consistency \
  release.enforcement-digest release.enforcement-signoff release.signoff-draft \
  release.core-compiler-contract release.observability-check release.readiness-check \
  release.runbook-check release.prepare
release.ci-pr: ci-pr
release.ci-pr-full: ci-pr-full
release.dry-run: release-dry-run
release.enforcement-consistency: enforcement-ladder-consistency
release.enforcement-digest: enforcement-ladder-digest
release.enforcement-signoff: enforcement-threshold-signoff
release.signoff-draft: signoff-draft
release.core-compiler-contract: core-compiler-runtime-contract
release.observability-check: observability-contract-check
release.readiness-check: release-readiness-v1-check
release.runbook-check: runbook-hardening-check
release.prepare: release-prepare
