# OrgPath for Intune & Azure Arc — Deployment Readiness Memo

> **Status:** DRAFT assessment — **not canon.** This memo lives in `inbox/`
> (draft staging per AGENTS.md). Promotion to canon requires a `UIAO_NNN`
> allocation in `document-registry.yaml` and, for any doctrinal claim, an
> ADR under `src/uiao/canon/adr/` plus governance-board review.
>
> **Scope of question:** *"If an agency decided to deploy OrgPath for Intune
> and Azure Arc, how ready is the code?"*
>
> **Date:** 2026-06-05 · **Boundary assumed:** GCC-Moderate (commercial
> infrastructure, FedRAMP Moderate authorization, per ADR-033).

## 1. Bottom line

| Surface | Verdict | Confidence |
|---|---|---|
| OrgPath core (Codebook, drift engine, governance runtime) | **Ready** — complete, tested, dry-run-safe | High |
| AD → OrgPath assessment (facet derivation, LDAP + export) | **Ready** | High |
| Arc / Intune **readiness scanning** (which servers/clients qualify) | **Ready** | High |
| Read-only governance UI + REST API + Windows/IIS deploy surface | **Ready** | High |
| OrgPath → **Intune** device-attribute writeback (Graph plane) | **Ready in GCC-Moderate** after credential setup | Medium |
| OrgPath → **Arc** tag writeback (ARM plane) | **Was blocked** (auth); **remediated by this PR** | Medium |
| Intune **profile/compliance authoring** adapter | **Not ready** — reserved slot, no implementation | High |
| **Azure Policy for Arc** (server-side enforcement/remediation) | **Not ready** — reserved slot, no implementation | High |

**Headline:** the *assessment, planning, drift-detection, and read-only
governance* layers are genuinely production-grade. The *live write-back* is
where readiness drops. As found, **Intune (Entra-device) writes can work in
a GCC-Moderate boundary** with one credential setup, but **Arc/ARM writes
could not authenticate against a live tenant** — they reused the Graph
transport, so ARM received a Graph-audience token and would return HTTP 401.
**This PR fixes that specific blocker.** Beyond it, *policy/profile
authoring* on both planes remains reserved (unbuilt) doctrine, and OrgPath
itself has **zero production adopters** — it is ratified Tier-3+ doctrine,
never run at tenant scale (per UIAO_151 / ADR-078).

## 2. Methodology

Direct source review plus three fan-out code surveys (Intune surface, Arc
surface, OrgPath runtime maturity). Findings below cite concrete files and
line references. Claims about live-write behavior were verified against the
actual transport/token code, not docstrings — one survey's optimistic
"ARM writes are production-ready" conclusion was **corrected** after reading
`_graph_clouds.py` and `entra_token.py`, which prove no ARM base or ARM
token audience existed on the write path.

## 3. What is solid (deploy-ready today)

| Capability | State | Evidence |
|---|---|---|
| OrgPath Codebook (15-facet Model C) | Complete, schema-validated | `UIAO_151`, `modernization/orgtree/codebook.py` |
| Drift engine (5 drift classes, per-facet) | Complete | `governance/drift_engine.py` |
| Governance runtime (6-phase loop, dry-run default) | Complete | `governance/orgpath_runtime.py` |
| AD → facet assessment (live LDAP + export) | Complete, pure/offline-testable | `modernization/orgtree/ad_assign.py`, `ad_mapping.py` |
| Arc readiness verdicts (READY / NEEDS_OS_UPGRADE / NEEDS_NETWORK_EGRESS / INELIGIBLE / NOT_SERVER) | Complete, broad test suite | `adapters/modernization/active_directory/arc_readiness.py` |
| Intune readiness verdicts (Windows OS / TPM / HVCI gates) | Complete | `adapters/modernization/active_directory/intune_readiness.py` |
| Read-only Intune compliance telemetry | Complete (observes, never mutates) | `adapters/intune_adapter.py` |
| Read-only OrgPath web console + REST API | Complete (no-write by design, ADR-084 §C7) | `api/web/console.py`, `api/routes/orgpath.py` |
| Windows/IIS deployment surface | Present | `deploy/windows-server/run.py`, `web.config` |

