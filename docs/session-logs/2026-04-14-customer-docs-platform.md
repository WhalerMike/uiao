---
title: Customer Documentation Platform — Bootstrap Session
date: 2026-04-14
session-id: 733c0924-69cd-41bb-96e3-973fd2771615
topic: customer-docs-platform
participants:
  - Michael Stratton (owner)
  - Claude (claude-opus-4-6, via Cowork mode)
status: IN-PROGRESS
related-adrs:
  - ADR-025 (Continuous Monitoring Program)
related-commits:
  - uiao-core@a4737292
  - uiao-docs@3890eb3
  - uiao-gos@e593daf
---

# Customer Documentation Platform — Bootstrap Session

## Context

Michael is standing up a **Customer Documentation Platform** spanning three GitHub repositories he owns:

- **`WhalerMike/uiao-core`** — FedRAMP-Moderate federal governance canon (authoritative source of truth for state machines, adapter registries, enforcement rules).
- **`WhalerMike/uiao-docs`** — FedRAMP-Moderate federal documentation (derived consumer of `uiao-core` canon; articles, guides, playbooks, appendices).
- **`WhalerMike/uiao-gos`** — Commercial AD → Entra ID migration product (firewalled from the federal pair; GCC-Moderate M365 SaaS only; Amazon Connect in Commercial Cloud as declared exception).

This session picks up from a prior working session (session-id `733c0924-69cd-41bb-96e3-973fd2771615`) whose transcript runs ~62 turns and was embedded inline in **ADR-025** as a one-shot dump. Going forward, session transcripts live in this directory per the convention in `README.md`, and ADRs stay scoped to discrete decisions.

## Prior-Session Summary (carried over)

The prior session accomplished:

1. **ScubaGear integration design.** Assessed `cisagov/ScubaGear` as a UIAO *Conformance Adapter* (a new adapter class parallel to Modernization Adapter — read-only assessors vs change-making integrators). Selected integration Pattern C (hybrid: native wrap + sidecar), reserved four conformance adapter slots (`scubagear` v1 active; `vuln-scan`, `stig-compliance`, `patch-state` reserved), and established dual runner strategy (Phase 1 `windows-latest`; Phase 2+ Azure Government self-hosted Windows).
2. **Continuous Monitoring Program canon.** Wrote `uiao-core/CONMON.md` (v0.1.0, 21,423 bytes) and extended `uiao-core/ARCHITECTURE.md` §16 with the ISCM six-step lifecycle mapped verbatim to NIST SP 800-137 §§3.1–3.6, cadence and control citations from FedRAMP Continuous Monitoring Playbook v1.0 (2025-11-17), and the canonical 11 security automation domains from 800-137 Appendix D (with IAM correctly placed *inside* Configuration Management, and Incident Management restored after an initial omission).
3. **Source verification.** Reference PDFs (NIST SP 800-137, FedRAMP ConMon Playbook v1.0) were uploaded directly by Michael after egress proxy blocked WebFetch to `nvlpubs.nist.gov` and `fedramp.gov`. PDFs landed at `uiao-core/compliance/reference/nist-sp-800-137/` and `uiao-core/compliance/reference/fedramp-conmon-playbook/` with SHA-256 sidecars and provenance READMEs. Every `UNSURE` marker in ARCHITECTURE.md §16 was verified against the actual source text via `pdftotext` extraction.
4. **Monitoring strategy.** Three-track plan documented in `CONMON.md` §9 for detecting updates to NIST 800-137, FedRAMP Playbook, and ScubaGear. Track 1 selected: GitHub Watch subscription on `cisagov/ScubaGear` releases for the one repo that actually has a feed; FedRAMP and NIST covered via periodic manual check.
5. **ADR-025.** Authored `uiao-docs/docs/adr/adr-025-continuous-monitoring-program.md` (131 KB) capturing decisions D1–D11, consequences, open items C1–C8 (with C3 pin policy and C4 monitoring track both RESOLVED in-session), and the full 62-turn transcript inline.
6. **Commits landed.**
   - `uiao-core@a4737292` — 7 files changed, 1266+/60− (ARCHITECTURE.md extensions, CONMON.md, reference PDFs + SHA sidecars + READMEs).
   - `uiao-docs@3890eb3` — 2 files changed, 2025+/5− (ADR-025 + supporting updates).
   - `uiao-gos@e593daf` — 2 files changed, 226+/45− (ARCHITECTURE.md for commercial product; originally blocked by stale `.git/index.lock` from a crashed sandbox git call; unblocked manually in PowerShell).

