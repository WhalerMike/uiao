# UIAO Continuous Monitoring Program (CONMON)

> Operational companion to `ARCHITECTURE.md` §16. This document holds the runbook detail — adapter schemas, workflow yaml skeletons, evidence schema, POA&M feed, SCR playbook, reference-monitoring procedure. For strategy and architectural context, read `ARCHITECTURE.md` §16 first.

**Version:** 0.1.0 (NEW, Proposed)
**Cloud boundary:** GCC-Moderate (M365 SaaS); Azure Government for Phase 3+ host-level.
**Scope:** All modules of the consolidated `WhalerMike/uiao` monorepo (`core/`, `docs/`, `impl/`) under a single FedRAMP-Moderate posture. The registered directory-migration IPAM adapters (`bluecat-address-manager`, `infoblox` in `core/canon/modernization-registry.yaml`) are in scope like any other modernization adapter; see ADR-028 for the history of the dissolved federal/commercial firewall.

---

## 1. Program authority and references

| Reference | Version / Date | Local copy | Role |
|---|---|---|---|
| NIST SP 800-137 | September 2011 | `compliance/reference/nist-sp-800-137/NIST.SP.800-137.pdf` | ISCM lifecycle and eleven security automation domains (Appendix D) |
| FedRAMP Continuous Monitoring Playbook | v1.0, 2025-11-17 | `compliance/reference/fedramp-conmon-playbook/FedRAMP_Continuous_Monitoring_Playbook.pdf` | Rev 5 ConMon cadence, POA&M, SCR, vulnerability scanning, annual assessment, incident communications |
| NIST SP 800-53 Rev 5 | Current | `compliance/reference/` (future) | Control catalog referenced by Playbook |
| CISA ScubaGear | Latest release | external (github.com/cisagov/ScubaGear) | M365 baseline assessment tool |

Authority precedence: **FedRAMP Playbook** > **NIST 800-137** > **800-53 Rev 5** on questions of cadence and deliverable format. **800-137** is the canonical source for ISCM process and capability taxonomy.

---

## 2. ISCM lifecycle — operational runbook

Mapped against NIST SP 800-137 §§3.1–3.6 and FedRAMP Playbook §§2–7.

### 2.1 Define ISCM strategy (800-137 §3.1)

**Artifact:** `canon/conmon/strategy.md` (to be created).
**Owner:** `canon-steward` subagent.
**Review cadence:** Annual, aligned to FedRAMP annual assessment cycle (Playbook §4).

The strategy doc captures:
- Organizational risk tolerance (agency-provided).
- Scope boundary (M365 tenant IDs, Azure Gov subscription IDs in Phase 2+).
- Monitoring frequencies per control family.
- Roles (CSP, agency AO, PMO, CISA, 3PAO — per Playbook §2).
- Metrics and success criteria.
- Reference to `adapter-registry.yaml` for the canonical conformance-adapter list.

### 2.2 Establish an ISCM program (800-137 §3.2)

**Artifact:** `canon/adapter-registry.yaml` — Conformance Adapter entries (class: conformance).
**Owner:** Michael + `canon-steward`.
**Cadence:** On-change. Every new conformance adapter requires a canon PR.

Entry-adding workflow:
1. Author `canon/adapters/<adapter-id>.md` — source-of-truth description.
2. Add `class: conformance` entry to `canon/adapter-registry.yaml` per schema in `ARCHITECTURE.md` §3.2.
3. `canon-sync-dispatch.yml` fires `repository_dispatch` to `uiao-docs` to scaffold adapter docs (§4 of `ARCHITECTURE.md`).
4. Build adapter runner under `adapters/<adapter-id>/`.
5. Write adapter-specific workflow (e.g., `conformance-scubagear.yml`) or attach to shared `conformance-run.yml`.

### 2.3 Implement an ISCM program (800-137 §3.3)

**Artifacts:** `adapters/<adapter-id>/`, GitHub Actions workflows (see §5 of this document).
**Owner:** Adapter implementer.
**Cadence:** Continuous — workflows trigger on schedule and events.

### 2.4 Analyze data and report findings (800-137 §3.4)

**Artifacts:** `conmon-aggregate.yml`, `tools/conmon_aggregate.py` (to be created), `dashboard/conmon-dashboard.json`, `poam/poam-<YYYY-MM>.csv`.
**Owner:** `canon-steward`.
**Cadence:** After every conformance adapter run; monthly rollup.

### 2.5 Respond to findings (800-137 §3.5)

**Artifact:** POA&M lifecycle in `uiao-docs` plus `poam/` tracking folder in `uiao`.
**Owner:** Michael (CSP role).
**Cadence:** Monthly POA&M submission (Playbook §2).