For *"assess our AD fleet, tell us which servers are Arc-eligible and which
clients are Intune-ready, derive everyone's OrgPath, classify drift, and
show it in a dashboard"* — this is ready to pilot now, entirely read-only.

## 4. Intune — write path

- The OrgPath → Intune **device extension-attribute writeback**
  (`onPremisesExtensionAttributes` via Microsoft Graph) is real:
  planner + dual-transport adapter (`adapters/entra_device_orgpath.py`)
  + a concrete httpx/MSAL `GraphTransport`. In a **GCC-Moderate** boundary
  (commercial Graph per ADR-033) the token audience is correct, so this
  path can go live once `UIAO_ENTRA_*` app credentials are set and the
  operator passes `uiao orgtree assess --target-type device --write
  --no-dry-run`.
- **Profile / compliance-policy authoring** — assigning Intune
  configuration profiles and compliance policies to OrgTree dynamic groups
  (the workflow `UIAO_011` describes) — is governed by an adapter that is
  **`status: reserved / phase: phase-planning`** in both
  `adapter-registry.yaml` and `modernization-registry.yaml`. The
  `EntraPolicyTargetAdapter` code exists and plans correctly, but it is not
  an activated, ADR-ratified adapter. You can read Intune state and target
  *existing* policies by OrgPath; you cannot author Intune profiles through
  UIAO yet.
- **Platform coverage caveat:** Intune readiness assessment is **Windows
  only**. macOS / iOS / Android are doctrine (ADR-071) with no adapter code.

## 5. Azure Arc — write path (the blocker, and its fix)

**As found:**

1. The OrgPath → Arc writeback *plans* ARM tag PATCHes correctly
   (`device_orgpath.py`, disposition `ARC-SERVER` → `tags.<Facet>`), and the
   dispatcher (`entra_device_orgpath.py`) emits the right ARM call shape
   (`PATCH {resource}?api-version=2023-03-15-preview`, body `{"tags": {…}}`).
2. **But there was no ARM transport.** The CLI wired it as
   `arm_transport = graph_transport` with the comment *"ARM writes share the
   credential path."* That is incorrect: `resolve_graph_base()` only ever
   returns a **Graph** host (`graph.microsoft.com`), never
   `management.azure.com`, and `EntraTokenProvider` **hardcoded** the Graph
   token scope (`https://graph.microsoft.com/.default`).
3. **Net effect:** a live Arc write would send a **Graph-audience bearer
   token to Azure Resource Manager**, which ARM rejects with **HTTP 401
   (invalid audience)**. The existing tests passed only because they inject
   a fake recorder transport — no test exercised a real ARM token.
4. The same root cause broke **sovereign-cloud Graph writes** (GCC-High /
   DoD): the token provider ignored `cloud` and always used the commercial
   Graph audience + commercial login authority. (Harmless for GCC-Moderate,
   which *is* commercial Graph — but a latent 401 for Government tenants.)

Separately, **Azure Policy for Arc** (the server-side governance/enforcement
plane — `UIAO_010`) is a **`status: reserved`** slot in
`modernization-registry.yaml` with **no implementation**.

**Remediated by this PR (see §7):** a real `ArmTransport` (ARM base + ARM
`.default` audience, cloud-aware) plus a cloud-/audience-aware
`EntraTokenProvider`. After this change, Arc tag writes authenticate
correctly; sovereign-cloud Graph writes do too. *Policy authoring* on both
planes remains reserved and out of scope for this change.

## 6. The systemic caveat

