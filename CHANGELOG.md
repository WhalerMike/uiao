# Changelog

All notable changes to UIAO are documented here. Format adapted from [Keep a Changelog](https://keepachangelog.com/); versioning follows [Semantic Versioning](https://semver.org/). Pre-1.0 minor versions may carry breaking changes.

## [Unreleased]

### Removed

- **Root-level clutter from the pre-consolidation era.** The 19 one-shot
  site-migration PowerShell scripts at the repository root
  (`01-fix-link-extensions.ps1` … `16-fix-warn-gaps.ps1`,
  `UIAO-DocAudit*.ps1`) are deleted — they were referenced only by each
  other and by historical provenance comments; git history preserves them.
  `RELEASE_NOTES.md` no longer carries the stale March 2026
  "Modernization Atlas v1.0" content (a pre-ADR-032 product identity
  presented as current on the published release-notes page); it is now a
  pointer to `CHANGELOG.md` and GitHub Releases so it cannot rot again.
  `SECURITY.md` stops referencing the `core/` and `impl/` directories
  retired by the ADR-032 consolidation (now `src/uiao/` and root
  `pyproject.toml`/`uv.lock`).

### Changed

- **AAN engine-neutrality COMPLETE: the ratchet is retired.** The final
  planning-doc dispositions (per the approved table): the ConMon gap
  roadmap, series requirements, deck style notes, and kit-expansion
  roadmap scrubbed in place with derivatives regenerated (docx via the
  pandoc house path, the roadmap deck via in-place notes/body rewrite —
  its speaker-note vendor-source footers also cited dead pre-move inbox
  paths, now fixed); the CR26 reconciliation's generator now displays
  host-repo-relative provenance and the register regenerated; the three
  engine-subject analyses (Vol V academy plan, Vol VII build-vs-buy,
  Book06 critique) moved to `inbox/UIAO-AAN-Integration/` per doctrine;
  the identity-kit requirements docx and a stray feedback docx moved to
  `inbox/`; the browser-duplicate docx deleted. The gate's allowlist is
  now a CLOSED PERMANENT REGISTER of six functional exemptions
  (`BUILD-DERIVATIVES.md` — operators must paste real build commands —
  and five gate scripts that functionally read engine paths); additions
  require a documented functional justification, and a registered file
  that goes clean must still leave.
- **AAN corpus engine-neutrality: ratchet 73 → 24.** The four Vol V
  training books (scrubbed in place as engine-agnostic training, Date
  Codes refreshed), all 39 remaining deck/spec YAMLs (speaker notes,
  vendor-source citations → "host repo"/"reference implementation", build
  headers → `BUILD-DERIVATIVES.md §1`; editorial — no Date Code cascade),
  and the two mainframe figures (`mf-fig-13/14` — diagram text no longer
  names the engine; PNGs regenerated) are engine-neutral. The gate's
  hosting-URL exemption now covers full deep-path URLs into the host
  repository — URL citations are references, prose naming stays
  forbidden. Remaining ratchet: the training subtree (relocation
  pending), 9 planning docs, 5 gate scripts.
- **AAN Vol IV Books 05 and 06 are engine-neutral.** The two heaviest
  engine-naming books (Cybersecurity Training & Awareness; Authorization
  Package & ConMon — 46 mentions between them) now speak evidence-contract
  language: "the governance substrate", "the governance engine's
  conformance adapter", `<engine> oscal …` reference-implementation CLI
  placeholders, and vendor-source citations to "reference implementation
  (host repo)". Their deck specs, both `ced-` figures (which rendered
  "UIAO" inside the diagram — SVGs redrawn, PNGs regenerated), and Date
  Codes moved in the same change; the engine-neutrality ratchet shrank
  79 → 73.
- **SVG-derived PNGs are no longer tracked (repo −66 MB, 865 files).** For
  every figure whose committed `.svg` source sits beside a committed `.png`,
  the PNG and its `.png.json` sidecar are now build artifacts, exactly as
  ADR-093 always declared: `quarto.yml` rasterizes every untracked-PNG
  figure (cairosvg, via `scripts/ci_render_untracked_figures.sh`) before
  each of its seven render jobs — with a same-command canary in
  `derived-binary-gate.yml` so a cairosvg-incompatible SVG fails on its PR,
  not post-merge on main — `link-check.yml` materializes empty
  stand-ins so lychee can resolve local image paths on PRs, and
  `image-gen.yml`'s commit-back now pushes only text outputs (placeholder
  rewrites + registry updates) — its stale Git-LFS wiring is gone (LFS was
  retired per `.gitattributes`). Two gates keep the invariant closed-world:
  the `block-tracked-build-artifacts` pre-commit hook now rejects staging
  any PNG/sidecar whose sibling SVG is tracked, and the new
  `derived-binary-gate.yml` workflow asserts tree-wide that no such pair
  exists. Grandfathered exceptions live in
  `scripts/svg-derived-png-allowlist.txt`: the `federal-aan-series/` tree
  (figure work mid-flight in a parallel program), three canonical figures
  whose `<foreignObject>` SVGs need the Playwright rasterizer, and two
  orgpath-narrative figures that trip a cairosvg parse bug.
  Local authoring: `python scripts/render_svg_images.py` regenerates
  everything on demand.

### Security

