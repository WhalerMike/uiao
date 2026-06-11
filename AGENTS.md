# AGENTS.md — UIAO Consolidated Monorepo

> Repo-root control surface for IDE agent integration. This file is the single agent entry point for the consolidated `src/uiao/` package.
>
> **Naming note:** the filename is `AGENTS.md` — the emerging tool-neutral convention recognized by Claude Code, OpenAI Codex, and other IDE agents. A thin `CLAUDE.md` stub at the repo root still resolves to this content for tools looking specifically for `CLAUDE.md`.

## Repository identity

- **Name:** `WhalerMike/uiao`
- **Purpose:** Unified Identity-Addressing-Overlay Architecture — a **universal-enterprise governance substrate** with drift-detected canon, schema-enforced adapters, and provenance-anchored evidence pipelines. The core engine is vertical-agnostic; federal compliance (FedRAMP Moderate Rev 5, OSCAL, KSI, BOD 25-01, CISA SCuBA) ships as the most mature vertical adapter pack on top of that substrate. See [ADR-085](src/uiao/canon/adr/adr-085-universal-enterprise-positioning.md) for the positioning doctrine — any artifact that describes the **core** as federal-scoped is a positioning bug.
- **Status:** pre-1.0; `main` is the primary development branch.
- **Cloud boundary (current deployment):** GCC-Moderate (Microsoft 365 SaaS only). This is the boundary the federal vertical is deployed against today; it is not a property of the core engine. Two named Commercial exceptions: Amazon Connect Contact Center, and SailPoint Non-Employee Risk Management (FedRAMP Moderate on AWS GovCloud, per ADR-059). Each exception is encoded as a discrete enum value in the `gcc-boundary` schema; new exceptions are added in lockstep with their authorizing ADR. Non-federal vertical adapter packs (commercial-regulated, state/local, generic enterprise) will introduce their own boundary enums under separate ADRs as they ship.

## Module topology

Declared machine-readably in [`src/uiao/canon/substrate-manifest.yaml`](src/uiao/canon/substrate-manifest.yaml) (UIAO_200):