From the project's own canon (`UIAO_151`, `ADR-078`): *"UIAO has no
production adopters at this version's ratification."* OrgPath Model C is
**Tier-3+ doctrine** — architecturally clean, internally tested, but never
proven against a real tenant at scale. The starter facet enumerations are
federal-IT defaults that every tenant must tune (Region, Department,
Division, Role, CostCenter, Classification, ClearanceLevel, AccountType).
Phase 8 (PowerShell tooling), cross-surface per-facet device equality
checks, and Codebook hot-reload are explicitly deferred to future ADRs.

A second data-shaping prerequisite for live Arc writes: the device record's
identifier (`device_id` / `target`) must be the **ARM resource ID** of the
Arc machine (e.g. `/subscriptions/…/providers/Microsoft.HybridCompute/
machines/{name}`), not a bare hostname. The new `ArmTransport` joins a
resource-relative path onto the ARM base and passes absolute URLs verbatim,
but it does not synthesize resource IDs — the assessment/export pipeline
must carry them.

## 7. What this PR changes

This memo ships alongside a code change that closes the Arc auth blocker:

- **`adapters/_arm_clouds.py`** (new) — `ARM_ENDPOINTS`, `resolve_arm_base()`,
  `arm_token_scope()`. Cloud → ARM host + ARM `.default` audience. Mirrors
  `_graph_clouds.py`. Azure Government (`gcc-high`, `dod`) →
  `management.usgovcloudapi.net`; commercial / GCC-Moderate →
  `management.azure.com`.
- **`adapters/arm_transport.py`** (new) — `ArmTransport`, the ARM-plane
  counterpart to `GraphTransport`: httpx + MSAL, ARM-audience token,
  resource-relative or absolute paths.
- **`api/auth/entra_token.py`** — `EntraTokenProvider` gains
  `scopes=` (token audience) and `authority_base=` / cloud-aware
  `from_environment(cloud=…)`. Defaults preserve the old commercial-Graph
  behavior, so existing callers are unaffected.
- **`adapters/graph_transport.py`** — `from_environment(cloud=…)` now passes
  the cloud-correct Graph audience + authority (fixes the latent
  sovereign-cloud 401).
- **`cli/orgtree.py`** — the device-write path builds a real
  `ArmTransport` instead of reusing the Graph transport.
- **Tests** — `tests/test_arm_clouds.py`, `tests/test_arm_transport.py`,
  `tests/test_entra_token_scope.py` (32 new tests). Full affected suite
  green; mypy clean.

What this PR **does not** do: activate the reserved Intune-authoring or
`azure-policy-arc` adapters (each needs a per-adapter ADR), add non-Windows
Intune readiness, or run anything against a live tenant.

## 8. Recommendation

1. **Greenlight a read-only / assessment pilot now** — Arc-readiness +
   Intune-readiness + OrgPath derivation + dry-run governance dashboard.
   This is solid and low-risk.
2. **Treat Intune device-attribute writeback as "one credential setup + a
   review away"** in GCC-Moderate. Pilot on a 5–10 % device population with
   `--write` (dry-run) first, then `--no-dry-run` behind an approval gate.
3. **Treat Arc live writes as "newly unblocked, needs a live-tenant
   smoke test"** — the transport now authenticates correctly, but it has
   not been exercised against a real ARM endpoint; validate with a single
   Arc machine before any fleet rollout, and ensure the app registration
   holds the right Azure RBAC role (e.g. *Tags Contributor*) on the target
   resources (ARM authz is role-based, not Graph application-permission
   based).
4. **Do not commit to dates for Intune profile authoring or Azure Policy
   for Arc** — those are reserved adapters; budget the per-adapter ADR +
   implementation work before promising server-side enforcement.

## 9. Provenance / promotion path

This memo is an assessment, not derived canon, so it stays in `inbox/`. To
canonize: allocate a `UIAO_NNN` in `document-registry.yaml`, file an ADR for
any doctrinal claim (e.g. "ARM is the second device-plane transport and gets
its own audience"), and route through governance-board review per AGENTS.md
invariant I5.