### 2.6 Review and update the monitoring program and strategy (800-137 §3.6)

**Artifact:** `canon/conmon/strategy.md` version bumps; `ARCHITECTURE.md` §14 change log.
**Owner:** `canon-steward`.
**Cadence:** Annual, plus on-change for significant policy shifts.

---

## 3. Conformance Adapter schema (full)

Defined in `ARCHITECTURE.md` §3.2 with abbreviated schema. Full operational schema below.

```yaml
# canon/adapter-registry.yaml — conformance class entry (full schema)
- id: scubagear                       # kebab-case, unique within registry
  class: conformance                  # modernization | conformance
  display-name: CISA ScubaGear (M365 SCuBA baseline)
  status: active                      # active | proposed | deprecated
  cloud-boundary: gcc-moderate

  # Provenance
  vendor: cisa                        # owning organization
  upstream-url: https://github.com/cisagov/ScubaGear
  license: CC0                        # UNSURE — pending repo read
  license-ref: LICENSE                # relative path in upstream repo

  # Runtime
  runtime: powershell                 # powershell | python | node | binary
  runtime-version: ">=5.1"            # semver-style range
  runner-class: windows-latest        # maps to GitHub Actions runner label
  tenancy: per-tenant                 # per-tenant | per-subscription | per-host

  # Scope of assessment
  scope:
    - entra
    - exchange
    - sharepoint
    - teams
    - power-platform
    - defender-o365

  # Policy evaluation
  policy-engine: opa-rego
  policy-source: upstream             # upstream | forked | local
  policy-pin: ""                      # commit SHA or tag if forked/pinned

  # Outputs
  outputs:
    - type: report-html
      path-template: "evidence/conformance/{adapter-id}/{run-id}/report.html"
    - type: findings-json
      path-template: "evidence/conformance/{adapter-id}/{run-id}/findings.json"
    - type: poam-csv
      path-template: "evidence/conformance/{adapter-id}/{run-id}/poam.csv"

  # Execution triggers
  triggers:
    - kind: schedule
      cron: "0 2 1 * *"               # monthly, 1st of month, 02:00 UTC
    - kind: event
      event: modernization-completed  # repository_dispatch after modernization adapter
    - kind: manual                    # workflow_dispatch

  # Evidence classification
  evidence-class: iscm-automated      # iscm-automated | iscm-manual | annual
  retention-years: 3                  # align to FedRAMP document retention (UNSURE #8)

  # Canon wiring
  canonical-source: canon/adapters/scubagear.md
  docs-required:
    - adapter-technical-specifications
    - adapter-validation-suites
  added: 2026-04-14
```

**Schema validation:** `schemas/adapter-registry.schema.json` (to be updated — current schema predates the `class` field).

---

## 4. Evidence schema

Each conformance adapter run produces a directory under `evidence/conformance/<adapter-id>/<run-id>/`.

```
evidence/conformance/scubagear/2026-04-15T02-00-00Z-abc123/
├── metadata.json                # run provenance
├── report.html                  # human-readable report (ScubaGear native)
├── findings.json                # normalized findings (UIAO schema)
├── poam.csv                     # POA&M rows (FedRAMP template shape)
├── raw/                         # adapter-native raw output
│   └── <tool-specific>
└── sha256sums.txt               # integrity manifest
```

### 4.1 `metadata.json` schema

```json
{
  "adapter-id": "scubagear",
  "adapter-version": "<upstream-version>",
  "policy-pin": "<commit-sha>",
  "run-id": "2026-04-15T02-00-00Z-abc123",
  "trigger": {"kind": "schedule", "cron": "0 2 1 * *"},
  "tenant": {"kind": "m365", "tenant-id-hash": "<sha256-truncated>"},
  "runner": {"class": "windows-latest", "self-hosted": false},
  "started-at": "2026-04-15T02:00:00Z",
  "completed-at": "2026-04-15T02:08:32Z",
  "exit-code": 0,
  "uiao-schema-version": "1.0"
}
```

Note: `tenant-id-hash` rather than raw tenant ID to avoid identifier leakage into public commit history.

### 4.2 `findings.json` schema (normalized UIAO shape)