- **BREAKING: the on-prem API's bearer auth now fails closed
  (`uiao.api.routes._auth`).** Previously `require_auditor` accepted any
  non-empty bearer token, decoded the JWT payload without verifying the
  signature, expiry, audience, or issuer, and silently defaulted the subject
  to `"auditor"` on parse failure — on live enforcement, CQL, and auditor
  routes. The dependency now verifies inbound Entra ID JWTs (RS256 via the
  issuing tenant's JWKS, plus `exp`/`nbf`/`aud`/`iss`/`tid` claim checks)
  through `uiao.saas.auth.EntraTokenVerifier` by default
  (`UIAO_API_AUTH_MODE=entra`). Deployments must set
  `UIAO_API_AUTH_AUDIENCE` (optionally `UIAO_API_AUTH_TENANTS`,
  `UIAO_API_AUTH_CLOUD`, `UIAO_API_AUTH_REQUIRED_ROLES`); the previous
  accept-anything behavior requires an explicit
  `UIAO_API_AUTH_MODE=insecure-dev` opt-in and must not be used outside
  local development. `uiao.api.routes.auditor` now shares this dependency
  instead of carrying its own unverified copy, and `pyjwt[crypto]` moved
  into the `[api]` extra.

### Fixed

- **All OSCAL emitters now declare one OSCAL version.** Emitters variously
  declared `1.0.4` (SSP/SAR/POA&M/AP/AR generators, dashboard export,
  adapter component-definitions) and `1.1.2` (ServiceNow, CyberArk,
  reciprocity component-definitions) across a single authorization
  package's documents. Every emitter now imports
  `uiao.oscal.version.OSCAL_VERSION`, which is derived from
  compliance-trestle's pin (currently 1.2.1) — the declared version can no
  longer disagree with the models the payloads are validated against.
- **KSI library loaders no longer silently drop rules.**
  `uiao.ir.mapping.ksi_to_ir` and `uiao.evidence.ksi_linker` globbed
  lowercase `ksi-*.yaml` only, dropping the 28 adapter-scoped uppercase
  `KSI-*.yaml` rules (cyberark, hrit-reciprocity, orgtree-readiness,
  servicenow) — the pipeline mapped 163 of 191 rules. Both now load through
  the shared `uiao.ksi.library` helpers, which also read the control list
  under either rule dialect (`controls` / `related_controls`), so the 84
  older-dialect rules stop producing empty NIST mappings in IR Controls.
- **`rules/ksi/index.yaml` is now a derived artifact.** The hand-maintained
  index had drifted in both directions (173 entries vs 191 rule files, four
  category directories missing, phantom entries). It is regenerated from
  the rule files by `scripts/rebuild_ksi_index.py` and gated by a
  regen-and-diff test (`tests/test_ksi_index_sync.py`).
- **KSI claims corrected across README / site / docs.** The advertised
  "163 cryptographically signed" KSIs are actually 191 UIAO-native
  indicator rules (not the official FedRAMP 20x KSI taxonomy) whose
  evaluation artifacts are integrity-protected with HMAC-SHA256 — a
  symmetric MAC, not a digital signature; wording now says so explicitly
  (README, `docs/index.qmd`, glossary, Evidence Fabric appendix,
  RFC-0026 roadmap, quickstart, ScuBA technical spec).

### Added

- **The AAN Evidence & Authorization Contract is published
  (`AAN_Evidence_Contract_Spec.md`).** The open specification every
  engine-neutral reference in the series points at — compliance spine +
  eight evidence slots + cadence/disposition rules in, OSCAL AP/AR/POA&M
  bundle + ConMon stream out, five conformance invariants — authored in
  the series and left untracked by an earlier session; now committed,
  Date-Coded, linked from the series index and the Executive Summary,
  and covered by the engine-neutrality gate (it names no engine, by
  construction). Closes the dangling "per the series evidence contract"
  citation the Phase 0 scrubs introduced.
- **AAN engine-neutrality gate (ratchet).** The Federal AAN series is a
  standalone compliance offering: an agency must be able to adopt it without
  adopting — or hearing about — any particular automation engine, UIAO
  included; where a book needs an engine it speaks in evidence-contract
  terms. `check_engine_neutrality.py` (pre-commit hook
  `aan-engine-neutrality` + a CI step in `aan-authorities-drift.yml`) now
  forbids word-boundary `uiao` in the corpus outside repository-hosting
  URLs, with a 79-file shrink-only ratchet of pre-existing naming (heavy
  books, deck/spec YAMLs, four figures that render the engine name inside
  the diagram, the training subtree pending relocation, planning docs, gate
  tooling) — a cleaned file must leave the list or the gate fails. First
  scrub in the same change: the Vol 0 Executive Summary and Product
  Inventory, Vol I Book 05, Vol VII Book 05, and `_metadata.yml` are now
  engine-neutral, with refreshed Date Codes.

- **ADR-097 — SQL Server transformation placement.** Settles the SQL Server
  Identity Transformation vertical against the Azure SaaS: its governance runs
  in the **same** UIAO control + evidence plane; its host-level execution
  (auth audit, Arc enrollment, login migration) runs **adjacent**, in the
  customer boundary on the Arc-connected host, orchestrated by the control
  plane (lane discipline, ADR-092). Registers `sql-server` in
  `modernization-registry.yaml` with `runner-class: on-prem-self-hosted`,
  adds a house-style placement figure, and documents it in the Azure SaaS
  operator guide (§13).

## [0.7.1] — 2026-07-14

### Fixed

- **Control-library status vocabulary — 31 controls silently outside every
  bucket.** 31 controls (whole `ca` / `ma` / `mp` / `pl` / `ps` / `ra` families)
  carried `status: Implemented` instead of `implemented`. Every consumer matches
  this token exactly and case-sensitively — `generators/ssp.py` passes it
  straight through into the OSCAL `implementation-status` prop (FedRAMP ns), so
  the capitalized variant emitted an **invalid OSCAL token** and matched neither
  the implemented nor the not-implemented bucket. Normalized to lower-case:
  controls loading as `implemented` go 99 → 130, off-vocabulary 31 → 0 (247
  total unchanged).

### Added

- **Status-vocabulary guard in `scripts/check_control_library.py`.** The checker
  validated field-set drift but never the `status` value. It now rejects any
  token outside the OSCAL implementation-status vocabulary
  (`implemented` / `partial` / `not-implemented` / `not-applicable`), reporting
  drift per file and failing `--strict`, so the case split cannot silently
  return. Covered by `tests/test_check_control_library.py`.

### Changed

- **`generators/narrative_loader.py` normalizes `status` defensively** with
  `.lower()`, so a stray case variant reaching the loader cannot skew generated
  output ahead of the blocking checker.

## [0.7.0] — 2026-06-07

**Theme: Multi-tenant Azure SaaS (ADR-096).** Adds a multi-tenant SaaS
deployment surface for UIAO on Azure Container Apps, parallel to (not
replacing) the single-tenant Windows/IIS surface. One operated service can
govern many customer Entra tenants, acquiring per-tenant Microsoft Graph /
ARM tokens via a managed identity.

### Added

- **Concrete per-tenant stamp executor** (`uiao.saas.azure_stamp`
  `AzureStampExecutor` + `uiao.saas.azure_provisioners`) — provisions a
  tenant's Postgres schema, Blob container, and Key Vault secret scope (named
  after the strictly-validated `data_namespace`). Orchestration is
  dependency-free and fake-tested; the Azure-backed provisioners lazy-import
  the `[saas]` SDKs. Wired into `attach_saas()`; executes only when
  `UIAO_SAAS_STAMP_EXECUTION_ENABLED` is set (dry-run otherwise).
- **`uiao.saas` package** — the multi-tenant layer that composes onto the
  existing `uiao.api` data plane via `attach_saas()`:
  - `tenant` — the `Tenant` aggregate + lifecycle state machine
    (`pending → active → suspended → deprovisioned`) with validated
    transitions and a deterministic per-tenant `data_namespace`
  - `repository` / `pg_repository` — async tenant registry, in-memory
    (dependency-free) plus a Postgres-backed implementation (behind `[saas]`)
  - `auth` — inbound Entra JWT verification; claim validation is pure-stdlib,
    RS256/JWKS signature verification is lazy-imported behind `[saas]`
  - `middleware` — `TenantResolutionMiddleware` binding a per-request
    `TenantContext` (`context`)
  - `control_plane` / `provisioning` — control-plane REST API (onboard /
    list / suspend / resume / deprovision) with a dry-run-by-default
    `StampExecutor`
  - `asgi` — container entrypoint `uiao.saas.asgi:app`
- **`[saas]` optional-dependency extra** (SQLAlchemy async + asyncpg, PyJWT,
  azure-identity / azure-keyvault-secrets / azure-storage-blob). Isolated so
  the blocking CI test job (`.[api]` only) stays green.
- **`deploy/azure/`** — container image (`Dockerfile`, `.dockerignore`) and
  Bicep IaC for Azure Container Apps (managed identity, ACR, Key Vault,
  PostgreSQL Flexible Server, Storage, Log Analytics) + operator `README.md`.
- **`.github/workflows/azure-saas-deploy.yml`** — manual-dispatch-only
  (dormant) build + deploy workflow using OIDC.
- **ADR-096** documenting the Azure SaaS architecture decision.
- **Docs** — `docs/customer-documents/platform/azure-saas.qmd` operator
  guide and a SaaS control-plane section in the CLI Reference (§5.1).
- 31 new tests (`tests/test_saas_*.py`) covering the tenant model,
  repository, inbound auth, middleware, and control-plane lifecycle.

### Notes

- The SaaS surface is additive — the single-tenant Windows/IIS deployment is
  unchanged. The deploy workflow does not run on merge; nothing deploys until
  an operator triggers it.

## [0.6.1] — 2026-05-15

**Theme: ServiceNow tier-1 adapter completion.** Closes the tier-1
conformance gap identified in #458 (child of #447 Microsoft Tier-1
umbrella). Same parallel-batch shape as v0.6.0 HRIT productization.

### Added

- **WS-A1** write-side methods on `ServiceNowAdapter`: `create_incident`,
  `update_incident`, `create_change_request`, `create_problem`, plus
  `_emit_ticket_manifest` and `_build_evidence` helpers
- **WS-A1** `ServiceNowCollector.post_record` and `patch_record` with
  bearer auth, JSON headers, `raise_for_status`, empty-scaffold fallback
- **WS-A2** `src/uiao/oscal/servicenow_evidence.py` —
  `emit_servicenow_component_definition` producing OSCAL 1.1.2
  component-definition with HMAC-SHA256 signing, IR-4/IR-5/IR-6/CM-3
  control mapping (51 tests, golden-file regression pinned)
- **WS-A3** KSI-SNOW-001 through KSI-SNOW-005 in
  `src/uiao/rules/ksi/servicenow/` (cadence, ATO mapping, closure
  evidence, change-request approval chain, SLA-violation findings);
  mapping registry grows from 181 to 186 entries
- **WS-A4** 6 tier-2 contract fixtures under
  `tests/fixtures/tier-2/servicenow/` (incident-create, incident-update,
  change-request-create, problem-create, query-result-empty,
  query-result-3-records)
- **WS-A5** real `detect_drift()` implementation backed by registry-
  expected scope and `collector.compare_for_drift`
- **WS-A5** `tests/test_servicenow_adapter.py` (34 tests) and
  `tests/conformance/test_servicenow_conformance.py` (6 tests)

### Changed

- `servicenow_adapter.py` line count grew 263 → 441 reflecting the new
  modernization (write) surface
- KSI control mapping registry: append-only growth, no existing entries
  modified

### CI

- `ruff check`: clean
- `ruff format --check`: 394 files clean
- `pytest`: 3495 passed, 0 failed, 163 skipped, 8 xfailed (~72 s)

### Out of scope (queued)

