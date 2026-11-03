# Every target is a thin wrapper, so CI and a laptop run exactly the same commands.
SHELL := bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory

include cluster/versions.env

CLUSTER_NAME ?= triage
KIND_CONFIG ?= cluster/kind-config.yaml
UV_RUN := uv run --frozen
SHELL_SCRIPTS := $(sort $(wildcard scripts/*.sh faults/*/*.sh))
MANIFESTS := $(sort $(wildcard faults/*/manifests cluster/addons/*/components.yaml))

# Fault targets need NAME=<id> naming a folder under faults/.
define require_fault
	@if [[ ! "$(NAME)" =~ ^[a-z0-9-]+$$ || ! -f "faults/$(NAME)/truth.yaml" ]]; then \
	  echo "usage: make $@ NAME=<id>; known faults: $$(cd faults && ls -d */ | tr -d / | xargs)" >&2; \
	  exit 2; \
	fi
endef

.PHONY: help setup lint test validate tools cluster cluster-down smoke \
	addons fault check reset verify-fault diagnose

help: ## List targets
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | expand -t 15

setup: ## Install the pinned Python deps into .venv (uv)
	uv sync --frozen

lint: ## ruff, mypy, yamllint, shellcheck, bash -n
	$(UV_RUN) ruff check .
	$(UV_RUN) ruff format --check .
	$(UV_RUN) mypy
	$(UV_RUN) yamllint --strict .
	$(UV_RUN) shellcheck $(SHELL_SCRIPTS)
	@for f in $(SHELL_SCRIPTS); do bash -n "$$f"; done

test: ## Unit tests (no cluster needed)
	$(UV_RUN) pytest

validate: ## Offline schema check of manifests + workflow lint (needs `make tools`)
	$(if $(MANIFESTS),kubeconform -strict -summary \
	  -kubernetes-version $(KUBECTL_VERSION:v%=%) $(MANIFESTS),@echo "no manifests yet")
	actionlint

tools: ## Install pinned kind, kubectl, kubeconform, actionlint into ~/.local/bin
	scripts/install-tools.sh

cluster: ## Create the kind cluster (context kind-$(CLUSTER_NAME)) and smoke-test it
	@kind version | grep -q "^kind $(KIND_VERSION) " || \
	  echo "warning: kind $(KIND_VERSION) is pinned; found: $$(kind version)" >&2
	kind create cluster --name $(CLUSTER_NAME) --config $(KIND_CONFIG) --wait 120s
	scripts/smoke.sh

cluster-down: ## Delete the kind cluster
	kind delete cluster --name $(CLUSTER_NAME)

smoke: ## Allowlist check + every node Ready
	scripts/smoke.sh

addons: ## Install the add-ons a fault requires: make addons NAME=<id>
	$(require_fault)
	scripts/addons.sh $(NAME)

fault: ## Inject a fault: make fault NAME=<id>
	$(require_fault)
	faults/$(NAME)/inject.sh

check: ## Exit 0 only if the fault's symptom is visible: make check NAME=<id>
	$(require_fault)
	faults/$(NAME)/check.sh

reset: ## Remove everything the fault created: make reset NAME=<id>
	$(require_fault)
	faults/$(NAME)/reset.sh

verify-fault: ## Full CI lifecycle for one fault: make verify-fault NAME=<id>
	$(require_fault)
	scripts/verify-fault.sh $(NAME)

diagnose: ## Dump a fault namespace's state for debugging: make diagnose NAME=<id>
	$(require_fault)
	scripts/diagnose.sh $(NAME)