```json
{
  "uiao-schema-version": "1.0",
  "adapter-id": "scubagear",
  "run-id": "2026-04-15T02-00-00Z-abc123",
  "findings": [
    {
      "id": "scubagear.entra.aad-2.1",
      "severity": "high",
      "control-family": "AC",
      "control-ids": ["AC-2", "AC-6"],
      "iscm-domain": "configuration-management",
      "title": "<rule-title>",
      "description": "<rule-description>",
      "result": "fail",
      "evidence-pointer": "raw/entra-aad-2.1.json",
      "remediation": "<guidance>"
    }
  ],
  "summary": {
    "total": 142,
    "pass": 118,
    "fail": 18,
    "error": 0,
    "n-a": 6
  }
}
```

### 4.3 POA&M row shape

Column set is FedRAMP Template-dependent (Playbook notes "periodically updated"). `tools/conmon_aggregate.py` maps `findings.json` fail-rows to the current FedRAMP POA&M Template columns. **Action item:** Obtain the current FedRAMP POA&M Template version and pin column map (open UNSURE #4 in `ARCHITECTURE.md` §16.9).

---

## 5. Workflow skeletons (draft — not yet implemented)

### 5.1 `conformance-run.yml` (triggered)

```yaml
# .github/workflows/conformance-run.yml
name: Conformance — single run
on:
  workflow_dispatch:
    inputs:
      adapter:
        description: "Adapter ID (from adapter-registry.yaml)"
        required: true
        type: string
      label:
        description: "Optional run label (e.g. 'scr-pre/ABC-123')"
        required: false
        type: string
  repository_dispatch:
    types: [modernization-completed, scr-evidence-requested]

permissions:
  contents: write
  id-token: write

jobs:
  resolve:
    runs-on: ubuntu-latest
    outputs:
      runner-class: ${{ steps.read.outputs.runner-class }}
      runtime: ${{ steps.read.outputs.runtime }}
    steps:
      - uses: actions/checkout@v4
      - id: read
        run: |
          python tools/conmon/resolve_adapter.py \
            --adapter "${{ github.event.inputs.adapter || github.event.client_payload.adapter }}" \
            >> "$GITHUB_OUTPUT"

  run:
    needs: resolve
    runs-on: ${{ needs.resolve.outputs.runner-class }}
    steps:
      - uses: actions/checkout@v4
      - name: Authenticate to tenant (service principal)
        # Windows runners — uses SCUBAGEAR_TENANT_APP_ID / _APP_SECRET
        # Azure Gov self-hosted (Phase 3+) uses managed identity where supported
        run: pwsh tools/conmon/auth.ps1
        env:
          TENANT_APP_ID: ${{ secrets.SCUBAGEAR_TENANT_APP_ID }}
          TENANT_APP_SECRET: ${{ secrets.SCUBAGEAR_TENANT_APP_SECRET }}
      - name: Invoke adapter
        run: pwsh tools/conmon/invoke.ps1 -Adapter ${{ github.event.inputs.adapter }}
      - name: Normalize findings to UIAO schema
        run: python tools/conmon/normalize.py
      - name: Compute SHA-256 integrity manifest
        run: python tools/conmon/hash_evidence.py
      - name: Commit evidence
        run: |
          git config user.name "conmon-bot"
          git config user.email "conmon-bot@users.noreply.github.com"
          git add evidence/conformance/
          git commit -m "[CONMON] evidence: ${{ github.event.inputs.adapter }} ${{ github.event.inputs.label || 'scheduled' }}"
          git push
```

### 5.2 `conmon-scheduled.yml` (monthly)

```yaml
name: Conformance — scheduled fan-out
on:
  schedule:
    - cron: "0 2 1 * *"   # 02:00 UTC on the 1st of each month
  workflow_dispatch: {}

jobs:
  fanout:
    runs-on: ubuntu-latest
    outputs:
      adapters: ${{ steps.list.outputs.adapters }}
    steps:
      - uses: actions/checkout@v4
      - id: list
        run: |
          python tools/conmon/list_active_conformance.py >> "$GITHUB_OUTPUT"

  dispatch:
    needs: fanout
    strategy:
      matrix:
        adapter: ${{ fromJson(needs.fanout.outputs.adapters) }}
    uses: ./.github/workflows/conformance-run.yml
    with:
      adapter: ${{ matrix.adapter }}
      label: scheduled-${{ github.run_id }}
```

### 5.3 `conmon-aggregate.yml` (after any run)

```yaml
name: ConMon — aggregate and POA&M feed
on:
  push:
    paths:
      - 'evidence/conformance/**/findings.json'
  workflow_dispatch: {}

jobs:
  aggregate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python tools/conmon/aggregate.py --month "$(date -u +%Y-%m)"
      - name: Open regression issues
        run: python tools/conmon/regression_issues.py
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - name: Commit dashboard + POA&M
        run: |
          git config user.name "conmon-bot"
          git config user.email "conmon-bot@users.noreply.github.com"
          git add dashboard/conmon-dashboard.json poam/
          git commit -m "[CONMON] aggregate: $(date -u +%Y-%m)" || true
          git push
```

---

## 6. Significant Change Request (SCR) playbook

Per FedRAMP Playbook §5. Change types (Playbook §5):

- **Routine Recurring Changes** — vulnerability management patching. No pre-approval required.
- **Transformative Changes** — major architectural shifts. Require pre-approval and SCR package.
- **Adaptive Changes** — moderate changes needing agency AO review.

### 6.1 SCR evidence pattern (implemented via conformance adapters)

1. **Pre-change snapshot:**
   ```
   gh workflow run conformance-run.yml \
     -f adapter=scubagear \
     -f label=scr-pre/<scr-id>
   ```
2. **Execute change** (outside ConMon scope).
3. **Post-change snapshot:**
   ```
   gh workflow run conformance-run.yml \
     -f adapter=scubagear \
     -f label=scr-post/<scr-id>
   ```
4. **Diff report:**
   ```
   python tools/conmon/diff.py \
     --pre evidence/conformance/scubagear/<scr-pre-run-id>/findings.json \
     --post evidence/conformance/scubagear/<scr-post-run-id>/findings.json \
     --out scr/<scr-id>/diff.md
   ```
5. **Attach diff** to SCR package per agency AO process (open UNSURE #7).

### 6.2 SCR package contents (per Playbook §5)

Typical SCR package includes:

- Change description and business driver.
- Security Impact Analysis (SIA).
- Proposed revised controls/configuration.
- Pre and post evidence (§6.1).
- Timeline.
- Rollback plan.

Template location: `canon/conmon/scr-template.md` (to be created).

---

## 7. POA&M feed

### 7.1 Generation

`conmon-aggregate.yml` runs `tools/conmon/aggregate.py` which:

1. Reads every `evidence/conformance/<adapter>/<run-id>/findings.json` from the current month.
2. Deduplicates findings by `id` (later run supersedes earlier).
3. Enriches each `fail` finding with NVD CVE data (where applicable — per Playbook §3 CVE/CVSS requirement).
4. Writes `poam/poam-<YYYY-MM>.csv` shaped to the current FedRAMP POA&M Template.
5. Writes `dashboard/conmon-dashboard.json` for Quarto site rendering.

### 7.2 Submission

POA&M submission target depends on impact level (Playbook §2):

- **LI-SaaS / Low / Moderate**: FedRAMP secure repository on **USDA Connect.gov**.
- **High**: CSP-owned secure repository.

UIAO is targeting **Moderate** initially, so USDA Connect.gov is the submission endpoint. Submission is a manual step performed by Michael (CSP role) — UIAO tooling produces the file, it does not submit.

### 7.3 Regression tracking

When `aggregate.py` detects new failing findings relative to the prior month, it opens GitHub issues labeled `conmon/regression` with:

- Adapter ID and run ID.
- Finding ID, severity, control-family, ISCM domain.
- Link to evidence directory.
- Recommended remediation (from adapter output).

---

## 8. Runner strategy — detailed

### 8.1 Phase 1 — GitHub-hosted runners

- `windows-latest` for ScubaGear (PowerShell runtime available out of the box).
- `ubuntu-latest` for aggregation, normalization, reporting.
- Authentication to M365 tenant via service principal (client secret in GitHub Actions secrets).

**Risk:** GitHub-hosted runner infrastructure is commercial, not within the federal ATO boundary. Evidence produced here is acceptable for dev/assessment but **not for production evidence of record once ATO is sought** (UNSURE #8 — confirm with agency AO; many accept this for Low/Moderate with documented compensating controls).

### 8.2 Phase 2 — Split strategy

- Move tenant-touching conformance runs to self-hosted Azure Gov Windows runners.
- Keep aggregation, normalization, reporting on GitHub-hosted (no tenant secrets involved).
- Secret-broker pattern: runner fetches secrets from Azure Key Vault via managed identity, not from GitHub Actions secrets.

### 8.3 Phase 3+ — Full Azure Government self-hosted

- All tenant-touching conformance execution on self-hosted runners inside the Azure Gov ATO boundary.
- Self-hosted runner registration token stored in Azure Key Vault.
- Runner VMs hardened to DISA STIG Windows Server baseline.
- Optional: runner scale-set for elastic capacity.

### 8.4 Self-hosted runner design (deferred to §13 Decision 13)

To be decided:

- Azure Government region (Virginia vs Arizona — tracked in `ARCHITECTURE.md` §13 Decision 9).
- VM SKU (Standard_D2s_v3 minimum; actual sizing TBD).
- Scale-set vs standalone.
- Managed identity vs service principal authentication.
- STIG baseline version and hardening automation (Ansible? Azure Policy?).

---

## 9. Reference document monitoring

**Problem:** NIST SP 800-137, FedRAMP ConMon Playbook, and the ScubaGear upstream all evolve. Without active monitoring, the UIAO canon drifts from authoritative sources.

**Current state:** This Cowork session's WebFetch tool is blocked on github.com, fedramp.gov, and nvlpubs.nist.gov (egress proxy). Any monitoring automation run from this session cannot directly fetch upstreams. The user (on a federal/local workstation) can fetch them manually or via a scheduled script.

### 9.1 Recommended monitoring pattern (three-track)

**Track 1 — GitHub Watch subscription (zero-friction, immediate):**
- User subscribes to `cisagov/ScubaGear` releases: Watch → Custom → Releases.
- User subscribes to `cisagov/ScubaGoggles` (SCuBA baseline repo) similarly if applicable.
- GitHub emails on new releases. Zero automation debt.

**Track 2 — Scheduled local fetch job (medium-friction, robust):**
- PowerShell or bash script on a local machine (or Azure Gov VM in Phase 3+).
- Fetches release metadata, PDF URLs, SHA-256 checksums for: cisagov/ScubaGear latest release, FedRAMP ConMon Playbook PDF, NIST SP 800-137 PDF.
- Compares against locally-stored values. Emails / opens issue on change.
- Cadence: weekly or monthly.
- Script location (proposed): `tools/conmon/monitor_references.py` or `tools/conmon/Monitor-References.ps1`.

**Track 3 — Scheduled Cowork task (best-effort):**
- A scheduled task in the Cowork scheduler attempts a WebFetch monthly and reports results.
- Likely to fail due to egress restrictions — but if egress is ever opened, this becomes the fastest signal.
- Low implementation cost; graceful failure mode.

### 9.2 On change detection

When a monitored upstream changes:

1. `canon-steward` subagent (see `ARCHITECTURE.md` agent table) reviews the delta.
2. If canon impact: author a PR updating `ARCHITECTURE.md`, `CONMON.md`, and adapter configurations as needed.
3. Replace the local reference PDF under `compliance/reference/<authority>/` with the new version. Keep old version in a dated subdirectory for audit traceability.
4. Bump change log (`ARCHITECTURE.md` §14).

### 9.3 ScubaGear-specific monitoring concerns

ScubaGear's Rego policy tree is what actually determines findings. Pinning a specific upstream release protects against surprise policy changes, but defeats the point of staying current with CISA guidance.

Recommended posture: track `main` for visibility; pin adapter to a specific release tag (e.g. `v1.x.x`) for production runs; review and bump the pin monthly after new CISA releases. This matches Playbook §5 *Routine Recurring Changes* pattern — the pin bump is a routine recurring change, not an SCR.

---

## 10. Open items specific to CONMON program

Separate from `ARCHITECTURE.md` §13 open decisions. These are operational-program items that don't rise to architectural decision level:

| # | Item | Owner | Blocks |
|---|---|---|---|
| C1 | Obtain current FedRAMP POA&M Template and pin column map | Michael | POA&M feed implementation |
| C2 | Write `canon/conmon/strategy.md` | `canon-steward` | Claimable 800-137 §3.1 implementation |
| C3 | Decide ScubaGear pin policy (track `main` vs pin vN.N.N) | Michael | v1 implementation |
| C4 | Select reference-monitoring track (§9.1) — Track 1 only, Track 1+2, or all three | Michael | Monitoring rollout |
| C5 | Service principal creation in M365 tenant (Graph read scopes) | Michael | ScubaGear adapter run |
| C6 | Decide whether to fork ScubaGear's Rego policies or consume upstream unchanged | Michael | Adapter `policy-source` field |
| C7 | Draft `canon/conmon/scr-template.md` aligned to Playbook §5 | Michael | First SCR submission |
| C8 | Commit reference PDFs to git (Git LFS or regular — 1 MB each so regular is fine) | Michael | Canon integrity |

---

## 11. Change log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-14 | 0.1.0 | Initial draft. Operational companion to `ARCHITECTURE.md` §16. ISCM lifecycle runbook, full Conformance Adapter schema, evidence schema, workflow skeletons, SCR playbook, POA&M feed, runner strategy, reference monitoring pattern, open items C1–C8. Sources verified against local copies of NIST SP 800-137 and FedRAMP ConMon Playbook v1.0 (2025-11-17) | Claude (Cowork) |