- Real ServiceNow tenant validation (#458 follow-up, lab-tenant access)
- #459 v0.6.2 Palo Alto NGFW adapter completion
- #460 v0.6.3 CyberArk PAM adapter completion

## [0.6.3] — 2026-05-18

**Theme: CyberArk PAM tier-1 conformance completion.** Closes CyberArk scope
under #460 (child of #447).

### Added

- CyberArk tier-2 fixtures under `tests/fixtures/tier-2/cyberark/`:
  `account-create.json`, `account-rotate-success.json`,
  `account-rotate-failure.json`, `account-verify.json`,
  `activity-audit.json`
- `src/uiao/oscal/cyberark_evidence.py` OSCAL component-definition emitter
  for IA-5, IA-5(1), AC-2, AC-6 with rotation-cause and verification props
- KSI-CARK-001 through KSI-CARK-005 under `src/uiao/rules/ksi/cyberark/`
  plus mapping entries in `uiao-control-to-ksi-mapping.yaml`
- `tests/conformance/test_cyberark_conformance.py` synthetic-vault conformance
  pack (mocked vault flow + KSI verdict assertions)
- `tests/test_cyberark_oscal_emitter.py` + golden regression fixture
  (`tests/fixtures/oscal/cyberark-component-definition-golden.json`)

### Changed

- `src/uiao/adapters/cyberark_adapter.py` now uses CyberArk PAS Web Services
  API paths for account create, change, verify, and activities retrieval with
  vault-scoped headers and token authentication
- Tier-1 integration guidance now explicitly documents the on-prem-self-hosted
  runner prerequisite for vault-reachable CyberArk validation



## [0.6.0] — 2026-05-11

**Theme: HRIT Single-ATO Productization.** Closes the runtime gap deferred by
ADR-054 §Implementation: the Single-ATO Reciprocity Model now emits signed,
OSCAL-mapped, evidence-graph-anchored reciprocity records per consuming agency,
with ConMon SLA enforcement and configuration-latitude drift detection. A
maintainer operating a single-ATO platform (OPM Solicitation 24322626R0007
anchor) can onboard a consuming agency, receive a signed `reciprocity-record.json`
plus a scoped OSCAL component-definition, and walk the 15-minute quickstart
against the synthetic three-agency (OPM + Treasury + IRS) fixture.

### Added

#### Canon

- **ADR-058** (`src/uiao/canon/adr/adr-058-hrit-productization-mission.md`) —
  HRIT Single-ATO Productization as v0.6.0 Mission Theme. Status: Accepted.
  Ratifies the runtime emission contract, ConMon SLA cadences (30-day draft SSP,
  45-day final SSP, 30-day reauthorization window), and the KSI-RECIP-001..008
  accountability signals.
- **UIAO_144** (`src/uiao/canon/specs/hrit-productization.md`) — HRIT
  Productization Operational Spec. Expands ADR-058 into the full operational
  narrative: reciprocity record lifecycle, per-agency bundle aggregation,
  configuration-latitude drift detection, and KSI mapping table.
- **UIAO_113 v1.2** (amendment to `src/uiao/canon/specs/graph-schema.md`) —
  Evidence Graph schema bumped to v1.2. New node types: `ato-decision`,
  `reciprocity-record`. New edge types: `ato-decision → reciprocity-record`,
  `reciprocity-record → consuming-agency`.
- **`reciprocity-record.schema.json`**
  (`src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json`) —
  JSON Schema 2020-12. Required fields: `controlling_ato_id`,
  `consuming_agency_code`, `reciprocity_basis`, `legal_basis` (enum),
  `effective_at`, `expires_at`, `configuration_latitude_ref`, `signature`
  (HMAC-SHA256: `algorithm`, `value`, `signed_at`, `signer`), `provenance`.
- **KSI-RECIP-001..008** (`src/uiao/rules/ksi/KSI-RECIP-*.yaml`) — Eight new
  Key Security Indicators covering legal-basis citation, controlling-ATO
  existence, expiry enforcement, configuration-latitude remediation ownership,
  SSP cadence (30-day draft, 45-day final), reauthorization SLA, per-agency
  bundle signature verification, and evidence-graph edge completeness. Mapping
  registry appended in `src/uiao/rules/ksi/uiao-control-to-ksi-mapping.yaml`.
- **`22_HRITProductization.qmd`** (`docs/docs/22_HRITProductization.qmd`) —
  Operational narrative for the HRIT productization theme. Two Mermaid diagrams:
  reciprocity-record lifecycle and per-agency bundle aggregation flow.

#### Runtime — six new modules

- **`src/uiao/oscal/reciprocity_record.py`** — `emit_reciprocity_record()`:
  produces a schema-valid, HMAC-SHA256-signed reciprocity record with OSCAL
  component-definition projection scoped to the consuming agency. Provenance
  block cites UIAO_140 + ADR-054.
- **`src/uiao/oscal/reciprocity_bundle.py`** —
  `aggregate_per_agency_bundle()`: bundles reciprocity-record + scoped
  component-definition + scoped assessment-results + provenance manifest into
  a directory independently verifiable by the consuming agency AO.
- **`src/uiao/monitoring/ato_cadence.py`** — Enforces 30-day draft SSP,
  45-day final SSP, and 30-day reauthorization-window SLAs. Emits `PASS |
  WARN | FAIL` with named SLA breaches and optional JSON output for downstream
  tooling.
- **`src/uiao/governance/config_latitude.py`** — Diffs observed tenant
  configuration against the SSP's enumerated configuration-latitude table;
  emits `DRIFT-SCHEMA` (P2 default) for each out-of-bounds parameter.
- **`src/uiao/canon/queries/configuration-latitude-violations.yaml`** — CQL
  query filtering drift findings to the configuration-latitude class.
- **`src/uiao/evidence/graph.py`** (if new) — Runtime traversal support for
  UIAO_113 v1.2 node and edge types added in this release.

#### CLI

- **`uiao reciprocity` sub-app** (`src/uiao/cli/reciprocity.py`, registered in
  `cli/app.py`): three commands:
  - `uiao reciprocity onboard-agency` — emit a signed reciprocity record for
    a consuming agency.
  - `uiao reciprocity list-records` — enumerate registered reciprocity records.
  - `uiao reciprocity verify` — verify a record's HMAC-SHA256 signature.
  All commands carry a runnable `Example::` block in `--help`.
- **`uiao conmon ato-cadence-check`** (new command in `cli/conmon.py`) —
  ConMon SLA cadence validator; wraps `src/uiao/monitoring/ato_cadence.py`.

#### Fixtures + quickstart

- **`examples/hrit/opm-treas-irs/`** — Synthetic three-agency fixture: OPM as
  controlling ATO, Treasury and IRS as consuming agencies. Includes one
  intentional configuration-latitude violation for drift-detector demonstration.
  Known-answer table per agency included.
- **`docs/docs/hrit-productization-quickstart.md`** — 10-step quickstart from
  `git clone` to three signed reciprocity records. Runs in <15 minutes on the
  synthetic fixture; no live Azure tenant or API keys required.

#### Tests

- **`tests/test_hrit_productization_smoke.py`** — End-to-end smoke against the
  WS-A8 three-agency fixture. Covers happy-path, lapsed-ATO (record past
  `expires_at` flagged), and configuration-latitude drift. Schema-validation
  assertions on every emitted record. Target: <60 seconds.
- **`tests/test_reciprocity_*.py`** — Unit tests for emitter (golden-file
  regression + signature verification), bundle aggregator (round-trip
  emit → re-validate from disk), and ConMon SLA cadence (four threshold
  cases: 28 d / 32 d / 46 d / 100 d with deterministic verdicts).
- **`tests/test_cli_help_smoke.py`** — Extended to cover `uiao reciprocity`
  sub-app (three new commands) and `uiao conmon ato-cadence-check`.
- **`tests/test_quickstart_smoke.py`** — Extended to cover the HRIT quickstart.

### Local verification (pre-0.6.0 cut)

```
$ python -m ruff check .
All checks passed!

$ python -m ruff format --check .
<N> files already formatted

$ python -m mypy src/uiao
Success: no issues found in <N> source files

$ python -m pytest -q
<N> passed, 156 skipped

$ uiao substrate drift
PASS — 0 P1 findings

$ python3 -c "
import re, pathlib
idx = pathlib.Path('src/uiao/canon/adr/index.md').read_text()
for m in re.finditer(r'\(adr-([0-9]+)[^)]*\.md\)', idx):
    p = pathlib.Path('src/uiao/canon/adr') / m.group(0)[1:-1]
    assert p.exists(), f'Missing: {p}'
print('OK — all ADR refs resolve')
"
OK — all ADR refs resolve
```

### Public-surface coverage

| Feature | v0.5.0 | v0.6.0 |
|---|---|---|
| Auditor API | ✅ | ✅ |
| CQL Engine | ✅ | ✅ |
| Evidence Graph (UIAO_113) | ✅ v1.1 | ✅ v1.2 (`ato-decision`, `reciprocity-record`) |
| Terraform adapter | ✅ | ✅ |
| Compliance Orchestrator | ✅ | ✅ |
| Enforcement Runtime | ✅ `uiao enforcement run` | ✅ |
| **Reciprocity record emission** | ❌ doctrine only | ✅ `uiao reciprocity onboard-agency` |
| **Per-agency OSCAL bundle** | ❌ | ✅ `aggregate_per_agency_bundle()` |
| **ConMon SLA cadence enforcement** | ❌ | ✅ `uiao conmon ato-cadence-check` |
| **Configuration-latitude drift detection** | ❌ | ✅ `DRIFT-SCHEMA` via `config_latitude.py` |
| **KSI-RECIP-001..008** | ❌ | ✅ 8 new accountability signals |

---

## [Unreleased]

**Theme: GCC-Moderate boundary integration — completion.** Lands the
remaining canonical, customer-doc, and adapter-data artifacts derived
from the four `inbox/New_FedRAMP_Boundary/` source documents (M365
GCC-Moderate Telemetry & Boundary Assessment, ThousandEyes Workaround
Analysis, FedRAMP 20x Assessment & Implications, LinkedIn Post Draft).
Companion to the Phase 1.4 / Phase 4 / Phase 5 cherry-picks already
landed via PRs #307 and #308 (the seven KQL queries, `sentinel_probe.py`
+ scorecard + 16 tests, and FINDING-002..009).

