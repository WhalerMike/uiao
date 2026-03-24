# PROJECT-CONTEXT.md – Single Source of Truth for UIAO Ecosystem

**Last Updated**: 2026-03-24
**Owner**: whalermike
**Mission**: Build a production-capable, single-YAML-canon pipeline that generates auditor-accepted FedRAMP Moderate Rev 5 artifacts with real evidence and continuous monitoring hooks.

## Core Architecture (Do Not Deviate Without Updating This File)
- **Primary Repo**: uiao-core https://github.com/WhalerMike/uiao-core
- **Validation Target**: uiao-validation-targets https://github.com/WhalerMike/uiao-validation-targets
  - FastAPI mock service running at http://localhost:8000 (or Docker)
  - Endpoints: /health, /ingest-evidence, /telemetry, /validation/fedramp-rev5-baseline
  - All evidence must use `prop:id` prefix and valid UUIDv4
- **Single Source of Truth**: The YAML canon file in uiao-core
- **Output Artifacts**: OSCAL 1.3.0 (Component Definition, SSP skeleton, POA&M), Markdown/DOCX/PDF/HTML via uiao CLI

## AI Orchestration Rules (All Agents Must Follow)

1. **Hierarchy**
   - **Comet-Perplexity**: Top-level orchestrator and task assigner
   - **Claude Code**: Senior planner + harsh reviewer (use Plan Mode, update CLAUDE.md after every correction)
   - **GitHub Copilot (copilot-swe-agent)**: Fast implementation and auto-fixing only — never the primary decision maker

2. **Memory & Context**
   - Always read this file + AGENTS.md + CLAUDE.md + UIAO-MEMORY.md before starting work
   - After any significant change or mistake, update the relevant memory file and this PROJECT-CONTEXT.md if architecture decisions change
   - Never assume context from previous sessions — explicitly reference files

3. **Quality Gates (Non-Negotiable)**
   - All code must pass ruff linting, pip-audit, and existing CI
   - OSCAL artifacts must validate with compliance-trestle
   - Evidence sent to validation-targets must include proper `prop:id`
   - Before any PR/merge: Claude harsh review (Tip 6 from whiteboard)
   - Use parallel Git worktrees for complex tasks (Tip 1)

4. **Current Priorities (March 2026)**
   - Tight integration between uiao-core and uiao-validation-targets (CLI commands to test against live target)
   - Full SSP control narrative templating with organization-defined parameters
   - Realistic POA&M generation from telemetry events
   - Evidence collection & linking (OSCAL back-matter)
   - Migrate pipeline to secure/GitHub Enterprise-ready setup
   - Expand validation-targets with more scenarios (failure injection, high-volume telemetry, scan imports)

## FedRAMP-Specific Constraints
- Target: FedRAMP Moderate Rev 5 baseline
- Focus: 20x Phase 2 (machine-readable evidence over narrative bloat, continuous monitoring, KSI mapping)
- POA&M statuses allowed: open, closed, risk-accepted, false-positive, operational-requirement, vendor-dependency, not-applicable
- Public repo rule: Never commit CUI or production artifacts here

## Decision Log (Add new entries at top)
- 2026-03-24: Created PROJECT-CONTEXT.md to prevent context collision across Comet/Copilot/Claude layers
- 2026-03-24: uiao-validation-targets bootstrapped as live mock telemetry endpoint
- 2026-03-23: Agentic workflow bootstrapped with AGENTS.md

---

**Instruction to All Agents**:
Before starting any task, read this file in full. If your change affects architecture, update this file and reference the commit. Ruthlessly simplify orchestration — do not create new agents without updating this context.