The full pre-compaction transcript is preserved in:

- `/sessions/dreamy-blissful-hamilton/mnt/.claude/projects/-sessions-dreamy-blissful-hamilton/733c0924-69cd-41bb-96e3-973fd2771615.jsonl` (raw JSONL)
- `uiao-docs/docs/adr/adr-025-continuous-monitoring-program.md` (narrative form, committed as `3890eb3`)

## Pending Work (queued at start of this session)

1. Unblock `uiao-gos` commit (stale `index.lock`). ✅ **DONE** — commit `e593daf` this session.
2. **Step 0a** — Create `canon/adapter-registry.yaml` and `canon/modernization-registry.yaml` in `uiao-core`, seeded with:
   - Modernization class: `entra-id`, `m365`, `service-now`, `palo-alto`, `scuba` (baseline target).
   - Conformance class: `scubagear` (Phase 1 active), plus reserved slots `vuln-scan`, `stig-compliance`, `patch-state`.
3. **Step 0a supporting** — Update `schemas/adapter-registry.schema.json` to accept the new `class: modernization | conformance` field.
4. **Step 0b** — Create `tools/sync_canon.py` and cross-repo sync workflows (`canon-sync-dispatch.yml` in `uiao-core`, `canon-sync-receive.yml` in `uiao-docs`).
5. **Steps 1–7** — Customer-documents tree expansion (Quarto `.qmd` conversion, `IMAGE-PROMPTS.md` siblings, `images/` folders, Master Document, `generate_images.py`, `aggregate_prompts.py`, Git LFS config with `lfs_budget_check.py`, Quarto landing page).
6. **Owner-side action** — Set up GitHub Watch subscription on `cisagov/ScubaGear` releases (Track 1 monitoring).

---

## Turn 1 — 2026-04-14T14:45Z — Michael

> PS C:\\Users\\whale\\uiao-gos> ...
> [master e593daf] [UIAO-GOS] CREATE: ARCHITECTURE.md — commercial product architecture (firewalled from federal pair)
>  2 files changed, 226 insertions(+), 45 deletions(-)

**Interpretation:** Confirmation that the `uiao-gos` commit unblocked successfully after removing the stale `.git/index.lock` and re-running `git add` + `git commit`. All three repositories are now current.

**Actions:** None required — pure status report from owner.

---

## Turn 2 — 2026-04-14T15:00Z — Michael

> The Word!

**Interpretation:** Affirmative to the session-log proposal from the prior turn, with a nudge toward Word-document output (the `docx` skill had just been surfaced in the skills reminder).

**Actions (Claude):**

- Called `AskUserQuestion` with two clarifying questions:
  - *Format:* Word only / Word + Markdown mirror / Markdown only.
  - *Location:* `uiao-docs/docs/session-logs/` (recommended) / `uiao-docs/session-journals/` (top-level).

---

## Turn 3 — 2026-04-14T15:04Z — Michael

**Answers via `AskUserQuestion`:**

- Format: **Word + Markdown mirror**
- Location: **`uiao-docs/docs/session-logs/` (Recommended)**

**Actions (Claude):**

- Invoked `docx` skill (pandoc available at `/usr/bin/pandoc` 2.9.2.1 — will use `pandoc` for `.md → .docx` mirror conversion rather than hand-crafted docx-js, since the MD is authoritative and the DOCX is purely derived).
- Created `uiao-docs/docs/session-logs/README.md` documenting the convention:
  - MD is source of truth, DOCX is regenerated mirror.
  - Naming: `YYYY-MM-DD-<kebab-topic>.md` + matching `.docx`.
  - Structure: YAML frontmatter + Context + per-turn entries with ISO timestamps and Actions blocks.
  - Append cadence: after every substantive (tool-using) turn.
  - Commit cadence: owner's choice; suggested PowerShell one-liner provided.
  - Relationship to ADRs clearly delineated (ADR = signed-off ruling, session log = working tape).
- Created this file (`2026-04-14-customer-docs-platform.md`) seeded with prior-session context carried over from the pre-compaction summary.
- Generated the paired `2026-04-14-customer-docs-platform.docx` via `pandoc <this-file>.md -o <this-file>.docx`.

**Files touched:**

- `uiao-docs/docs/session-logs/README.md` (new)
- `uiao-docs/docs/session-logs/2026-04-14-customer-docs-platform.md` (new — this file)
- `uiao-docs/docs/session-logs/2026-04-14-customer-docs-platform.docx` (new, derived)

