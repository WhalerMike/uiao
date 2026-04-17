# UIAO monorepo — common developer tasks
#
# Everything is driven from $UIAO_WORKSPACE_ROOT (auto-exported below).
# Targets are thin — they delegate to the CI workflows' underlying
# commands so local runs agree with CI.
#
# Usage:
#   make               # help
#   make bootstrap     # first-time setup
#   make walk          # substrate walker report
#   make drift         # substrate-drift exit-code gate
#   make test          # full impl pytest
#   make lint          # ruff check + format-check
#   make fmt           # ruff auto-format
#   make schemas       # validate canon YAML + JSON against schemas
#   make docs          # render Quarto site to HTML
#   make release TAG=v0.2.0  # cut a release (push tag → triggers release.yml)

REPO_ROOT    := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
export UIAO_WORKSPACE_ROOT := $(REPO_ROOT)
PYTHON       ?= python3
IMPL         := $(REPO_ROOT)/impl
DOCS         := $(REPO_ROOT)/docs

.PHONY: help bootstrap walk drift test test-substrate lint fmt schemas docs clean release branch-prune

help:
	@echo "UIAO monorepo targets:"
	@echo ""
	@echo "  bootstrap       First-time setup (pip install, pre-commit, substrate check)"
	@echo "  walk            uiao substrate walk (full drift report)"
	@echo "  drift           uiao substrate drift (exit-code gate)"
	@echo "  test            Full impl pytest suite"
	@echo "  test-substrate  Fast substrate walker tests only"
	@echo "  lint            ruff check + ruff format --check"
	@echo "  fmt             ruff check --fix + ruff format (mutate files)"
	@echo "  schemas         Validate canon YAML/JSON against their schemas"
	@echo "  docs            Render Quarto site to HTML (docs/_site/)"
	@echo "  clean           Remove build artifacts (docs/_site, impl/dist, __pycache__)"
	@echo "  release TAG=vX.Y.Z  Cut a release (push tag → triggers release.yml)"
	@echo "  branch-prune    Delete local claude/* branches merged to main"
	@echo ""
	@echo "Workspace root: $(REPO_ROOT)"

bootstrap:
	@bash scripts/bootstrap.sh

walk:
	@PYTHONPATH=$(IMPL)/src $(PYTHON) -c "from uiao_impl.cli.substrate import substrate_app; substrate_app(['walk'])"

drift:
	@PYTHONPATH=$(IMPL)/src $(PYTHON) -c "from uiao_impl.cli.substrate import substrate_app; substrate_app(['drift'])"

test:
	@cd $(IMPL) && PYTHONPATH=src $(PYTHON) -m pytest -q

test-substrate:
	@cd $(IMPL) && PYTHONPATH=src $(PYTHON) -m pytest tests/test_substrate_walker.py -q

lint:
	@cd $(IMPL) && ruff check . && ruff format --check .

fmt:
	@cd $(IMPL) && ruff check --fix . && ruff format .

schemas:
	@$(PYTHON) scripts/validate_schemas.py

docs:
	@cd $(DOCS) && quarto render --to html

clean:
	@rm -rf $(DOCS)/_site $(DOCS)/.quarto $(IMPL)/dist $(IMPL)/build $(IMPL)/*.egg-info
	@find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	@echo "Cleaned build artifacts + __pycache__ + .pytest_cache"

release:
	@if [ -z "$(TAG)" ]; then echo "ERROR: TAG=vX.Y.Z required" >&2; exit 1; fi
	@echo "Tagging $(TAG) and pushing…"
	@git tag -a "$(TAG)" -m "Release $(TAG)"
	@git push origin "$(TAG)"
	@echo "Tag pushed. Watch: https://github.com/WhalerMike/uiao/actions/workflows/release.yml"

branch-prune:
	@git branch --merged main | grep -E "^\s+claude/" | xargs -n 1 git branch -d 2>&1 || echo "(no merged claude/* branches)"