### Added

- **`src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml`** —
  machine-readable telemetry-gap matrix, 26 rows across four
  disposition classes (`confirmed` / `inferred` / `restricted` /
  `retention-limited`). Backs the cherry-picked findings and the
  scorecard in `sentinel_probe.py`.
- **`src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/`**
  — five-file canon reference: README, methodology
  (boundary-inference framework over SI-4 / AU-2 / AU-3 / SC-7),
  capabilities (per-feature dispositions), MITRE Chains A & B,
  resolved-positions on previously disputed questions.
- **`docs/customer-documents/compliance/boundary-authorization/B1-gcc-moderate-boundary-model.qmd`**
  — fills the B.1 leaf of the boundary-authorization scaffold with
  the ZTMM ceiling table, BOD 25-01 / M-22-09 / M-21-31 / NIST 800-207
  posture, and MAS 2026 forward path.
- **ADR-057** (`src/uiao/canon/adr/adr-057-thousandeyes-networks-pillar-scope.md`)
  — PROPOSED. Endorses ThousandEyes only as a Networks-pillar
  component of a broader compensating-architecture stack with four
  preconditions. (Originally drafted as ADR-047 on the integration
  branch; renumbered after main's two unrelated ADR-047 files
  landed.)
- **`docs/narrative/2026-04-fedramp-gcc-moderate-three-assessments.md`**
  — public-surface synthesis with a reference map across all
  artifacts.
- **`inbox/New_FedRAMP_Boundary/`** — original `.docx` source
  documents + `IMAGE-PROMPTS-fedramp-moderate.md` + image-pipeline
  Python scripts. Immutable provenance for every derived artifact in
  this section.

### Changed

- **`src/uiao/canon/data/fedramp-20x.yml`** — extended with four new
  top-level blocks: `minimum_assessment_scope` (five MAS-CSO inclusion
  tests), `ksi_families` (all eleven KSI families — was 7 in the
  UIAO-specific `core_mappings`), `deployment_surfaces` (Phase 2 Pilot
  Required; Rev5 Balance Improvement Releases Optional; Phase 1 Pilot
  Archived), and `gap_matrix_scope_effect` (per-signal-class
  projection of MAS-CSO against the GCC-Moderate gap matrix).
- **`docs/docs/04_FedRAMP20x_Phase2_Summary.qmd`** — appended §12
  covering MAS-CSO, the eleven KSI families, the three deployment
  surfaces, and three caveats on assessor interpretation drift.
- **`docs/docs/03_FedRAMP20x_Crosswalk.qmd`** — appended §12 with the
  MAS-CSO scope-effect-by-signal-class crosswalk; ~30–40% of the gap
  matrix has a credible descope path under MAS-CSO-MDI.
- **ADR-043** — PROPOSED → ACCEPTED on Rev5 Balance Improvement
  Release publication for Vulnerability Detection and Response and
  Collaborative Continuous Monitoring (the modernized pathways for
  RV5-CA07-VLN and RV5-CA07-CCM).
- **`docs/findings/fedramp-gcc-moderate-informed-network-routing.md`
  (FINDING-001)** — added `related_ksi: ["KSI-SC-07", "KSI-SI-04"]` to
  bring it to parity with the cherry-picked findings, which already
  carry the cross-reference.
- **`docs/findings/fedramp-gcc-moderate-thousandeyes-coverage-scope.md`
  (FINDING-002 ThousandEyes)** — repointed all four ADR references
  from `ADR-047` to `ADR-057`. The cherry-pick from PR #307 captured
  the original branch's ADR-047 reference, but main's ADR-047 slot is
  now occupied by two unrelated ADRs.

## [0.4.1] — 2026-05-01

**Theme: Identity transformation canon + FedRAMP 20x integration + hygiene burn-down.** Establishes the canonical inventory of identity/directory transformations, the Priority 1 deliverable plans, foundational ADRs, the ADR governance protocol, the first batch of Phase 1 PowerShell discovery scripts that feed every downstream Spec 1/2/3 deliverable, the FedRAMP 20x KSI integration spec (UIAO_133 + ADR-047), and a comprehensive cleanup of post-consolidation drift in CONTRIBUTING.md, root layout, AGENTS.md module topology, and pyproject.toml dependency hygiene.

### Added

#### Canon — Identity transformation framework