**Commit hand-off (PowerShell):**

```powershell
Set-Location 'C:\Users\whale\uiao-docs'
git add docs/session-logs/
git commit -m "[UIAO-DOCS] CREATE: docs/session-logs/ — session-log convention + 2026-04-14 customer-docs-platform log"
git push
```

---

---

## Turn 4 — 2026-04-14T15:12Z — Michael

> [Confirmed commit `2a67d07` on uiao-docs pushed successfully. GitHub flagged "Build and Deploy Documentation" required status check as expected-but-bypassed — owner has admin override rights.]

**Interpretation:** Session-log scaffold is live on GitHub. Clear to proceed with Step 0a (adapter registries).

**Actions (Claude):**

- Updated todo list with Step 0a subtasks.
- Read `uiao-core/canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md` (268 lines) to confirm the canonical doctrinal adapter taxonomy.
- **Discovered taxonomy collision.** UIAO_003 names four doctrinal adapter classes (Identity, Telemetry, Policy, Enforcement — three of four still `NEW (Proposed)`), while the prior session committed `class: modernization | conformance` into `ARCHITECTURE.md` §3.2 as the adapter-registry field. These are orthogonal axes, not competing taxonomies. Paused to surface to owner via `AskUserQuestion`.

## Turn 5 — 2026-04-14T15:15Z — Michael (via AskUserQuestion)

**Answer:** Dual-axis (Recommended) — registry carries both `class` (operational) and `mission-class` (doctrinal) as orthogonal fields.

**Actions (Claude):**

- Inspected existing `uiao-core/schemas/` — found subdirectory convention (`ksi/`, `udc/`, `uiao-api/`); created `schemas/adapter-registry/` to match.
- Created **`uiao-core/schemas/adapter-registry/adapter-registry.schema.json`** (JSON Schema draft-07) with:
  - `registry-class: modernization | conformance` at the registry level (pins each file to one operational axis).
  - `class: modernization | conformance` on every adapter entry (operational axis).
  - `mission-class: identity | telemetry | policy | enforcement | unmapped | mixed` on every adapter entry (doctrinal axis).
  - `mission-class-notes` required when mission-class is `unmapped` or `mixed` (enforced via `allOf`/`if`/`then`).
  - `successor` required when status is `deprecated` or `retired`.
  - Canon invariant fields: `gcc-boundary` (enum pinning to `gcc-moderate` or `commercial-exception-amazon-connect`), `ssot-mutation` (enum locked to `never`), `certificate-anchored` (boolean, must be true), `object-identity-only` (boolean, must be true).
  - Operational fields: `phase`, `vendor`, `license`, `runtime`, `runtime-version`, `runner-class`, `tenancy`, `policy-engine`, `policy-pin`, `scope`, `outputs`, `triggers`, `evidence-class`, `retention-years`, `controls` (NIST SP 800-53 pattern validation), `automation-domain` (NIST SP 800-137 Appendix D enum — all 11 canonical domains).
  - `additionalProperties: false` on both registry root and adapter entries (strict schema; any unknown field fails CI).

- Created **`uiao-core/canon/modernization-registry.yaml`** (`registry-class: modernization`, 5 adapters):
  - `entra-id` — Microsoft Entra ID, active, phase-1, controls CM-8/IA-2/IA-4/AC-2.
  - `m365` — Microsoft 365 tenant (Graph API), active, phase-1, controls CM-2/CM-3/CM-8.
  - `service-now` — ServiceNow ITSM, active, phase-1, controls IR-4/IR-5/IR-6/CM-3, evidence-class `incident`.
  - `palo-alto` — Palo Alto NGFW, active, phase-1, controls SC-7/CM-7/AC-4, runner-class `on-prem-self-hosted`.
  - `scuba` — CISA SCuBA baseline (target state — distinct from the assessment tool), active, phase-1, controls CM-2/CM-6/CM-7.
  - All 5 declare `mission-class: unmapped` with `mission-class-notes` referencing ODA-15.

- Created **`uiao-core/canon/adapter-registry.yaml`** (`registry-class: conformance`, 4 slots):
  - `scubagear` — **active**, phase-1, `mission-class: policy`, runtime `powershell-7.4` pinned `1.5.1`, policy-engine `opa-rego`, policy-pin `main` (with monthly bump per CONMON.md §6), scope `[aad, defender, exo, powerbi, powerplatform, sharepoint, teams]`, controls CA-2/CA-5/CA-7/CM-6/CM-8/RA-5, automation-domain `configuration-management`, references ADR-025.
  - `vuln-scan` — **reserved**, phase-planning, `mission-class: telemetry`, controls RA-5/RA-5(5)/CA-7/SI-2, automation-domain `vulnerability-management`.
  - `stig-compliance` — **reserved**, phase-planning, `mission-class: policy`, controls CM-6/CM-7/CA-7, automation-domain `configuration-management`.
  - `patch-state` — **reserved**, phase-planning, `mission-class: telemetry`, controls SI-2/CM-8/CA-7, automation-domain `patch-management`.

