---
adr_id: adr-096
title: "Azure SaaS architecture — multi-tenant UIAO on Container Apps"
status: PROPOSED
decided: 2026-06-07
deciders: Michael Stratton
updated: 2026-06-07
next_review: 2026-12-07
review_trigger: The compute target changes (Container Apps → App Service / AKS); a customer requires single-tenant deployment-per-tenant isolation that the shared data plane cannot satisfy; the inbound auth model changes (e.g. CAE / continuous access evaluation); a sovereign-cloud (GCC-High / DoD) SaaS offering is stood up; the tenant registry outgrows a single PostgreSQL Flexible Server
impact: "Introduces a multi-tenant SaaS deployment surface for UIAO on Azure Container Apps, parallel to (not replacing) the single-tenant Windows/IIS surface. Adds the uiao.saas package (tenant registry, per-request tenant resolution, control-plane onboarding API, provisioning service), a [saas] optional-dependency extra, a container image and Bicep IaC under deploy/azure/, and a manual-dispatch-only deploy workflow. Establishes per-request multi-tenancy plus a control-plane stamp pattern. No change to the CLI or the existing data-plane routes."
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-096-azure-saas-architecture.html
---

# ADR-096: Azure SaaS architecture — multi-tenant UIAO on Container Apps

## Status

**PROPOSED** — June 7, 2026

## Context

UIAO ships today as a single-tenant service: the `uiao.api` FastAPI app
(`deploy/windows-server/`) runs behind IIS on Windows Server, authenticates
inbound callers via Kerberos/Negotiate, and acquires a *single* Microsoft
Graph application token via `EntraTokenProvider` for *one* tenant. That model
fits an agency running UIAO inside its own boundary.

To offer UIAO as a **SaaS** — where many customer Entra tenants are governed
by one operated service — three things are missing:

1. **Inbound multi-tenancy.** Requests arrive with Entra access tokens minted
   by *different* customer tenants. The service must verify each token
   against the issuing tenant's keys, identify the tenant (`tid` claim), and
   isolate that tenant's data.
2. **Per-tenant outbound identity.** Graph / ARM calls must run as *that
   customer's* consented application identity, not a single hard-wired app.
   The cloud-resolution plumbing already exists
   (`_graph_clouds`, `_arm_clouds`, `EntraTokenProvider`); what is missing is
   the per-tenant binding.
3. **A control plane.** Onboarding (admin consent), lifecycle
   (suspend/resume/deprovision), and per-tenant resource stamping.

The existing IIS surface cannot host this: Kerberos inbound auth is
single-realm, the app token is single-tenant, and Windows/IIS is a poor fit
for elastic, scale-to-zero, container-native SaaS.

## Decision

**1. Azure Container Apps is the SaaS compute target.**
It gives each revision a **user-assigned managed identity** (the governance
principal the Graph/ARM transports already expect), managed ingress + TLS,
revision-based blue/green, and KEDA scale-to-zero for bursty governance
passes. It is lighter to operate than AKS and more elastic than App Service.
The Windows/IIS surface is retained for single-tenant/on-prem customers; the
SaaS surface is additive.

**2. Per-request multi-tenancy + a control-plane stamp pattern (both).**
The data plane resolves the tenant *per request* from the validated `tid`
claim (`TenantResolutionMiddleware`) and binds a `TenantContext` for the
duration of the request. The control plane (`/control/v1`) onboards tenants
and orchestrates per-tenant stamps (DB schema, Blob prefix, Key Vault scope)
via a `ProvisioningService`. This is the "full SaaS" shape: one shared,
elastically-scaled data plane with strong per-tenant data-namespace
isolation, plus a control plane that can stamp dedicated resources where a
customer's compliance posture requires it.

**3. PostgreSQL Flexible Server is the durable tenant registry + state.**
The tenant registry (`saas_tenants`) and per-tenant evidence state live in
Postgres; evidence bundles live in Blob Storage; per-tenant secrets live in
Key Vault. The `data_namespace` derived from each tenant GUID is the
isolation handle (schema/row scoping, Blob prefix, secret scope).

**4. Dependency isolation behind a `[saas]` extra.**
The blocking CI test job installs only `.[api]`. Therefore everything
importable from `uiao.saas`'s top level depends only on the stdlib,
`pydantic`, and FastAPI/Starlette; the Postgres repository and the JWKS
signature verifier are lazy-imported and declared under a new `[saas]`
optional-dependency extra — exactly mirroring how `uiao.api` is gated behind
`[api]`. CI stays green without pulling SQLAlchemy / asyncpg / Azure SDKs
into the test matrix.

**5. Dry-run-by-default provisioning.**
Following the OrgPath-runtime doctrine, the `ProvisioningService` plans the
Azure-resource side of onboarding through an injected `StampExecutor`. The
default `NoOpStampExecutor` only *plans* — the control plane is safe to
exercise in CI and locally. A concrete executor is injected for production.

## Consequences

### Positive

- A real SaaS path with no rewrite of the governance core — `uiao.saas`
  composes onto the existing `uiao.api` app via `attach_saas()`.
- Managed-identity token acquisition removes secret sprawl; the governance
  principal is an Azure identity, not a stored client secret.
- The change is governance-clean: a new package, a new extra, a new deploy
  directory, and a dormant workflow. No CLI or existing-route changes.

### Negative / trade-offs

- A shared data plane means tenant isolation is enforced in code
  (middleware + data namespace), not by physical separation. Customers
  requiring hard isolation use the control-plane stamp to provision
  dedicated resources — heavier ops.
- Adds operational surface (Postgres, Key Vault, Blob, ACR, Container Apps)
  that must be monitored and patched.
- Introduces the `[saas]` dependency set (SQLAlchemy, asyncpg, PyJWT, Azure
  SDKs) for anyone running the SaaS plane.

### Security

- Inbound tokens are signature-verified against the issuing tenant's JWKS
  (RS256) in production; `insecure_allow_unsigned` is dev/test only and
  defaults off.
- The control plane requires a publisher-tenant token carrying the
  `UIAO.SaaS.Admin` app role; the data plane rejects non-onboarded and
  non-active tenants with 403.
- Secrets (DB DSN, per-tenant client secrets) live in Key Vault / Container
  Apps secrets, never in the image or git.

## Boundary note

This ADR's deployment is **GCC-Moderate / commercial** (per ADR-033,
"commercial" infrastructure also serves GCC-Moderate). A sovereign-cloud
(GCC-High / DoD) SaaS offering is explicitly a future decision and a listed
review trigger; the `UIAO_SAAS_CLOUD` setting and the issuer/Graph/ARM
resolution already account for sovereign endpoints, but no sovereign SaaS is
stood up by this ADR.

## Implementation

- Package: `src/uiao/saas/` (`tenant`, `repository`, `pg_repository`,
  `auth`, `context`, `middleware`, `provisioning`, `control_plane`, `app`,
  `asgi`).
- Extra: `[saas]` in `pyproject.toml`.
- Container + IaC: `deploy/azure/` (Dockerfile, Bicep modules, README).
- CI: `.github/workflows/azure-saas-deploy.yml` (manual-dispatch only).
- Tests: `tests/test_saas_*.py`.