- **UIAO_135** (`src/uiao/canon/UIAO_135_identity-directory-transformation-inventory.md`) — Identity & Directory Transformation Inventory. 17 transformations (X.500 → flat attribute model, identity-object, policy, governance), coverage assessment, 8-spec roadmap across three priorities.
- **UIAO_136** (`src/uiao/canon/UIAO_136_priority1-transformation-project-plans.md`) — Priority 1 Transformation Specs project plans. 107 deliverables across 5 phases: Computer Object Transformation (Spec 1, 30), HR-Agnostic Provisioning Architecture (Spec 2, 33), Service Account → Workload Identity Mapping (Spec 3, 38), 6 cross-cutting deliverables.
- **UIAO_133** (`src/uiao/canon/adr/adr-index.md`) — Architectural Decision Records Index.
- **UIAO_134** (`src/uiao/canon/adr/adr-review-protocol.md`) — ADR Review Protocol; event/cadence/signal-based review mechanisms, freshness-check automation scaffolding.
- **ADR-001** — HAADJ Deprecated; Entra ID Join as sole device join target.
- **ADR-002** — Arc-enabled servers require non-domain-joined state.
- **ADR-003** — API-driven inbound provisioning as HR-agnostic canonical path.
- **ADR-004** — Workload Identity Federation as default for external integrations.
- **ADR-048** — OrgPath attribute selection (#262).

#### Discovery scripts (UIAO_136 Phase 1)

Twenty-four PowerShell scripts under `tools/discovery/`:

- **Spec 1 (Computer Objects):** D1.1 AD computer inventory, D1.2 device classification matrix, D1.3 GPO-to-device dependency map, D1.4 authentication protocol audit, D1.5 Kerberos SPN inventory, D1.6 BitLocker/LAPS state assessment.
- **Spec 2 (HR-driven Provisioning):** D1.1 HR attribute schema, D1.2 OrgPath translation rules, D1.3 attribute mapping matrix (HR → Entra ID), D1.4 HR→AD attribute mapping matrix, D1.5 UPN generation rules engine, D1.6 Worker Type taxonomy, D1.7 HR connector comparison matrix.
- **Spec 3 (Service Accounts):** D1.3 Windows service credential audit, D1.4 IIS app pool identity audit, D1.5 COM+/DCOM application identity audit, D1.6 Kerberos delegation chain map, D1.7 SPN collision report, D1.8 SQL Server auth audit, D1.9 LDAP bind account inventory, D1.10 cert-based auth audit, D1.11 network service account audit, D1.12 service account owner matrix.

Spec1-D1.7..D1.9, Spec2-D1.8, and Spec3-D1.1 remain pending (corrupted during the originating CoPilot Tasks session, tracked for regeneration).

### Changed

- **UIAO_135 §3 and §4** corrected to acknowledge ADR coverage for previously-flagged gaps; §3.2 reduced to three items still genuinely lacking a transformation spec (AD security group rationalization, Kerberos/NTLM elimination, LDAP-dependent app migration) (#266).
- **ADR-001..004 cross-references** standardized from provisional `UIAO_IDT_001/002` to canonical `UIAO_135/UIAO_136` per `document-registry.yaml` convention; UIAO_135 §5 refinement note marked resolved.
- **`document-registry.yaml`** registers UIAO_133, UIAO_134, UIAO_135, UIAO_136 (previously stamped on docs but missing from the registry).
- **ADR-025** renumbered to ADR-047 to resolve the slot collision created when the four identity-transformation ADRs occupied the empty 001-004 slots.

#### Canon — FedRAMP 20x integration

- **UIAO_133** (`src/uiao/canon/specs/fedramp-20x-integration.md`) — FedRAMP 20x Integration spec. KSI emission tagging contract, MAS classification rubric, KSI-staleness drift class, dual-pathway posture (#278).
- **ADR-047** (`src/uiao/canon/adr/adr-047-fedramp-20x-integration.md`) — substrate-level decision committing UIAO to KSI emission tagging, MAS classification, and KSI-staleness drift class. Status: PROPOSED. Ratification gate: RFC-0010 publication + stable Moderate KSI catalog + clean dry-run + steward signoff (#278).
- **FINDING-002** (`docs/findings/fedramp-20x-moderate-pilot.md`) — governance finding documenting the FedRAMP 20x Moderate Pilot framework movement and external assessment, with internal remedy across Phase 0/2/3 (#278).

#### Canon — Microsoft coverage doctrine + ingestion contract

- **UIAO_009** (`src/uiao/canon/UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md`) — Microsoft Coverage And Gap Doctrine (#273).
- **UIAO_007** (`src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md`) — ingestion contract refresh (#273).
- **D3.1** (`src/uiao/canon/specs/Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md`) — API-Driven Inbound Provisioning Architecture, Spec 2 Phase 3 (#272). Verification pass against Microsoft Learn (#274) and v0.2 → v1.0 closure verification (#276).
- **D1.7** — verification pass against Microsoft Learn (#274) and v0.2 → v1.0 closure verification (#276).
- **ADR-049** — accepted (#271, #270); +9 reserved adapter slots appended to `adapter-registry.yaml`.
- **ADR-050** — D3.1 reference middleware implementation choices, accepted (#277, #275).

#### Phase 2 architecture artifacts

- **Per-domain Phase 2 diagram pack** — generator + index under `phase2/` driven by source model at `canon/phase2/UIAO_Phase2_TSA.psd1` via `tools/Write-Phase2TSA.ps1` (#268).

### Changed — Documentation & topology

- **CONTRIBUTING.md** — full rewrite. Old text described the pre-consolidation three-repo layout (`core/` / `impl/` / `docs/`), `pip install -e ./impl`, and the abandoned `[UIAO-CORE]` commit prefix — none of which had matched reality since ADR-028 + ADR-032. New text uses AGENTS.md as source-of-truth: post-ADR-032 `src/uiao/` topology, `pip install -e ".[dev]"`, the actual `<verb>: <module-or-area> — <description>` convention, and the six named invariants (I1–I6) verbatim from AGENTS.md (#282).
- **CODE_OF_CONDUCT.md** — Contributor Covenant 2.1, fetched from EthicalSource canonical source. Closes the GitHub community-profile gap (#282).
- **AGENTS.md module topology table** — added `tools/`, `diagrams/`, `phase2/`, `canon/` (root), and `deploy/` rows (previously undocumented despite holding real working content). Includes disambiguation that root `canon/` is **not** the canon authority — that lives at `src/uiao/canon/` per invariant I4 (#284).
- **`phase2/README.md`** (new) — documents the Phase 2 generator pipeline (`canon/phase2/*.psd1` → `tools/Write-Phase2TSA.ps1` → `phase2/*.md`) and the `UIAO_P2_NNN` namespace distinct from canonical `UIAO_NNN` (#284).
- **`canon/README.md`** (new) — disambiguation notice ("NOT canon authority"); rename to `models/` planned for follow-up (#284).
- **CONTRIBUTING.md / CODE_OF_CONDUCT.md / AGENTS.md additions** substantively unblock issue #183 (external-contributor onramp).

### Changed — Identity transformation canon

- **UIAO_135 §3 and §4** corrected to acknowledge ADR coverage for previously-flagged gaps; §3.2 reduced to three items still genuinely lacking a transformation spec (AD security group rationalization, Kerberos/NTLM elimination, LDAP-dependent app migration) (#266).
- **ADR-001..004 cross-references** standardized from provisional `UIAO_IDT_001/002` to canonical `UIAO_135/UIAO_136` per `document-registry.yaml` convention; UIAO_135 §5 refinement note marked resolved.
- **`document-registry.yaml`** registers UIAO_133, UIAO_134, UIAO_135, UIAO_136 (previously stamped on docs but missing from the registry).
- **ADR-025** renumbered to ADR-047 to resolve the slot collision created when the four identity-transformation ADRs occupied the empty 001-004 slots.

### Changed — pyproject.toml hygiene

- **`compliance-trestle-fedramp`** pinned to `>=0.2` (was unpinned — any breaking release would have landed silently) (#285).
- **`[dependency-groups]` block removed** — was PEP 735 syntax for `uv sync --group dev`, but no workflow or Makefile invokes uv that way (CI uses `pip install -e ".[dev|api]"`). Eliminates phantom "which floor wins?" question that never actually applied (#285).
- **`[tool.ruff] exclude = ["inbox"]` restored** — Copilot commit `7f0072bc` claimed this fix in its message but the change was lost during the squash-merge of PR #277. Restoring it unblocks any local commit that triggers the ruff hook (#285).
- **`.pre-commit-config.yaml`** ruff pin bumped `v0.6.9 → v0.9.0` to recognize `UP045` in the codebase's ignore list (was failing every Python-touching local commit) (#286).

### Changed — root + docs/ cleanup

- **Removed dead root files**: `release-drafter.yml` (root copy was a duplicate workflow file that never executed — workflows only run from `.github/workflows/`), `README2.md` (stale draft), `dirtree.txt` (218 KB generated output), and 11 page-screenshot PNGs from `docs/` (~984 KB) (#283).
- **Relocated misplaced PowerShell scripts**: `Test-UiaoCli.ps1` → `scripts/`, `docs/Split-UIAODocs.ps1` → `scripts/`. Per AGENTS.md, `docs/` is `.qmd`/`.md`/`.yml` only; `scripts/` holds workspace tooling (#283).
- **Relocated `docs/generate_images.py` → `scripts/generate_images.py`** (1182 lines) with workflow path updates in lockstep across `.github/workflows/image-gen.yml` (7 sites), `tests/test_image_pipeline.py` (3 sites), `docs/academy/{image-pipeline,document-generation}-guide.qmd` (9 sites), `.gitignore`, and `.gitattributes` (#286).

### Fixed

- **Link Check** unblocked on main — repointed two stale `github.com/.../blob/main/...` URLs in `docs/findings/fedramp-20x-moderate-pilot.md` to existing Phase 2/3 Quarto chapters (the canon spec stubs they referenced were never written) (#281).

### Tooling

- `.gitignore` excludes `dev/null/` — Windows-shell mishap when `git lfs install` is invoked with `/dev/null` as a path argument creates the directory in-tree instead of redirecting.

### Repo metadata

- GitHub repo description, homepage URL, and topics (`fedramp`, `oscal`, `compliance`, `cybersecurity`, `drift-detection`, `governance`, `nist`, `python`, `scuba`, `zero-trust`) configured. Closes the metadata gap flagged in this morning's repo assessment.

### Issues & tracking

- Filed [#279](https://github.com/WhalerMike/uiao/issues/279) — mypy override burn-down; 12 modules, 13 suppressed error codes, 5-phase plan.

---

## [0.5.0] — 2026-04-25

**Theme: adoption readiness — onramp + public-surface coverage.** Phase 1 (tracked in issue #183) closes the gap between *what's implemented* in `src/uiao/` and *what an external user can reach*. After 0.5.0 every ghost-`v1.0.0` feature promise is reachable through the documented public surface, every CLI command has a runnable example in `--help`, and a stranger goes from `git clone` to a full FedRAMP auditor bundle in 10 minutes.

### Added

- **`docs/docs/quickstart.md`** — 10-minute walkthrough from clone to auditor bundle (evidence, POA&M, SSP narrative) using a shipped synthetic SCuBA fixture. CI smoke test (`tests/test_quickstart_smoke.py`, 4 tests) prevents the doc from rotting (#197).
- **`examples/quickstart/scuba-normalized.json`** — adopter-friendly copy of the synthetic M365 SCuBA fixture (5 KSI results: 2 PASS / 1 WARN / 2 FAIL / 1 unmapped) (#197).
- **`docs/docs/adapter-authoring-tutorial.md`** — 30-minute walkthrough from zero to a merged adapter PR using the shipped ScubaGear adapter as the worked example. 7 numbered sections + 4 checkpoints + troubleshooting (#199).
- **`uiao enforcement` sub-app** — UIAO_111 Enforcement Runtime is now CLI-reachable. Two commands: `list-policies` enumerates the built-in demo set, `run` evaluates a policy against a list of IR objects with state-count summary + optional JSON output. 5 behavioral tests in `tests/test_cli_enforcement.py` (#211).
- **Quickstart "Want a REST API?" section** — names the `[api]` install extra, the uvicorn launch command, and the 5-route-module surface (auditor, boundary, health, orgpath, survey, 17 endpoints total). Quickstart now documents both public shapes (#213).
- **Evidence-vs-IR division-of-responsibility note** in `src/uiao/rules/canon-consumer.md` — frames `evidence` as the canonical bundle/graph surface and `ir` as the pipeline-stage surface; provides a decision rule for new commands (#214).
- **`docs/reports/cli-surface-audit-v0.4.0.md`** — M1 audit identifying 36 flat top-level commands, 92% missing examples, 6 already-modularized sub-apps as the target pattern (`1896d890`).
- **`docs/reports/public-surface-audit-v0.5.0.md`** — M5 audit scoring the v0.5.0 surface against the ghost-`v1.0.0` feature list. Final score after this release: 6/6 reachable (#204).
- **ADR-046** (`src/uiao/canon/adr/adr-046-cli-surface-convention.md`) — ratifies the sub-app-per-domain CLI convention; documents the 33-row rename table for the v0.5.0 hard-break and bans new flat top-level commands (`AGENTS.md` invariant I6 added) (#195).

### Changed

- **CLI surface reorganized into 11 sub-apps** per ADR-046. `cli/app.py` shrinks from 1,375 → 73 lines (sub-app registration only). 36 flat top-level commands carved into 5 new sub-app modules (`cli/{adapter,canon,conmon,generate,ir}.py`); `validate` and `validate-ssp` move under existing `oscal` sub-app (#195).
  - **Breaking:** every pre-0.5.0 command name moves under a sub-app. Mapping table in ADR-046. No deprecation shims (zero known external users at v0.4.0; cheapest moment to break names).
- **44/44 leaf commands now carry a runnable `Example::` block in `--help`** — was 4/44 pre-release (#198).
- **Quarto site renders the new onboarding docs** and surfaces them through a `Getting started` navbar menu. Render pattern extended to include the two onboarding `.md` files (#201).

### CLI rename map (v0.4.x → v0.5.0)

Full mapping in ADR-046. Highlights:

- `uiao generate-{ssp,docs,docx,pptx,sbom,…}` → `uiao generate {ssp,docs,…}` (11 commands)
- `uiao ir-{scuba-transform,evidence-bundle,…}` → `uiao ir {scuba-transform,…}` (14 commands)
- `uiao conmon-{process,export-oa,dashboard}` → `uiao conmon {process,…}` (3 commands)
- `uiao adapter-run` / `adapter-run-scuba` → `uiao adapter run` / `run-scuba` (2 commands)
- `uiao canon-check` → `uiao canon check`
- `uiao validate` / `validate-ssp` → `uiao oscal validate` / `validate-ssp`

### Public-surface coverage

Score against the pre-OSS ghost-`v1.0.0` feature list:

| Feature | v0.4.0 | v0.5.0 |
|---|---|---|
| Auditor API | ✅ | ✅ |
| CQL Engine | ✅ | ✅ |
| Evidence Graph (UIAO_113) | ✅ | ✅ |
| Terraform adapter | ✅ | ✅ |
| Compliance Orchestrator | ✅ | ✅ |
| **Enforcement Runtime** | ❌ import-only | ✅ `uiao enforcement run` |

### Tooling

- **`tests/test_cli_help_smoke.py`** — walks the Typer command tree and asserts `--help` returns exit 0 for every registered command. 53 parametrized cases at v0.5.0 baseline; new commands automatically join coverage (#195). Catches the class of latent import bug PR #158 hit at v0.4.x.
- **AGENTS.md invariant I6** — disallows new flat top-level CLI commands; new commands must live under a sub-app (#195).

### Local verification (pre-0.5.0 cut)

```
$ python -m ruff check .
All checks passed!

$ python -m ruff format --check .
381 files already formatted

$ python -m mypy src/uiao
Success: no issues found in 187 source files

$ python -m pytest -q
2060 passed, 156 skipped
```

## [0.4.0] — 2026-04-23

**Theme: substrate-governance realignment + CI-gate restoration.** Landing this arc closes every silently-disabled quality gate that accumulated after the ADR-032 single-package consolidation (2026-04-20). Every Python quality signal on `main` is now actively enforced.

### Added

- **ADR-044** (`src/uiao/canon/adr/adr-044-substrate-governance-realignment.md`) — ratifies the post-ADR-032 alignment of UIAO_200, UIAO_201, the workspace-contract schema, the substrate walker, and the substrate-drift CI step to the single-package topology (#151).
- **UIAO_200 Substrate Manifest v2.0** — six-module topology (`uiao`, `tests`, `docs`, `scripts`, `inbox`, `deploy`); sub-boundaries inside `uiao/`; `role` enum widened from `[authority, consumer]` to `[authority, consumer, package, tooling, staging, deploy]` (#151).
- **UIAO_201 Workspace Contract v2.0** — `module_paths` mirrors v2.0 manifest; `build_outputs.package_dist` (was `impl_dist`); `canon_consumer_rule` retargeted (#151).
- **UIAO_008 CLI Reference v1.0** — promoted from top-level shadow `canon/UIAO_132_CLI_Reference_v1.0.md`; reallocated from UIAO_132 (collision with FedRAMP RFC-0026 spec) into the UIAO_002-099 top-level-canon range (#154).
- **UIAO_005 / UIAO_006 / UIAO_007** — promoted from top-level shadow canon (`SCuBA Value Proposition`, `AODIM Architecture`, `OrgTree Modernization`) with schema-conformant provenance (#154).
- **UIAO_001 SSOT v1.1** — expanded from a 21-line stub into a full authoritative doctrine: post-ADR-032 topology table, canon-consumer rule pointer, provenance chain model, 5-class drift taxonomy, canon change process (#167).
- **`src/uiao/rules/canon-consumer.md`** — new post-ADR-032 canon-consumer rule (importlib.resources reads, read-only runtime); supersedes the retired pre-consolidation rule under `impl/.claude/rules/` (#151).
- **`tests/test_api_smoke.py`** — three smoke tests on `uiao.api.app:app` (importability, route-prefix presence, openapi schema generation). Caught a latent production-deploy import bug that no other test surfaced (#158).
- **`[api]` optional extra** — declares `fastapi>=0.110`, `httpx>=0.27`, `uvicorn>=0.29`, `msal>=1.28` so `uiao.api.*` and the gcc-boundary-probe adapter actually resolve (#152, #158).
- **`[dev]` extra** — adds `types-PyYAML`, `types-requests` for mypy typeshed stubs.
- **Substrate-walker `docs/` scan** — extended to walk `docs/**/*.{md,qmd}` for code-path citations; new tests; 42 P2 narrative-drift warnings surface on current tree (non-blocking) (#166).
- **Two new walker tests** covering the docs-scan behavior (#166).

### Changed

- **Ruff gate → blocking.** 230-finding baseline cleared (128 via `ruff check --fix`, 7 via `--unsafe-fixes`, ~76 via `ruff format` splitting one-line dataclasses, 13 manual). Step-level `continue-on-error` on `ruff format --check` also removed (Copilot review) (#153).
- **Mypy gate → blocking with strict flags.** 130 findings burned down across four batches (#161, #162, #163, #164); `disallow_untyped_defs = true` + `warn_return_any = true` restored with 77 additional fixes (#165). Per-module overrides for docx-heavy generators + adapter-reflection surfaces documented inline.
- **Full pytest gate → blocking.** Restored after `[api]` dep declaration unblocked `tests/test_auditor_api.py` collection (#152).
- **`substrate-drift.yml`** — gates on `report.blocking` (P1) rather than `report.ok` (any finding), matching the `uiao substrate drift` CLI semantics; push-path filters made symmetric with pull_request filters (#151, #157).
- **CI path filters** repaired in all 7 workflows that still referenced the retired `impl/**` / `core/canon/` / `src/uiao/impl/**` paths (#150, #151). `adapter-conformance.yml` triggers widened to include registry + schema edits (#157).
- **Substrate walker** (`src/uiao/substrate/walker.py`) retargeted from `core/canon/*` to `src/uiao/canon/*`; `IMPL_REF_PATTERN` renamed `CODE_REF_PATTERN` and broadened to match both `src/uiao/` and `impl/` prefixes; `SubstrateReport.impl_refs_checked` renamed `code_refs_checked` (JSON contract change) (#151).
- **`workspace-contract.schema.json`** — `module_paths.required` narrowed to `[uiao, tests, docs]` with `minProperties: 3`; `build_outputs.impl_dist` → `package_dist`; `canon_consumer_rule.const` retargeted (#151).
- **`src/uiao/api/routes/routes.py`** split into `health.py` / `survey.py` / `orgpath.py`. The stitched file had been preventing `uiao.api.app` from importing — another latent production bug (#158).
- **README.md / Makefile / AGENTS.md** — rewritten for the flattened `src/uiao/` layout; obsolete `core/` / `impl/` references removed (#147, #151, #153-165).
- **`adapter-conformance.yml`** — now triggers on registry + schema edits in addition to adapter code (#157).
- **`release.yml`** — job renamed ("Build impl/ wheel and sdist" → "Build wheel and sdist"); `impl-dist-*` artifact → `uiao-dist-*`; `working-directory: impl` dropped; sigstore-verify snippet retargeted `uiao_impl-*` → `uiao-*` to match the distribution name (#150).
- **Schema-description cleanup** across `src/uiao/schemas/` — 4 stale `core/schemas/` / `core/canon/` path references in description strings retired to `src/uiao/schemas/` / `src/uiao/canon/` (#159).
- **Canon narrative drift cleared** — 11 P2 DRIFT-PROVENANCE warnings from ADR prose retired (ADR-028/029/031/032/044, UIAO_121/122/126) by retargeting `impl/...` citations to current `src/uiao/...` paths with historical notes (#156).

### Fixed

- **Production-deploy bug #1** — `deploy/windows-server/run.py` retargeted from the retired `uiao.impl.api.app:app` to `uiao.api.app:app`; `C:\srv\uiao\impl\src` sys.path shim removed (#150, #153).
- **Production-deploy bug #2** — two adapter directories with hyphens in their names (`active-directory/`, `gcc-boundary-probe/`) renamed to the underscore form (`active_directory/`, `gcc_boundary_probe/`). Hyphenated dir names are invalid Python package identifiers; every `from uiao.adapters.modernization.active_directory...` import was literally unresolvable. Locally masked because `msal` was missing; would have failed at startup on IIS (#155).
- **Production-deploy bug #3** — `src/uiao/api/app.py` imported `health`, `survey`, `orgpath` from `.routes` as if they were modules, but the symbols lived inside a single stitched `routes.py`. Split into separate files (#158).
- **Production-deploy bug #4** — `src/uiao/ir/mapping/ksi_to_ir.py` passed `hash=None` to `ProvenanceRecord(...)`; the field is `content_hash` (#165).
- **Hyphen-named dirs elsewhere** — substrate-walker now discoverable by mypy (was aborting at startup) (#155).

### Deprecated / Removed

- Top-level shadow canon directory (`canon/UIAO_005_*.md`, etc.) removed; contents promoted under `src/uiao/canon/` with registry entries (#154).

### Canon

- UIAO_001 SSOT v1.0 → **v1.1** (CANONICAL)
- UIAO_200 Substrate Manifest v1.0 → **v2.0** (OPERATIONAL)
- UIAO_201 Workspace Contract v1.0 → **v2.0** (OPERATIONAL)
- **UIAO_005** SCuBA Value Proposition (new registered) (CANONICAL)
- **UIAO_006** AODIM Architecture (new registered) (CANONICAL)
- **UIAO_007** OrgTree Modernization — AD to Entra ID (new registered) (CANONICAL)
- **UIAO_008** UIAO-Core CLI Reference (new registered) (CANONICAL, Draft)
- **ADR-044** Substrate Governance Realignment to Post-ADR-032 Single Package (ACCEPTED)
- **`src/uiao/rules/canon-consumer.md`** rewritten for the post-ADR-032 world

### CI stack state after 0.4.0

| Gate | Status |
|---|---|
| `schema-validation.yml` | ✅ blocking |
| `pytest.yml` | ✅ blocking (substrate fast + full suite) |
| `substrate-drift.yml` | ✅ blocking (P1 only; walker now works) |
| `metadata-validator.yml` | ✅ blocking |
| `adapter-conformance.yml` | ✅ blocking (330/330) |
| `ruff.yml` | ✅ blocking |
| `mypy.yml` | ✅ blocking (strict flags) |
| `quarto.yml` | ✅ render; deploy on main |
| `link-check.yml` | 🟡 soft-fail (repo config) |
| `release.yml` | build/sigstore/SBOM on tag |

### Infrastructure

- **Release workflow dry-run** — `python -m build --sdist --wheel` verified clean from the repo root; `uiao-0.4.0-py3-none-any.whl` + `uiao-0.4.0.tar.gz` produced; wheel filename pattern matches `release.yml`'s sigstore verification snippet. End-to-end run with sigstore signing requires a tag push from the owner's session.

### Local verification (pre-0.4.0 cut)

- `mypy src/uiao --ignore-missing-imports` → Success: no issues found in 171 source files.
- `pytest -q` → 1587 passed, 156 skipped, 0 failed.
- `ruff check .` → All checks passed.
- `ruff format --check .` → clean.
- `uiao substrate drift` → PASS with 42 P2 docs-narrative warnings (P1-only gate, non-blocking).
- `python -m build` → wheel + sdist produced clean.

---

## [Unreleased]

### Added
- Contributor foundation at repo root: `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md`, PR template, four structured issue templates (bug, canon-change, adapter-activation, governance-drift) (#37).
- `CODEOWNERS` re-established at `.github/CODEOWNERS` with canon/adapter-scoped ownership (#36).
- Tag-triggered release workflow building `impl/` wheel + sdist and attaching to GitHub Releases (#36).
- `.lycheeignore` baseline covering CI-predictable false-positive link-check patterns (#35).
- `dependabot.yml` at `.github/dependabot.yml` tracking `pip` (under `/impl`) and `github-actions` weekly (#21).
- First live CI at repo root:
  - `schema-validation.yml` — adapter registries, substrate manifest, workspace contract, metadata schema (#6)
  - `pytest.yml` — substrate walker (blocking) + full impl (blocking as of #19) (#11, #19)
  - `substrate-drift.yml` — `uiao substrate drift` on every canon PR (#16)
  - `metadata-validator.yml` — canon document frontmatter, blocking as of #20 (#17, #20)
  - `quarto.yml` — render on PR + deploy to GitHub Pages on push to main (#22)
  - `ruff.yml` — blocking as of #34 (#28, #34)
  - `link-check.yml` — lychee baseline, soft-fail initial state (#29)
- `UIAO_200` Substrate Manifest (`core/canon/substrate-manifest.yaml`) + schema (#4).
- `UIAO_201` Workspace Contract (`core/canon/workspace-contract.yaml`) + schema (#7).
- `UIAO_121–UIAO_124` adapter-framework specs properly registered in `document-registry.yaml` after renumbering from slug-style IDs (#20).
- Substrate walker + drift bootstrap at `impl/src/uiao_impl/substrate/walker.py` with `uiao substrate walk` / `uiao substrate drift` CLI, 10 tests (#8).
- `ADR-028` ratifying monorepo consolidation and retiring the `uiao-gos` federal/commercial firewall (#5).

### Changed
- **CyberArk adapter promoted** from `reserved/phase-planning` → `active/phase-1` in `core/canon/modernization-registry.yaml` (#32). 9 of 10 modernization adapters now active; only `mainframe` remains reserved (z/OS Connect infrastructure dependency).
- **Infoblox adapter promoted** from `reserved/phase-planning` → `active/phase-1` with NIOS >=8.0 runtime and FedRAMP-authorized annotation (#3).
- `docs/narrative/governance-os-directory-migration.md` rewritten from the migrated `uiao-gos` README into a substrate-aligned canonical narrative that closes the ADR-028 doctrinal loop (#31).
- `core/ARCHITECTURE.md` §2 rewritten from four-repository topology to three-module monorepo topology; `uiao-gos` firewall section replaced with "Uniform canon invariants" (#5).
- `core/CONMON.md` scope line retargeted from "federal pair, uiao-gos out of scope" to all monorepo modules (#5).
- `ADR-025 §D7` marked SUPERSEDED by ADR-028; partial-supersession banner added at ADR-025 top so readers arriving from any section see the relationship immediately (#14).
- Monorepo-aware canon path resolution in `impl/src/uiao_impl/config.py` and `impl/tests/canon_paths.py` — unblocks the full impl pytest suite (#15).
- Typer arguments: `B008` added to ruff ignore list (legitimate Typer idiom, not a bug) (#34).
- `docs/_quarto.yml`: `site-url` and `repo-url` retargeted from `uiao-docs` to the consolidated `uiao` repo (#22).
- Metadata validator soft-fail → blocking after renumbering 4 slug-style adapter-spec IDs (#20).
- Ruff soft-fail → blocking after burning down the 16 residual lint errors (#34).
- Pytest full-impl soft-fail → blocking after canon-path fix merged (#19).

### Removed
- `gos/` directory retired; its contents integrated into the canonical UIAO substrate (#3). Python code relocated to `impl/src/uiao_impl/directory_migration/`; IPAM adapters registered canonically; narrative moved to `docs/narrative/`.
- `impl/src/uiao_impl/directory_migration/` Python scaffolding (38 files, ~1,600 LOC) — all ARC-5 stubs with broken `from core.*` imports and zero callers. Markdown reference docs pointed to by registry entries retained (#12).
- `impl/src/uiao_impl/directory_migration/drift/drift_engine.py` — unused duplicate of `impl/src/uiao_impl/governance/drift.py` (#9).
- 3 stub provider adapters (entra, m365, servicenow) under `directory_migration/providers/` that duplicated mature implementations under `impl/src/uiao_impl/adapters/*.py` (#10).
- `core/.github/` tree (33 files — 24 inert workflows + CODEOWNERS + 7 issue templates + dependabot.yml) — GitHub only reads `/.github/`; these contributed nothing post-consolidation (#13).
- 211 tracked build artifacts from `docs/site/` (Quarto rendered output) and `docs/exports/{docx,pptx}` — already in `.gitignore` but predated the rule (#2). Working-tree savings: 160 MB.
- 128.9 MB of redundant PNG bytes via two pngquant passes (PR #18: 120.7 MB from 30 files ≥1 MB; PR #30: 8.2 MB from 26 files 100 KB–1 MB).

### Canon
- UIAO_200 UIAO Substrate Manifest (OPERATIONAL)
- UIAO_201 UIAO Workspace Contract (OPERATIONAL)
- UIAO_121 UIAO Adapter Conformance Test Plan — Template (CANONICAL)
- UIAO_122 UIAO Adapter Developer Training Program (CANONICAL)
- UIAO_123 UIAO Adapter Integration & Test Plan — Canonical Template (CANONICAL)
- UIAO_124 UIAO Adapter Operations Runbook (CANONICAL)
- ADR-028 Monorepo Consolidation and Integration of `uiao-gos` (ACCEPTED)

### Infrastructure
- Four predecessor repos (`uiao-core`, `uiao-docs`, `uiao-gos`, `uiao-impl`) merged into `WhalerMike/uiao` with **3,549 commits of history preserved** via git subtree merges (#1).

---

## Conventions

**Version tagging:** `vMAJOR.MINOR.PATCH` pushed as git tag → triggers `.github/workflows/release.yml` → builds wheel + sdist from `impl/`, creates GitHub Release with auto-generated notes.

**Pre-1.0 semantics:** minor version bumps may include breaking changes; read the [Unreleased] section carefully before upgrading across minor versions.

**Issue links:** `(#NN)` refers to `https://github.com/WhalerMike/uiao/pull/NN` unless otherwise noted.

## [0.3.0] — 2026-04-20

### Added
- **Single-package monorepo** consolidating `core/`, `impl/`, and partial `src/` into one `src/uiao/` Python package. `pip install -e .` now installs everything in one step; canon, rules, schemas, and KSI library ship as package data via `importlib.resources`. See [ADR-032](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/adr-032-single-package-consolidation.md).
- Full runtime dependency declarations in `pyproject.toml` (`jinja2`, `jsonschema`, `python-docx`, `python-pptx`, `openpyxl`, `matplotlib`, `compliance-trestle`, `compliance-trestle-fedramp`, `lxml`, etc.) — previously inherited from the separate `uiao-impl` editable install.
- Dynamic version from `src/uiao/__version__.py` via `[tool.setuptools.dynamic]` (SSOT; resolves prior drift between `pyproject.toml` and the module).
- Optional extras: `[dev]`, `[visuals]`, `[plantuml]`. Classifiers, keywords, `[project.urls]`, and root-level `[tool.pytest.ini_options]` added.
- `BlueCatAdapter` (BAM Tier-4 IPAM adapter) under `src/uiao/adapters/bluecat_{adapter,parser}.py` with 69 unit/OSCAL tests and fixtures (#114).
- Briefing generator test suite — 39 tests across `collect_ci_status`, `collect_memory_entries`, `collect_adapter_status`, `collect_control_coverage`, `collect_oscal_status`, `collect_priorities`, `collect_changelog`, and end-to-end `build_briefing()` (#112).
- Mypy CI workflow (`.github/workflows/mypy.yml`) — non-blocking while the 57 pre-existing type debts are burned down.
- `docs/governance/` — promoted governance docs (`ARCHITECTURE.md`, `VISION.md`, `CONMON.md`, `PROJECT-CONTEXT.md`, `CODE_OF_CONDUCT.md`, `NOTICE`) from the old `core/` root.

### Changed
- CLI entry point: `uiao = "uiao.cli.app:app"` (was `uiao.cli:main`); `uiao --version` now prints `uiao X.Y.Z` (was `uiao-core X.Y.Z`).
- `scuba_adapter` renamed to `scubagear_adapter`; class `ScubaAdapter` → `ScubaGearAdapter`; `ADAPTER_ID` `"scuba"` → `"scubagear"`. Resolves the canon/code inversion where the `scubagear` adapter-registry entry had no implementation while the `scuba` modernization entry had a conformance-behavior implementation (#113).
- All imports rewritten: `uiao.impl.*` → `uiao.*` across ~150 files.
- `uiao-core` / `uiao-impl` narrative references sanitized across 430+ non-ADR files. ADRs, `CHANGELOG.md`, and `RELEASE_NOTES.md` preserved as the archival record.
- `Settings._resolve_canon_root()` simplified to a two-tier resolver (`UIAO_CANON_PATH` env var, then packaged canon at `src/uiao/canon/`). Dead `../core` and `../uiao-core` sibling-checkout fallbacks removed.
- KSI `collector_id: uiao-core-ksi-builder` → `uiao-ksi-builder` across 84 YAMLs (metadata only; not matched by any runtime `COLLECTOR_ID`).

### Removed
- `core/` directory (content absorbed into `src/uiao/canon/`, `docs/governance/`, `scripts/tools/`, or removed as obsolete duplicates).
- `impl/` directory (content absorbed into `src/uiao/`, `tests/`, `scripts/`, `.github/workflows/`). `impl/pyproject.toml` and the `uiao-impl` editable distribution retired; `pip uninstall uiao-impl` clears the old install.
- Per-module `CLAUDE.md` / `AGENTS.md` under `core/` and `impl/` (module-scoped docs consolidated into the repo-root pair).

### Fixed
- `src/uiao/__version__.py` normalized to LF-only, no trailing blank.
- `ScubaGearAdapter` conformance: `ConnectionProvenance.identity`, `claim_id`, `entity`, `evidence.source`, `DriftReport.drift_type`, and `DriftReport.details["adapter"]` now carry the `scubagear` prefix (was `scuba`) — 30/30 conformance criteria pass.

### Migration

```bash
pip uninstall uiao-impl -y   # retire the old editable install (if present)
git pull origin main
pip install -e .             # single install step — all runtime deps declared
uiao --version               # -> uiao 0.3.0
pytest -q                    # baseline: ~1071 passed, ~156 skipped
```

Code that still imports from `uiao.impl.*` should be rewritten to import from `uiao.*`.
