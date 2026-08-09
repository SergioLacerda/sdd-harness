##@ Docker

.PHONY: docker-build docker.build
docker-build: ## Build Docker image with BuildKit/buildx
	cp infrastructure/docker/.dockerignore .dockerignore
	trap 'rm -f .dockerignore' EXIT INT TERM; \
	DOCKER_BUILDKIT=1 docker buildx build --load $(DOCKER_BUILD_FLAGS) \
	  -t sdd-harness -f infrastructure/docker/Dockerfile .

# --- Namespaced alias (additive, non-breaking — see proposal.md Decision D2) ---
docker.build: docker-build