- **Validated both YAMLs** against the schema with a Draft-07 validator (`jsonschema` + `pyyaml`, `--break-system-packages`):
  - Initial failure: `updated: 2026-04-14` parsed as `datetime.date` (PyYAML default), schema expected `string`. Fix: quoted the date value in both YAMLs.
  - Final result: **both files clean, 9 adapters total (5 modernization + 4 conformance).** Mission-class distribution: 5 unmapped (all modernization, pending ODA-15), 2 policy (scubagear, stig-compliance), 2 telemetry (vuln-scan, patch-state).

- Updated **`uiao-core/ARCHITECTURE.md`**:
  - §3.1 file-listing block rewritten to show the real on-disk layout (two YAML files in `canon/`, schema in `schemas/adapter-registry/`).
  - §3.2 retitled from "Adapter registry schema (NEW, Proposed)" to "Adapter registry schema — dual-axis taxonomy". New prose explains why two axes exist, what each one encodes, and why separation matters (prevents the operational choice from ratifying the doctrinal one; lets UIAO_003 evolve without forcing a registry migration). YAML excerpt rewritten to show both a modernization entry (entra-id) and a conformance entry (scubagear) with their full invariant fields.
  - §13 — added **ODA-15** describing the modernization mission-class gap with three resolution options: (a) add a fifth canonical class "Integration" to UIAO_003, (b) re-scope `enforcement` to cover target-environment changes, or (c) accept `unmapped` permanently as the dual-axis model's final answer.
  - §14 change-log — added 0.5.0 entry for "Step 0a — Adapter registries landed".

**Files touched:**

| Path | Action |
|---|---|
| `uiao-core/schemas/adapter-registry/adapter-registry.schema.json` | new |
| `uiao-core/canon/modernization-registry.yaml` | new |
| `uiao-core/canon/adapter-registry.yaml` | new |
| `uiao-core/ARCHITECTURE.md` | updated (§3.1, §3.2, §13, §14) |
| `uiao-docs/docs/session-logs/2026-04-14-customer-docs-platform.md` | updated (this append) |
| `uiao-docs/docs/session-logs/2026-04-14-customer-docs-platform.docx` | regenerated via pandoc |

**Commit hand-off (PowerShell):**

```powershell
# uiao-core — Step 0a registries + schema + ARCHITECTURE.md dual-axis
Set-Location 'C:\Users\whale\uiao-core'
git add schemas/adapter-registry/ canon/adapter-registry.yaml canon/modernization-registry.yaml ARCHITECTURE.md
git commit -m "[UIAO-CORE] CREATE: Step 0a — adapter registries (dual-axis taxonomy) + ARCHITECTURE.md v0.5.0"
git push

# uiao-docs — session log append
Set-Location 'C:\Users\whale\uiao-docs'
git add docs/session-logs/2026-04-14-customer-docs-platform.md docs/session-logs/2026-04-14-customer-docs-platform.docx
git commit -m "[UIAO-DOCS] LOG: append Turn 4-5 — Step 0a adapter registries landed"
git push
```

---

## Next Up

- **Step 0a supporting — tooling.** Add a small Python validator (`tools/validate_registries.py`) and wire it into the existing CI gates (`metadata-validator` check). Also consider a canonical-YAML linter (enforce key ordering so diffs stay clean).
- **Step 0b — Cross-repo sync.** Build `uiao-core/tools/sync_canon.py` + `.github/workflows/canon-sync-dispatch.yml`, and the matching receiver `uiao-docs/.github/workflows/canon-sync-receive.yml`. This is what turns the registries from static files into a propagating source of truth.
- **ODA-15 resolution.** At some point Michael picks (a), (b), or (c). Until then, modernization adapters stay `unmapped` and any canon review of UIAO_003 must carry ODA-15 as a blocker for promoting §4.2–§4.5 from NEW (Proposed) to canonical.
- **Track 1 monitoring action item.** Owner still needs to subscribe to `cisagov/ScubaGear` releases on GitHub (prior session carryover).
