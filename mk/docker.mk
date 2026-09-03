##@ Docker

.PHONY: docker-build docker.build
docker-build: ## Build Docker image with BuildKit/buildx
	$(PYTHON) tools/maintenance/make_tasks.py docker-build --flags "$(DOCKER_BUILD_FLAGS)"

# --- Namespaced alias (additive, non-breaking; see proposal.md Decision D2) ---
docker.build: docker-build