| Module | Role | Contents |
|---|---|---|
| [`src/uiao/`](src/uiao/) | **Package** — the single installable `uiao` Python distribution. | Canon (`canon/`), rules (`rules/`), schemas (`schemas/`), KSI library (`ksi/`), adapters (`adapters/`), IR (`ir/`), CLI (`cli/`), governance, evidence, oscal, ssp, substrate walker, orchestrator, etc. |
| [`tests/`](tests/) | Test suite | ~1000+ tests: unit, integration, adapter conformance, substrate drift. |
| [`docs/`](docs/) | Derived documentation | Articles, guides, narratives, Quarto site. Every published doc traces provenance to canon under `src/uiao/canon/`. |
| [`scripts/`](scripts/) | Maintenance scripts | Validators, canon-sync, doc generators, one-shot tooling. |
| [`tools/`](tools/) | PowerShell generators | `Write-Phase2TSA.ps1`, `Write-Phase2Diagrams.ps1`, `Write-CanonFiles*.ps1` — author-time generators that read source models (`.psd1`/`.txt`) and write derived markdown into `phase2/` and other targets. Not invoked at runtime; not on the CI path. |
| [`diagrams/`](diagrams/) | Diagram-pipeline subsystem | Self-contained Mermaid SSOT system covering all 9 UIAO document categories. Own README, governance ([`diagrams/governance/DIAGRAM-GOVERNANCE.md`](https://github.com/WhalerMike/uiao/blob/main/diagrams/governance/DIAGRAM-GOVERNANCE.md), UIAO_DG_001 v2.0), metadata schema, registry of 17 active diagrams, render/validate/inject Python scripts, and CI workflow definition. Independent of phase numbering — uses `DIAG_NNN` namespace. |
| [`phase2/`](phase2/) | Phase 2 architecture artifacts | Generated output of `tools/Write-Phase2TSA.ps1` from the source model at `models/phase2/UIAO_Phase2_TSA.psd1`. Feeds the customer-facing **Phase 2 — Governance OS** chapter ([`docs/customer-documents/operational-guides/uiao-modernization-program/03-phase2-governance-os.qmd`](https://github.com/WhalerMike/uiao/blob/main/docs/customer-documents/operational-guides/uiao-modernization-program/03-phase2-governance-os.qmd)). Uses the `UIAO_P2_NNN` namespace (not the canonical `UIAO_NNN` allocation). Most domain/lifecycle/transformation files are placeholder scaffolds pending design sessions; `_legacy/` holds the prior generator output. Index at [`phase2/UIAO_Phase2_Index.md`](https://github.com/WhalerMike/uiao/blob/main/phase2/UIAO_Phase2_Index.md). |
| [`models/`](models/) | **Phase 2 source models — NOT canon authority.** | Holds `models/phase2/UIAO_Phase2_TSA.psd1`, the PowerShell-data-file source model that `tools/Write-Phase2TSA.ps1` consumes to generate `phase2/`. Renamed from `canon/` (which collided with `src/uiao/canon/`) so the role is explicit: generator-input source models, not canonical governance. Canon authority lives **only** at `src/uiao/canon/`. |
| [`inbox/`](inbox/) | Scratch surface | Agent-authored drafts. Nothing here is canon. |
| [`deploy/`](deploy/) | Deployment artifacts | `deploy/windows-server/` holds the IIS deployment surface (`run.py`, `web.config`, `requirements-windows.txt`) for the single-tenant FastAPI service in `src/uiao/api/`. `deploy/azure/` holds the **multi-tenant SaaS** surface (ADR-096): Dockerfile + Bicep IaC for Azure Container Apps, running `uiao.saas.asgi:app`. |
| [`.github/workflows/`](.github/workflows/) | CI | Schema validation, pytest, substrate-drift, mypy (non-blocking), ruff, quarto, link-check, release. |

Install: `pip install -e .` from the repo root; the `uiao` CLI entry point is [`uiao.cli.app:app`](https://github.com/WhalerMike/uiao/blob/main/src/uiao/cli/app.py).

## Operating principles (substrate-wide)

1. **SSOT** — every claim has exactly one canonical source under `src/uiao/canon/`. All other representations are provenance-anchored pointers. **ADRs are SSOT for the *decisions* they record, not for the *external facts* they cite** (statutory/regulatory mandates, vendor behavior, standards requirements): an external fact is authoritative only where the ADR directly links to its source. Downstream documents must trace an external fact to that source — either by citing it directly (preferred for customer-facing docs) or by citing an ADR that carries the inline link (the chain doc → ADR → source resolves); citing an ADR that lacks the link, or asserting the fact unsourced, is provenance drift. See [ADR-000 §"ADRs Are Decision Records, Not Sources of Truth"](src/uiao/canon/adr/adr-000-adr-process.md).
2. **Canon-anchored evidence** — every artifact the substrate produces cites the canon document ID and version it derives from.
3. **Dual-axis adapter taxonomy** — every adapter declares `class` (modernization | conformance) × `mission-class` (identity | telemetry | policy | enforcement | integration) per UIAO_003.
4. **Schema-first governance** — five JSON Schemas under `src/uiao/schemas/` validate every registry, manifest, and frontmatter edit in CI.
5. **Drift is explicit** — five-class taxonomy (`DRIFT-SCHEMA`, `DRIFT-SEMANTIC`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY`) defined in [`docs/docs/16_DriftDetectionStandard.qmd`](https://github.com/WhalerMike/uiao/blob/main/docs/docs/16_DriftDetectionStandard.qmd).
6. **Version isolation** — no references to any previous version in active canon context; ADRs are append-only with supersession markers.
7. **Diagram source of truth — committed Claude-authored SVG, not Mermaid or NanoBanana (ADR-093).** Authored documents (`.md` / `.qmd`) **must not** introduce new ```` ```mermaid ```` fenced code blocks. New diagrams are authored as **committed `<name>.svg`** files against the house style in `src/uiao/canon/svg-style/` (palette + templates + `STYLE.md`), and rasterized to PNG deterministically by `scripts/render_svg_images.py` (CI: `.github/workflows/image-gen.yml`). The SVG is the source of truth; the PNG is a build artifact. **No raster AI runs at render time** — this retires the Gemini 2.5 Flash Image ("NanoBanana") pipeline, whose generative output baked spelling errors into figures. `[IMAGE-NN: …]` / `[DIAGRAM-NN: …]` placeholders and `[IMAGE-REF: UIAO-FIG-NNN]` canonical reuse still drive the registry/manifest/`replace_placeholders.py` flow; the generation backend is the only thing that changed (SVG, not Gemini). `scripts/generate_images.py` is retained for placeholder harvesting + manifest rebuild (its Gemini call path is dead). The `uiao.generators.mermaid` module renders only pre-existing blocks during migration — not for authoring new ones.

## Key artifacts

| Concern | Artifact | Purpose |
|---|---|---|
| Module declaration | `src/uiao/canon/substrate-manifest.yaml` (UIAO_200) | What modules exist, their roles, drift-scan scope |
| Workspace binding | `src/uiao/canon/workspace-contract.yaml` (UIAO_201) | Local-root env var, module paths, build-output paths |
| Document registry | `src/uiao/canon/document-registry.yaml` | UIAO_NNN allocations across the canon |
| Modernization adapters | `src/uiao/canon/modernization-registry.yaml` | Change-making adapters (20 entries) |
| Conformance adapters | `src/uiao/canon/adapter-registry.yaml` | Read-only adapters (ScubaGear etc.) |
| Adapter schema | `src/uiao/schemas/adapter-registry/adapter-registry.schema.json` | Constrains both registries |
| Metadata schema | `src/uiao/schemas/metadata-schema.json` | Constrains canon document frontmatter |
| Substrate schema | `src/uiao/schemas/substrate-manifest/substrate-manifest.schema.json` | Constrains UIAO_200 |
| Workspace schema | `src/uiao/schemas/workspace-contract/workspace-contract.schema.json` | Constrains UIAO_201 |

## Public surface inventory (M5 — as of v0.5.0)

Authoritative record of what is CLI-reachable, what is library-only, and what is gated behind an optional extra. Update this table whenever a feature moves between tiers.

| Feature | Module | CLI surface | Tier | Notes |
|---|---|---|---|---|
| OSCAL generation | `uiao.generators.*` | `generate-ssp`, `generate-all`, `validate-ssp`, `generate-sbom` | CLI | Core pipeline |
| Visual rendering | `scripts/render_svg_images.py` (committed SVG → PNG, ADR-093) | `render-svg-images` | CLI / CI | Requires `cairosvg` (or Playwright); no API key |
| Document generation | `uiao.generators.docs`, `rich_docx`, `pptx` | `generate-docs`, `generate-docx`, `generate-pptx`, `generate-briefing` | CLI | — |
| ConMon / Sentinel | `uiao.monitoring` | `conmon-process`, `conmon-export-oa`, `conmon-dashboard` | CLI | — |
| Adapter runner | `uiao.adapters.*` | `adapter-run`, `adapter-run-scuba` | CLI | `servicenow`, `entra`, `scuba` |
| IR pipeline | `uiao.adapters.scuba.ir`, `uiao.evidence.*` | `ir-scuba-transform` … `ir-ssp-inject` | CLI | 11 commands |
| Auditor bundle | `uiao.auditor.bundle` | `ir-auditor-bundle` | CLI | REST API: `[api]` extra |
| CQL Engine | `uiao.cql` | `cql query` | CLI | UIAO_108; SQL-like queries over bundles |
| Evidence Graph | `uiao.evidence.graph` | `evidence graph` | CLI | UIAO_113; provenance tracing |
| Substrate walker | `uiao.substrate.walker` | `substrate walk`, `substrate drift` | CLI | — |
| KSI evaluation | `uiao.ksi` | `ksi evaluate`, `ksi report` | CLI | — |
| OSCAL export | `uiao.oscal` | `oscal generate`, `oscal export` | CLI | — |
| Orchestrator | `uiao.orchestrator` | `orchestrator run`, `orchestrator status` | CLI | — |
| **Enforcement Runtime** | `uiao.enforcement` | ❌ None | **Library-only** | UIAO_111; policies are Python callables — see `docs/docs/cli-reference.md §4.1` |
| **FastAPI REST API** | `uiao.api` | ❌ None (server) | **`[api]` extra** | `pip install "uiao[api]"`; see `docs/docs/cli-reference.md §5` |

## Public surface additions (v0.6.0)

New CLI commands and library modules introduced by the HRIT Single-ATO Productization mission theme (ADR-058 / UIAO_143). These rows supplement the v0.5.0 inventory above.

| Feature | Module | CLI surface | Tier | Notes |
|---|---|---|---|---|
| Reciprocity operations | `uiao.cli.reciprocity` | `uiao reciprocity onboard-agency`, `list-records`, `verify` | CLI | UIAO_140 / ADR-054 |
| HRIT Single-ATO Reciprocity emitter | `uiao.oscal.reciprocity_record` | (via `uiao reciprocity onboard-agency`) | CLI | UIAO_140 §6, HMAC-SHA256 signing |
| Per-agency reciprocity bundle | `uiao.oscal.reciprocity_bundle` | (library, used by CLI) | Library | UIAO_140 §7, self-verifying |
| ATO cadence SLA validator | `uiao.monitoring.ato_cadence` | `uiao conmon ato-cadence-check` | CLI | UIAO_140 §4, 30/45-day SSP + 30-day reauth |
| Configuration-latitude drift | `uiao.governance.config_latitude` | (governance library) | Library | UIAO_140 §5, DRIFT-SCHEMA emission |
| Evidence Graph v1.2 (ATO nodes) | `uiao.evidence.graph` | (via `uiao evidence graph`) | Library | UIAO_113 v1.2, ATO-decision + reciprocity-record nodes |
| KSI-RECIP family | `uiao.rules.ksi` (KSI-RECIP-001..008) | (via `uiao ksi evaluate`) | Data | 8 KSIs covering reciprocity-program health |
| **OrgPath Governance Runtime** | `uiao.governance.orgpath_runtime` | `uiao orgtree govern` | CLI | UIAO_163 / UIAO_174; composes the `DriftEngine` + Phase 5 adapters into a runnable governance loop, emits governance telemetry. Dry-run default; transport-free until a transport is injected in Python |
| **OrgPath Web Console** | `uiao.api.web.console` | ❌ None (web UI) | **`[api]` extra** | Azure-Portal-style, **read-only** (ADR-084 §C7) governance UI served by `uiao.api.app` under `/orgpath`. Server-rendered (Jinja2): drift dashboard, codebook explorer, principal lookup, run-a-governance-pass. Reads the runtime + Codebook; no writes |
| **OrgPath AD assessment** | `uiao.modernization.orgtree.ad_assign`, `ad_mapping` | `uiao orgtree assess` | CLI | Reads/assesses Active Directory (live LDAP or `--from-export`) and derives OrgPath facet values via a tenant-tunable AD→facet mapping (YAML override + in-code default), validating each against the Codebook (UIAO_151). `--write` (devices) plans/applies the Entra/ARM writes. Dry-run default |
| **OrgPath brownfield inventory** | `uiao.modernization.orgtree.inventory` | `uiao orgtree inventory` | CLI | Captures **already-enrolled** devices missing OrgPath across Entra (Graph `onPremisesExtensionAttributes`) + Arc (ARM `tags`) — live (`--from-graph`/`--from-arm`, `[api]` extra) or offline (`--devices-export`/`--machines-export`). Classifies capture status (complete/partial/absent) vs the Codebook, proposes a backfill via the source chain (`--asset-map` → `--owner-map`), and emits a `govern`-compatible snapshot (gaps re-surface as `DRIFT-IDENTITY`) + a backfill worklist. **Read-only** — no writes |
| **Graph transport** | `uiao.adapters.graph_transport` | (library, used by `--no-dry-run`) | **`[api]` extra** | Concrete `Transport` for the Entra/Graph plane: httpx + MSAL (`EntraTokenProvider`), cloud-aware via `resolve_graph_base`. `from_environment(cloud=…)` acquires the cloud-correct Graph audience + login authority |
| **ARM transport** | `uiao.adapters.arm_transport` | (library, used by `--no-dry-run`) | **`[api]` extra** | ARM-plane counterpart to `GraphTransport` for the Arc device-plane writeback (`ARC-SERVER` dispositions): resolves `management.azure.com` (commercial/GCC-Moderate) or `management.usgovcloudapi.net` (Azure Government) via `resolve_arm_base`, and acquires an **ARM-audience** token (`arm_token_scope`). A Graph-audience token sent to ARM is rejected 401 — this is why the two planes need distinct transports |

## Public surface additions (OrgPath multi-cloud — ADR-098)

| Feature | Module | CLI surface | Tier | Notes |
|---|---|---|---|---|
| **OrgPath binding profiles** | `uiao.modernization.orgtree.binding_profiles` | ❌ None | **Library-only** | UIAO_193 / ADR-098; loads + validates the six executable per-target storage contracts (`src/uiao/canon/data/orgpath/binding-profiles/`) against `binding-profile.schema.json` and the Codebook. `microsoft-entra` is the reference profile (the ADR-078 slot table); `aws`, `gcp`, `okta`, `ldap`, `vmware` are `proposed` until their transports ship. Boundary: Moderate/Commercial only |
| **OrgPath profile-driven planner** | `uiao.modernization.orgtree.profile_assign` | ❌ None | **Library-only** | UIAO_193 / ADR-098 phase 3; `BindingProfilePlanner` turns a binding profile + derived facets into `FacetOperation` writes routed by the profile's locators (the cross-vendor counterpart to `DeviceOrgPathPlanner`). Honors `writable`, skips reserved/inactive facets, emits `uncaptured` ops for `priority`-overflow casualties. Dependency-free, dry-run by nature |
| **Okta / LDAP transports** | `uiao.adapters.okta_transport`, `uiao.adapters.ldap_transport` | ❌ None | **Library-only** | Write seams for the `okta` / `ldap` binding profiles; registered as the first `mission-class: identity` modernization adapters (`okta-orgpath`, `ldap-orgpath`, status `proposed`). `httpx` (Okta) and `ldap3` (LDAP) are lazy-imported so module import never hard-requires them. Endpoints resolved from operator config; commercial/on-prem only |
| **OrgPath enforcement projection** | `uiao.modernization.orgtree.enforcement_projection` | ❌ None | **Library-only** | UIAO_193 / ADR-098 phase 4; the cross-vendor generalization of `rule_renderer.render_rule`. `EnforcementProjector` compiles a `CompositionSpec` (facet predicate) against a binding profile's `enforcement` plane into a vendor-neutral `EnforcementGroup` (facets must be bound on that plane; values validated against the Codebook), then `to_nsx` / `to_tag_match` render NSX security groups and the generic tag-membership form (Palo Alto DAG / AWS SG / GCP secure tags). Pure-identity profiles are rejected (no enforcement plane). Microsoft's row of the projection table remains `rule_renderer` |

## Public surface additions (LocPath — ADR-102)

| Feature | Module | CLI surface | Tier | Notes |
|---|---|---|---|---|
| **LocPath location registry** | `uiao.modernization.locpath` | ❌ None | **Library-only** | UIAO_194 / ADR-102 §D6 phase 1; loads + validates LocPath location registries — envelope against `location-registry.schema.json`, every node against `location.schema.json` (the UIAO_194 normative node schema), plus the integrity rules JSON Schema cannot express (level/depth consistency, case-insensitive path uniqueness, parent existence, UUID/timestamp parseability). Ships the `reference` registry (`src/uiao/canon/data/locpath/location-registry.yaml`) — the executable UIAO_194 worked example, not deployment data. Prefix-matching lookup (`node_for`, `nodes_under`, `sites`, `ancestors_of`) is the contract governance rules use. Mover/drift extensions and Entra exposure are later ADR-102 §D6 phases. Boundary: Moderate/Commercial only |
| **HR duty-station → LocPath assignment** | `uiao.modernization.locpath.hr_assign` | ❌ None | **Library-only** | UIAO_194 / ADR-102 §D6 phase 2; read-only conformance pass (registry id `hr-duty-station-locpath`, canon/adapter-registry.yaml). Resolves the Spec2-D1.1 `locationCode` on canonical HR records (`hrit.inventory.HRRecord`) through the governed duty-station map (`canon/data/locpath/duty-station-map.yaml`, `duty-station-map.schema.json`; targets must resolve at Site or deeper) into Primary-LocPath assignments with governing Site + provenance, emitting HRIT-shaped `DriftFinding`s (`GOV-LOCPATH-NNN`, class `DRIFT-IDENTITY` until the phase-3 location drift classes ship) for empty/unmapped codes, inactive targets, and duplicate employees. Extends ADR-088 (HR truth source) from organizational to physical placement. Never writes |

## Public surface additions (Active Governance Directory — ADR-100)

The **Active Governance Directory (AGD)** is UIAO's protocol-projection plane: an
in-path **read-only** LDAPv3 server (`uiao.directory`) that projects the OrgPath
Codebook + a principal snapshot over the LDAP wire protocol, so directory-bound
tooling can query the governance substrate in its native protocol. ADR-100 carves
the narrow read-only exception to the ADR-092 §1 data-plane boundary that this
in-path surface requires — it serves `BIND` / `SEARCH` / `UNBIND` and carries **no
write op**, so it cannot mutate canon or the provider of record. Pure-stdlib
(`asyncio` + a hand-rolled BER subset + stdlib `ssl`); no new runtime dependency.
Kerberos/KDC, SASL, write ops, and AD-specific schema are explicit ADR-100
roadmap, not shipped.

| Feature | Module | CLI surface | Tier | Notes |
|---|---|---|---|---|
| **AGD LDAP server** | `uiao.directory.server` | `uiao directory serve` | CLI | ADR-100; asyncio LDAPv3 read projection. Anonymous + simple bind; base/one/subtree search; `noSuchObject` for absent base, `unwillingToPerform` for unsupported ops. **LDAPS-on-connect** via `--tls-cert`/`--tls-key` (`build_server_tls_context`; default port 636 with TLS, 1389 plaintext) **and StartTLS** in-band upgrade (RFC 4511 §4.14) via `--starttls` (plaintext port, `server.tls_context`). Loopback + plaintext by default. `--check` validates inputs without binding |
| **AGD read scoping** | `uiao.directory.policy` | (via `serve`) | **Library-only** | ADR-100 §5 per-bind read scoping. `ReadPolicy` marks facets sensitive (default: clearance + cost-center, named via the `ldap` binding profile); sensitive attributes are redacted from results unless the connection completed an authenticated (non-anonymous) simple bind |
| **AGD DIT projection** | `uiao.directory.dit` | `uiao directory tree` | CLI | ADR-100; projects a `{principal_id, principal_type, attributes}` snapshot into a read-only DIT using the `ldap` binding profile's `uiaoOrgPath<Facet>` attribute names (UIAO_193). `tree` emits LDIF for inspection. No store of its own — read-only by construction |
| **AGD LDAP/BER codec** | `uiao.directory.ber`, `uiao.directory.protocol` | ❌ None | **Library-only** | ADR-100; minimal BER/ASN.1 codec + LDAPv3 message parse/serialize (RFC 4511 subset) + the search-filter algebra (and/or/not/present/equality/substrings) |

## Public surface additions (Azure SaaS — ADR-096)

The multi-tenant SaaS plane (`uiao.saas`) turns the single-tenant `uiao.api`
service into a per-request multi-tenant SaaS on Azure Container Apps. It is
**additive** — the Windows/IIS surface (`deploy/windows-server/`) is retained
for single-tenant/on-prem deployments. All Postgres / Azure-SDK code is
isolated behind a new `[saas]` extra and lazy-imported, so the blocking CI
test job (`.[api]` only) stays green.

| Feature | Module | Surface | Tier | Notes |
|---|---|---|---|---|
| **SaaS data-plane tenancy** | `uiao.saas.middleware`, `uiao.saas.context` | ASGI middleware | **`[api]` extra** | Resolves the Entra `tid` claim → registered `Tenant`, binds a per-request `TenantContext`. Rejects non-onboarded / non-active tenants 403 |
| **SaaS control plane** | `uiao.saas.control_plane`, `uiao.saas.provisioning` | REST `/control/v1` | **`[api]` extra** | Onboard / list / suspend / resume / deprovision tenants. Requires a publisher-tenant token with the `UIAO.SaaS.Admin` app role. Dry-run-by-default `StampExecutor` |
| **Inbound Entra verification** | `uiao.saas.auth` | library | **`[api]` extra** (JWKS verify: `[saas]`) | Claim validation is pure-stdlib; RS256 JWKS signature verification is lazy-imported (PyJWT) behind `[saas]` |
| **Tenant registry (durable)** | `uiao.saas.pg_repository` | library | **`[saas]` extra** | SQLAlchemy-async + asyncpg `saas_tenants` table. In-memory fallback (`uiao.saas.repository`) needs no extra |
| **SaaS ASGI entrypoint** | `uiao.saas.asgi:app` | server | **`[saas]` extra** | `uvicorn uiao.saas.asgi:app` — composes the data plane + control plane. Container image + Bicep IaC under `deploy/azure/` |
| **Per-tenant stamp executor** | `uiao.saas.azure_stamp`, `uiao.saas.azure_provisioners` | library | **`[saas]` extra** | `AzureStampExecutor` provisions a tenant's Postgres schema + Blob container + Key Vault secret scope (named after `data_namespace`, strictly validated). Dry-run unless `UIAO_SAAS_STAMP_EXECUTION_ENABLED`; orchestration is dependency-free + fake-tested, the Azure-backed provisioners lazy-import the SDKs |

### Rules for moving a feature between tiers

- **Library-only → CLI**: write a Typer command, add happy-path + failure-mode tests, update this table and `docs/docs/cli-reference.md`.
- **CLI → library-only**: add a deprecation note to the command's docstring for one release cycle, then remove the command and update this table.
- **Any tier → `[api]` extra**: requires a `[api]` optional-dependency declaration in `pyproject.toml` and a documentation note in `cli-reference.md`.



```bash
uiao substrate walk              # structured report
uiao substrate walk --json       # machine-readable
uiao substrate drift             # exit-code-only summary (CI-friendly)
```

Source: [`src/uiao/substrate/walker.py`](https://github.com/WhalerMike/uiao/blob/main/src/uiao/substrate/walker.py).

Emits `DRIFT-SCHEMA` (module paths exist) and `DRIFT-PROVENANCE` (registry docs resolve) findings.

## CI stack (all live at repo-root `.github/workflows/`)

| Workflow | Trigger | Blocking? |
|---|---|---|
| `schema-validation.yml` | Canon / schemas PRs | ✅ |
| `pytest.yml` | `src/uiao/**`, `tests/**`, `pyproject.toml` | ✅ (substrate fast + full suite) |
| `substrate-drift.yml` | Canon / substrate / workspace PRs | ✅ |
| `metadata-validator.yml` | `src/uiao/canon/**/*.md` + metadata schema | ✅ |
| `quarto.yml` | `docs/**` PRs | ✅ render; deploy on main |
| `adapter-conformance.yml` | `src/uiao/adapters/**` + adapter tests | ✅ |
| `ruff.yml` | Python PRs | ✅ |
| `mypy.yml` | Python PRs | ✅ |
| `link-check.yml` | `*.md` / `*.qmd` PRs + weekly | ✅ |
| `release.yml` | Tag `v*.*.*` | — |

> **Gate restoration history:** `ruff.yml` was returned to blocking after the 230-finding baseline was cleared (135 via `--fix`, ~76 via `ruff format` splitting one-line dataclasses, 13 manual fixes). The full pytest suite was restored to blocking once the `fastapi`/`httpx`/`uvicorn` runtime dependencies of `uiao.api` were declared as an `[api]` optional extra. `mypy.yml` was returned to blocking after a 4-batch burn-down (130 → 0) combining per-module suppressions for third-party-stub-less surfaces (python-docx, python-pptx, matplotlib, jinja2, etc.), duck-typed pattern ignores (adapter-class reflection, importlib.metadata), and real type fixes (entra_token None-narrowing, drift-class Literal typing, ProvenanceRecord `content_hash` kwarg).

## Commit convention

```
<verb>: <module-or-area> — <description>
```

Common `<verb>`s: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`. Use a scope prefix (e.g. `feat(adapters/bluecat):`) when it clarifies blast radius. Cross-cutting commits are permitted — describe the cross-cut in the body.

## Operating rules

- **Canon edits** → `src/uiao/canon/`, plus a UIAO_NNN entry in `document-registry.yaml` if the document is new. Doctrine changes require an ADR under `src/uiao/canon/adr/`.
- **New CLI commands** ship with happy-path + failure-mode tests in the same PR.
- **Adapters** go under `src/uiao/adapters/` and register in `src/uiao/canon/adapter-registry.yaml` (conformance) or `modernization-registry.yaml` (modernization). Every adapter declares `class` × `mission-class` per UIAO_003.
- **Microsoft Graph adapters** resolve their endpoint via `uiao.adapters._graph_clouds.resolve_graph_base()` rather than hardcoding hostnames. Accepted config keys: `cloud` (`commercial` / `gcc-high` / `dod`, default `commercial` — also serves GCC-Moderate per ADR-033), `graph_api_version` (default per-adapter — `beta` for IntuneAdapter; `v1.0` for EntraAdapter, M365Adapter, EntraDynamicGroupsAdapter, EntraAdminUnitsAdapter, InBoundaryTelemetry), and an explicit URL override key (`graph_endpoint` for most adapters; `api_base_url` for the two Entra group/AU adapters that pre-dated the convention). Unknown clouds fail closed at construction.
- **Azure Resource Manager (ARM) writers** (the Arc device-plane writeback) resolve their base via `uiao.adapters._arm_clouds.resolve_arm_base()` and their token audience via `arm_token_scope()` — never by reusing the Graph transport. The ARM plane uses a distinct host (`management.azure.com` for commercial/GCC-Moderate, `management.usgovcloudapi.net` for Azure Government) and a distinct token audience (`…/.default` on the ARM host); a Graph-audience token is rejected by ARM with HTTP 401. `EntraTokenProvider` takes a `scopes=` audience and a cloud-aware `from_environment(cloud=…)` authority so Graph and ARM writers each get a correct token.
- **Canon reads at runtime** use `importlib.resources` against `uiao.canon` / `uiao.rules` / `uiao.schemas`, never hardcoded filesystem paths.
- **Python lint/format gates are independent and both blocking.** `ruff.yml` runs `ruff check` *and* `ruff format --check` as separate gates; passing one doesn't satisfy the other. Before pushing any Python change run `ruff check --fix <paths>` *and* `ruff format <paths>`. Recurring gotchas worth pre-empting:
    - **Don't import what you don't use** (`F401`). Common temptations: `dataclasses.field` when only `@dataclass` is needed; `datetime.datetime` / `datetime.timezone` when the adapter inherits `self._now()` from `DatabaseAdapterBase` or has an equivalent local helper.
    - **Don't quote forward-reference annotations** (`UP037`) in files that already declare `from __future__ import annotations` — every annotation is deferred (string at runtime) already, so explicit `"DriftReport"` quoting is redundant. Import the referenced type at module level so mypy resolves it, then write the annotation unquoted. The `# noqa: F821 — forward reference` comment is *also* redundant in that case and should not be added.
    - **Same rule for circular-import workarounds.** If a module-level import would cycle, prefer restructuring or `TYPE_CHECKING`-guarded imports over inline `import` inside the method — but if the inline import is unavoidable, leave the annotation quoted *and* keep the inline import; don't mix the two patterns.

## History

The monorepo was consolidated from four predecessor repos (`uiao-core`, `uiao-docs`, `uiao-gos`, `uiao-impl`) on 2026-04-17 with full history preserved ([ADR-028](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/adr-028-monorepo-consolidation-gos-integration.md)). The `uiao-gos` federal/commercial firewall was retired in that pass; its directory-migration adapters (`bluecat-address-manager`, `infoblox`) are now canonical modernization adapters.

On 2026-04-20 the hybrid `core/` + `impl/` + partial `src/` tree was flattened into a single `src/uiao/` package with `pip install -e .` packaging and full runtime deps declared ([ADR-032](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/adr-032-single-package-consolidation.md)). Everything that used to import from `uiao.impl.*` now imports from `uiao.*`; canon ships inside the package via `importlib.resources`.

## Writing patterns

- **Chunked writes for long content (>≈150 lines), regardless of filetype.** Applies equally to `.md`, `.qmd`, `.py`, `.yaml`, and `.json`. Write the file in 3–5 logical sections using an initial `Write` for section 1 then `Edit` calls to append subsequent sections via unique anchor text. Length — not filetype — determines when to chunk.
    - **Why**: stream-idle timeouts truncate single-Write operations on multi-hundred-line files; each chunk persists as it lands, so a timeout mid-document costs at most one section, not the whole file. Also produces reviewable increments.
    - **Ordering for Python**: imports → constants/dataclasses → utilities → higher-level functions → `main` / CLI. Each chunk depends only on what's already above it.
    - **Ordering for Markdown/Quarto**: frontmatter → overview → principles → body sections → appendices → references. Each chunk is self-contained prose; dependencies are by narrative flow, not execution.
- **Session memory is ephemeral.** Within-session pledges ("I'll use this pattern from now on") do not persist across session boundaries or context compactions. Durable behavior lives in this file — if a pattern is worth adopting, commit it here.

## Agent usage notes

- **Always run `uiao substrate walk` first** on a fresh clone to validate the tree is intact.
- **Canon changes belong under `src/uiao/canon/`.** If a change would create a new canonical governance document, make the PR against `src/uiao/canon/` with a UIAO_NNN allocation in `document-registry.yaml`.
- **Read the relevant ADR before touching doctrinal canon.** ADR-028 retires the firewall; ADR-025 §D7 is superseded; ADR-027 defines adapter retirement.
- **CI is comprehensive.** 6 blocking workflows will catch schema violations, drift, and test regressions before merge.

## Repository Invariants

These rules define how the monorepo is organized and why. Violating any of them breaks either the CLI, the governance model, or the build pipeline. Changes that cross an invariant require an ADR and human review, not a quick fix.

### Directory intent

`src/uiao/` is the **single installable Python package** — runtime code, canon, schemas, rules, KSI, adapters, CLI. Post-ADR-032 there is no sibling `core/` or `impl/` tree: every concern previously split across those directories now lives under `src/uiao/<subpackage>/`. Canon (under `src/uiao/canon/`) is the governance authority — SSOT, ADRs, schemas, rules, KSI, specs, registries. Once canon is production-frozen it is protected: changes require a canon-change ADR and governance-board review. Runtime code consumes canon via `importlib.resources`, never by reaching outside its package.

`tests/` is the **single test suite** — unit, integration, adapter conformance, substrate drift. Authoritative; previously split between `impl/tests/` and `core/tests/`, now consolidated.

`docs/` is **human-readable documentation source only**. Source extensions: `.qmd`, `.md`, `.yml`, `.yaml`, `.puml`. Binary build output (`.docx`, `.pdf`, `.png`, `.epub`, `.pptx`) is **generated**, not authored, and should live in build output directories (`docs/_site/`, `docs/publications/`) that are either gitignored or release-pinned. Never commit binary output into the source tree alongside source files.

`scripts/` is **workspace tooling** — bootstrap, link check, schema validators, reorganization helpers. Short-lived; not imported at runtime.

`inbox/` is **draft staging** — content that isn't canonized yet. Promote to `src/uiao/canon/` or `docs/` when ready.

`deploy/windows-server/` holds the **Windows IIS deployment artifacts** (uvicorn `run.py`, `web.config`, `requirements-windows.txt`) for the FastAPI service in `src/uiao/api/`. Referenced from `src/uiao/api/app.py`.

### Technical invariants

**I1. `src/uiao/` is a single regular package.**
One `__init__.py` at `src/uiao/` level; one distribution named `uiao`; one import root. The pre-ADR-032 PEP 420 namespace split between `src/uiao/*` and `impl/src/uiao/impl/*` is retired — there is no `uiao.impl` subpackage anymore. Imports are always `from uiao.<subpackage> import …`.

**I2. Single CLI entry point: `uiao.cli.app:app`.**
The `uiao` console script registered by `pyproject.toml` resolves directly to `src/uiao/cli/app.py`. No bridge module, no lazy-import indirection, no `sys.path` manipulation. If a CLI subcommand fails on import, debug the subcommand's own imports — not the entry point.

**I3. One `pyproject.toml`, one editable install.**
`pip install -e .` from the repo root installs everything: runtime code, canon, schemas, rules, KSI, adapters (shipped as package-data per the root `pyproject.toml`). There is no sibling `impl/pyproject.toml` and no install-order dance. Dev tooling: `pip install -e ".[dev]"`.

**I4. Canon is a read-only dependency of code.**
Code reads canon via `importlib.resources.files("uiao.canon")` and similar. Code must not write to canon, and must not assume canon is at a particular filesystem path — it may be packaged as resources inside an installed wheel.

**I5. Canon changes flow through the canon-change process.**
Adding, modifying, retiring, or superseding anything under `src/uiao/canon/` requires:

- A new `UIAO_NNN` allocation in `document-registry.yaml` (for new docs)
- A new ADR in `src/uiao/canon/adr/` (for doctrinal changes)
- Governance review

Direct commits that touch canon without an ADR reference are a governance drift signal.

**I6. CLI commands live under sub-apps; new flat top-level commands are disallowed (see ADR-046).**
Every command in `src/uiao/cli/` must be registered under a domain sub-app
(`adapter`, `canon`, `conmon`, `evidence`, `generate`, `ir`, `ksi`,
`orchestrator`, `oscal`, `scuba`, `substrate`, …). The only exception is the
root `--version` / `--help` callback in `cli/app.py`. A PR that adds a flat
top-level `@app.command(...)` is rejected at review unless it also introduces
the sub-app that hosts it. The smoke test in
`tests/test_cli_help_smoke.py` walks the Typer tree and asserts `--help`
returns exit 0 for every command, catching import regressions across the
whole surface.
