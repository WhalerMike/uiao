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

# Bash is required for the inbox-convert / inbox-status targets
# (process substitution + null-delimited find). All other rules work
# under either sh or bash — setting SHELL once globally is the least
# intrusive fix.
SHELL        := /bin/bash

REPO_ROOT    := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
export UIAO_WORKSPACE_ROOT := $(REPO_ROOT)
PYTHON       ?= python3
PANDOC       ?= pandoc
IMPL         := $(REPO_ROOT)/impl
DOCS         := $(REPO_ROOT)/docs
INBOX        := $(REPO_ROOT)/inbox

.PHONY: help bootstrap walk drift test test-substrate lint fmt schemas docs check-links clean release branch-prune inbox-convert inbox-status

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
	@echo "  check-links     Crawl live Pages site for broken links (requires pwsh)"
	@echo "                    override: URL=<url> DEPTH=<n>"
	@echo "  clean           Remove build artifacts (docs/_site, impl/dist, __pycache__)"
	@echo "  release TAG=vX.Y.Z  Cut a release (push tag → triggers release.yml)"
	@echo "  branch-prune    Delete local claude/* branches merged to main"
	@echo "  inbox-convert   Convert inbox/*.docx → .md siblings via pandoc (idempotent)"
	@echo "  inbox-status    Show which inbox/*.docx files lack an up-to-date .md sibling"
	@echo ""
	@echo "Workspace root: $(REPO_ROOT)"

bootstrap:
	@bash scripts/bootstrap.sh

walk:
	@PYTHONPATH=$(IMPL)/src $(PYTHON) -c "from uiao.impl.cli.substrate import substrate_app; substrate_app(['walk'])"

drift:
	@PYTHONPATH=$(IMPL)/src $(PYTHON) -c "from uiao.impl.cli.substrate import substrate_app; substrate_app(['drift'])"

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

check-links:
	@command -v pwsh >/dev/null 2>&1 || { echo "ERROR: pwsh (PowerShell) not found. Install from https://github.com/PowerShell/PowerShell"; exit 1; }
	@pwsh scripts/check-links.ps1 $(if $(URL),-StartUrl $(URL)) $(if $(DEPTH),-MaxDepth $(DEPTH))

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

# ---------------------------------------------------------------------------
# inbox-convert — pandoc bridge from binary authoring (.docx) to the
# governed markdown pipeline. Siblings are regenerated only when the
# .docx is newer than the .md. The .docx files themselves stay local
# per inbox/.gitignore unless explicitly allowlisted.
#
# Usage:
#   make inbox-convert           # convert every stale inbox/**/*.docx
#   make inbox-status            # dry-run: list files that need conversion
#
# Requirements: pandoc >= 2.19 (install with `winget install pandoc`,
# `brew install pandoc`, or `apt install pandoc`).
# ---------------------------------------------------------------------------

# Shell-loop implementation (not a pattern rule) because the canonical
# inbox/ filenames contain spaces and em-dashes that would break Make's
# target-name quoting. Loop runs in bash so set -o pipefail + quoted
# expansions survive whitespace.

inbox-convert:
	@command -v $(PANDOC) >/dev/null 2>&1 || { echo "ERROR: pandoc not found (install pandoc, or set PANDOC=/path/to/pandoc)"; exit 1; }
	@test -d "$(INBOX)" || { echo "ERROR: $(INBOX) does not exist"; exit 1; }
	@set -eu; \
	converted=0; skipped=0; \
	while IFS= read -r -d '' docx; do \
	  md="$${docx%.docx}.md"; \
	  if [ -f "$$md" ] && [ "$$md" -nt "$$docx" ]; then \
	    skipped=$$((skipped+1)); \
	    continue; \
	  fi; \
	  echo "inbox-convert: $$docx -> $$md"; \
	  $(PANDOC) --from=docx --to=gfm --wrap=none --markdown-headings=atx \
	      --extract-media="$(INBOX)/.media" "$$docx" -o "$$md"; \
	  converted=$$((converted+1)); \
	done < <(find "$(INBOX)" -name '*.docx' -print0 2>/dev/null); \
	echo "inbox-convert: converted=$$converted skipped=$$skipped"

inbox-status:
	@echo "Scanning $(INBOX) for .docx files missing or older than their .md siblings..."
	@set -u; \
	total=0; stale=0; \
	while IFS= read -r -d '' docx; do \
	  total=$$((total+1)); \
	  md="$${docx%.docx}.md"; \
	  if [ ! -f "$$md" ] || [ "$$docx" -nt "$$md" ]; then \
	    echo "  STALE:  $$docx"; \
	    stale=$$((stale+1)); \
	  fi; \
	done < <(find "$(INBOX)" -name '*.docx' -print0 2>/dev/null); \
	if [ $$stale -eq 0 ]; then echo "All $$total docx file(s) have up-to-date .md siblings."; fi
