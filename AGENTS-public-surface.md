# AGENTS — Public Surface Additions (companion to AGENTS.md)

> Append-only changelog of CLI/library surface added since the v0.5.0 **M5
> inventory** in
> [`AGENTS.md`](AGENTS.md#public-surface-inventory-m5--as-of-v050). Split out
> of AGENTS.md to keep the agent entry point lean; content is unchanged.
> New version waves are appended **here**, not to AGENTS.md. Tier-move rules
> remain in [`AGENTS.md`](AGENTS.md#rules-for-moving-a-feature-between-tiers).

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

> **CLI promotion (v0.6.x).** All ADR-102 §D6 phases — plus the ADR-104
> E911 layer — are now operator-reachable through the `uiao locpath`
> sub-app (`src/uiao/cli/locpath.py`, registered in `cli/app.py`), the
> physical-place counterpart to `uiao orgtree`. Commands:
> `validate registry` / `validate duty-station-map` (phase 1),
> `assign` (phase 2), `mover` + `policy-drift` (phase 3),
> `e911-check` (ADR-104), and `expose groups` / `expose admin-units`
> (phase 4). Every command is **read-only** and accepts a JSON HR /
> observed-state export, an optional agency `--registry` / `--map`
> override, `--out` for machine-readable output, and (where findings can
> gate CI) `--strict` to exit non-zero. Tests:
> `tests/test_cli_locpath.py`. The rows below now read **CLI** where they
> previously read library-only; the underlying functions are unchanged.

| Feature | Module | CLI surface | Tier | Notes |
|---|---|---|---|---|
| **LocPath location registry** | `uiao.modernization.locpath` | `uiao locpath validate registry` | **CLI** | UIAO_194 / ADR-102 §D6 phase 1; loads + validates LocPath location registries — envelope against `location-registry.schema.json`, every node against `location.schema.json` (the UIAO_194 normative node schema), plus the integrity rules JSON Schema cannot express (level/depth consistency, case-insensitive path uniqueness, parent existence, UUID/timestamp parseability). Ships the `reference` registry (`src/uiao/canon/data/locpath/location-registry.yaml`) — the executable UIAO_194 worked example, not deployment data. Prefix-matching lookup (`node_for`, `nodes_under`, `sites`, `ancestors_of`) is the contract governance rules use. Mover/drift extensions and Entra exposure are later ADR-102 §D6 phases. Boundary: Moderate/Commercial only |
| **HR duty-station → LocPath assignment** | `uiao.modernization.locpath.hr_assign` | `uiao locpath assign` | **CLI** | UIAO_194 / ADR-102 §D6 phase 2; read-only conformance pass (registry id `hr-duty-station-locpath`, canon/adapter-registry.yaml). Resolves the Spec2-D1.1 `locationCode` on canonical HR records (`hrit.inventory.HRRecord`) through the governed duty-station map (`canon/data/locpath/duty-station-map.yaml`, `duty-station-map.schema.json`; targets must resolve at Site or deeper) into Primary-LocPath assignments with governing Site + provenance, emitting HRIT-shaped `DriftFinding`s (`GOV-LOCPATH-001..005`, class `DRIFT-IDENTITY::location-assignment`) for empty/unmapped codes, inactive targets, and duplicate employees. Extends ADR-088 (HR truth source) from organizational to physical placement. Never writes |
| **Location Mover + drift classes** | `uiao.modernization.locpath.mover`, `uiao.modernization.locpath.drift` | `uiao locpath mover`, `policy-drift` | **CLI** | UIAO_194 / ADR-102 §D6 phase 3. The three location drift classes ship as **sub-classes** of the canonical taxonomy (ADR-063 / UIAO_163 convention; ADR-012 + ADR-033 top-levels unchanged): `DRIFT-IDENTITY::location-assignment`, `DRIFT-AUTHZ::location-policy`, `DRIFT-BOUNDARY::location-boundary`. `plan_location_moves()` diffs two assignment states into join/leave/move `MoverEvent`s carrying the stale impact surfaces (e911-dispatchable-location; dynamic-groups + administrative-units on cross-site moves; telemetry/service-access/DIA boundary transitions) plus one assignment-drift finding per event (`GOV-LOCPATH-006`). `detect_location_policy_drift()` compares `ObservedSiteState` (the phase-3 observational contract — collectors are separate; gcc_boundary_probe is the boundary-signal precedent) against governed site classification (`GOV-LOCPATH-007..011`). Both read-only; phase 4 owns the writes |
| **LocPath Entra exposure** | `uiao.modernization.locpath.entra_exposure` | `uiao locpath expose groups`, `admin-units` | **CLI** | UIAO_194 / ADR-102 §D6 phase 4 — completes the §D6 plan. `plan_locpath_site_groups()` / `plan_locpath_admin_units()` derive one Entra group / Administrative Unit per governed Site (`LocPath-Site-<SEG>-Users`, `AU-Site-<SEG>`; AUs restricted-management per UIAO_154) with membership from the Primary-LocPath assignment plan. Two modes honoring ADR-102 §D5 (LocPath claims NO extensionAttribute slot): **assigned membership** (default — the governed substrate is the membership source; Graph bodies bind members through a caller-supplied employee_id→objectId map, failing closed on unresolved identities) and **dynamic rule** (only when the deployment supplies a `locator` — the future binding-profile seam — rendering `(<locator> -startsWith "/SITE/PATH")`). Planning is pure (no Graph I/O); `to_graph_body()` mirrors the dynamic-groups / admin-units adapter shapes; transport/apply stays with the existing Entra adapters |

## Public surface additions (Active Governance Directory — ADR-100)

The **Active Governance Directory (AGD)** is UIAO's protocol-projection plane: an
in-path **read-only** LDAPv3 server (`uiao.directory`) that projects the OrgPath
Codebook + a principal snapshot over the LDAP wire protocol, so directory-bound
tooling can query the governance substrate in its native protocol. ADR-100 carves
the narrow read-only exception to the ADR-092 §1 data-plane boundary that this
in-path surface requires — it serves `BIND` / `SEARCH` / `UNBIND` and carries **no
write op**, so it cannot mutate canon or the provider of record. Pure-stdlib
(`asyncio` + a hand-rolled BER subset + stdlib `ssl`); the core is pure-stdlib,
no new core runtime dependency. SASL/GSSAPI bind is the one optional surface
(behind the `[kerberos]` extra, ADR-101). Writes are accepted as **governed
intent** (ADR-109) — translated, never applied to a store — and `serve --apply`
now promotes them to **gated L3 actuation** routed through the `ldap`
binding-profile transport to the provider of record. The projection can be fed
straight from a real OrgPath producer (`serve/tree --from-assessment`, the
`uiao orgtree assess` output) rather than only a hand-authored snapshot.
KDC/ticket issuance and AD-specific *write* schema remain roadmap.

| Feature | Module | CLI surface | Tier | Notes |
|---|---|---|---|---|
| **AGD write-as-intent** | `uiao.directory.writes` | `uiao directory serve --enable-writes` | CLI | ADR-109; a `modify` is translated by `translate_modify` into governed `FacetOperation`s (ADR-084) and routed by `WriteRouter` **dry-run by default** — never applied to the projection. Only governed `uiaoOrgPath<Facet>` attributes are writable (non-governed → `unwillingToPerform`); facets are single-valued; values Codebook-validated. Writes require an authenticated bind (→ `insufficientAccessRights` otherwise) and a configured router (→ `unwillingToPerform`, read-only, otherwise). `--enable-writes` is plan-only (L2); `--apply` promotes to live actuation (next row) |
| **AGD write actuation** | `uiao.directory.actuation`, `uiao.adapters.entra_facet_writer` | `uiao directory serve --enable-writes --apply --provider {ldap,entra}` | CLI | ADR-109 §3 / ADR-092 §3; `FacetActuator` is the gated `apply_fn` seam — routes an approved write plan into a Phase-5-shaped adapter's `apply(operations, dry_run=False)`. Two providers: `--provider ldap` uses `FacetWriteAdapter` over `LdapTransport.modify` (addressed by DN); `--provider entra` uses `EntraFacetWriter` over `GraphTransport` (PATCH `onPremisesExtensionAttributes` on `/users/{id}` or `/devices/{id}`, addressed by the resolved principal id+type — `servicePrincipal` and synced-user writes refused/read-only at Graph). The projected-DN → `(principal_id, principal_type)` resolution is `Directory.principal_for`, threaded via `WriteRouter(principal_resolver=…)` onto each op's `metadata`. Actuation is **off by default**: `FacetActuator(adapter, enabled=False)` raises `ActuationDisabled` (the L3 opt-in); `governance_review_ops` always held; each apply audited. Construction deferred past `--check`, so validation opens no connection / acquires no token |
| **AGD AD-schema veneer** | `uiao.directory.ad_schema` | `uiao directory serve/tree --ad-veneer` | **Library-only** | ADR-110; opt-in (default off), **read-only** veneer synthesized at build time by `build_directory(..., ad_veneer=True)`: `sAMAccountName` / `userPrincipalName` / `displayName` / AD `objectClass` values / a deterministic, namespaced **non-authoritative** synthetic `objectSid` (advertised via `uiaoSyntheticSid: TRUE`). Never stored; never a governed facet (so AD attrs are refused on `modify`, ADR-110 §4). The AGD never issues authoritative SIDs / is an AD-DC / accepts domain join |
| **AGD LDAP server** | `uiao.directory.server` | `uiao directory serve` | CLI | ADR-100; asyncio LDAPv3 read projection. Anonymous + simple bind; base/one/subtree search; `noSuchObject` for absent base, `unwillingToPerform` for unsupported ops. **LDAPS-on-connect** via `--tls-cert`/`--tls-key` (`build_server_tls_context`; default port 636 with TLS, 1389 plaintext) **and StartTLS** in-band upgrade (RFC 4511 §4.14) via `--starttls` (plaintext port, `server.tls_context`). Loopback + plaintext by default. `--check` validates inputs without binding |
| **AGD SASL/GSSAPI bind** | `uiao.directory.sasl` | `uiao directory serve --sasl-gssapi` | **`[kerberos]` extra** | ADR-101; gate-only Kerberos ticket validation. Mechanism-agnostic multi-step `SaslMechanism` state machine (driven over `saslBindInProgress`); `GssapiMechanism` (RFC 4752) lazy-imports `gssapi`, accepts the client's service ticket with the AGD's **own** keytab, and maps the validated principal into read scope (ADR-100 §5). Never issues tickets / runs a KDC / stores user secrets (ADR-101 §4 boundary). Auth gates reads only — no write op |
| **AGD read scoping** | `uiao.directory.policy` | (via `serve`) | **Library-only** | ADR-100 §5 per-bind read scoping. `ReadPolicy` marks facets sensitive (default: clearance + cost-center, named via the `ldap` binding profile); sensitive attributes are redacted from results unless the connection completed an authenticated (non-anonymous) simple **or SASL** bind |
| **AGD DIT projection** | `uiao.directory.dit` | `uiao directory tree` | CLI | ADR-100; projects a `{principal_id, principal_type, attributes}` snapshot into a read-only DIT using the `ldap` binding profile's `uiaoOrgPath<Facet>` attribute names (UIAO_193). `tree` emits LDIF for inspection. No store of its own — read-only by construction |
| **AGD assessment feed** | `uiao.directory.feed` | `uiao directory tree/serve --from-assessment` | CLI | ADR-100; `principals_from_assessment` converts `uiao orgtree assess --out` output (facet-*name* values) onto the Codebook's `extensionAttribute` slots, so the projection is fed from a real OrgPath producer (AD survey → assess → AGD) rather than a hand-authored snapshot. Mutually exclusive with `--snapshot`. `serve --bind name=password` sets the simple-bind credential map from the CLI |
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

## Public surface additions (SaaS production-readiness — ADR-115)

A cloud-agnostic production-readiness layer on top of ADR-096. All of it is
stdlib + `pydantic` + Starlette (the `[api]` extra) — no `[saas]` dependency —
so the blocking CI test job covers every line, and it ships unchanged on any
compute target (Azure Container Apps today; AWS later).

| Feature | Module | Surface | Tier | Notes |
|---|---|---|---|---|
| **Per-plan quotas** | `uiao.saas.quotas` | library | **`[api]` extra** | `PlanQuota` per `TenantPlan` (trial/standard/enterprise/gov): `requests_per_minute` + `burst` + advisory caps. Defaults monotonic, override-friendly; unknown plan fails closed to trial ceilings |
| **Per-tenant rate limiting** | `uiao.saas.ratelimit` | ASGI middleware | **`[api]` extra** | `TenantRateLimiter` fixed-window over each plan's `window_limit`, keyed by tenant id. Best-effort **per-replica**. `429` + `Retry-After` + `RateLimit-*` headers; admitted requests carry `RateLimit-*` too. Injectable clock → deterministic tests |
| **Distributed rate limiting** | `uiao.saas.ratelimit` | ASGI middleware | **`[api]` extra** (Redis store: `[redis]`) | `DistributedTenantRateLimiter` runs the same per-plan budget over a shared `WindowStore` for a **globally-exact** limit across replicas (ADR-118) — `RedisWindowStore` in production (lazy `redis.asyncio`), `InMemoryWindowStore` for tests. Drop-in behind the same `check(tenant)` contract; the middleware awaits it. Selected by `UIAO_SAAS_RATE_LIMIT_REDIS_URL` |
| **Control-plane audit trail** | `uiao.saas.audit`, `uiao.saas.pg_audit` | REST `GET /control/v1/audit` | **`[api]` extra** (durable sink: `[saas]`) | Immutable `AuditEvent` per lifecycle action (onboard/suspend/resume/deprovision, success *and* rejection) with actor = publisher-admin subject. `build_audit_sink` selects the durable, append-only `PostgresAuditSink` (`saas_audit_events`, shares the registry's passwordless engine) when a database is configured, else the in-memory `InMemoryAuditSink`. Endpoint gated behind `UIAO.SaaS.Admin` |
| **RFC 9457 problem+json** | `uiao.saas.errors` | both planes | **`[api]` extra** | `application/problem+json` everywhere — standard members plus `error` (stable machine code, preserved from prior shapes) + `tenant` extensions. Data-plane middleware builds it directly; `HTTPException` handler renders control-plane errors identically |
| **Readiness probe** | `uiao.saas.app` (`/readyz`), `TenantRepository.ping()` | server | **`[api]` extra** | `/readyz` confirms the tenant registry is reachable (`SELECT 1` for Postgres) → `503 degraded` otherwise. Azure Container App readiness probe repointed `/healthz` → `/readyz`. `/healthz` stays the static liveness probe |

## Public surface additions (Azure SaaS deployment hardening — ADR-116)

Cloud-portable deployment hardening on top of ADR-096. The token-cache logic is
stdlib-only (`[api]` extra); `azure-identity` and `sqlalchemy` are lazy-imported
behind the `[saas]` extra, so the blocking CI test job covers the new code.

| Feature | Module | Surface | Tier | Notes |
|---|---|---|---|---|
| **Passwordless Postgres (Entra)** | `uiao.saas.pg_auth` | library | **`[api]` extra** (token acquire: `[saas]`) | `EntraPostgresTokenProvider` caches + refreshes an OSSRDBMS access token used as the Postgres connection password; `apply_entra_auth` injects it per-connection via a SQLAlchemy `do_connect` listener. Sovereign-cloud-aware scope (`ossrdbms_scope_for`). Wired by `build_repository` when `UIAO_SAAS_DATABASE_USE_ENTRA_AUTH=true`. Removes the long-lived DB password entirely |
| **Bicep IaC validation gate** | `.github/workflows/bicep-validate.yml` | CI | n/a | Compiles the whole Bicep graph + validates the param file on every `deploy/azure/**` change — credential-free (`az bicep build` / `build-params`), no subscription. Postgres Bicep now binds the managed identity as Entra admin with password auth disabled |

## Public surface additions (AWS SaaS surface — ADR-117)

The AWS parallel of the Azure SaaS surface — same `uiao.saas` application, a
second cloud substrate. AWS runtime deps (`boto3` + shared SQLAlchemy/asyncpg)
are the new `[aws]` extra; `import uiao.saas` pulls neither boto3 nor the Azure
SDKs, so the blocking CI job covers the new application code.

| Feature | Module | Surface | Tier | Notes |
|---|---|---|---|---|
| **Passwordless Postgres (RDS IAM)** | `uiao.saas.aws_pg_auth` | library | **`[api]` extra** (token sign: `[aws]`) | `RdsIamTokenProvider` caches + regenerates a short-lived RDS IAM auth token used as the Postgres connection password, through the **same** `pg_auth.apply_token_auth` `do_connect` seam as the Entra provider (ADR-116). `boto3` lazy-imported. Wired by `build_repository` when `UIAO_SAAS_DATABASE_USE_AWS_IAM_AUTH=true` |
| **AWS per-tenant stamp executor** | `uiao.saas.aws_stamp`, `uiao.saas.aws_provisioners` | library | **`[api]` extra** (provisioners: `[aws]`) | `AwsStampExecutor` mirrors `AzureStampExecutor` across RDS schema / S3 prefix / Secrets Manager scope, reusing the cloud-neutral `Provisioner` protocol + `require_safe_namespace` guard. Dry-run unless `UIAO_SAAS_STAMP_EXECUTION_ENABLED`; orchestration is dependency-free + fake-tested, the boto3 provisioners lazy-import |
| **AWS CDK IaC** | `deploy/aws/` (`app.py`, `uiao_saas_stack.py`) | server | **CDK (`[aws]` runtime)** | `UiaoSaasStack`: VPC · RDS PostgreSQL (IAM auth, private, encrypted) · ECS Fargate + ALB running `uiao.saas.asgi:app` · S3 evidence bucket · IAM task role. Image referenced from ECR (cloud-neutral `uiao-saas`) |
| **CDK synthesis gate** | `.github/workflows/cdk-synth.yml` | CI | n/a | `cdk synth` on every `deploy/aws/**` change — credential-free, no account. The AWS analogue of `bicep-validate` |
