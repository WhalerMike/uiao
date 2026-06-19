---
adr_id: adr-116
title: "Azure SaaS deployment hardening — passwordless Postgres and an IaC validation gate"
status: PROPOSED
decided: 2026-06-19
deciders: Michael Stratton
updated: 2026-06-19
next_review: 2026-12-19
review_trigger: Private networking lands (VNet injection + private endpoints + public-access disable) and supersedes the public-network firewall rule; the compute target changes off Container Apps (ADR-096 trigger); a sovereign-cloud (GCC-High / DoD) SaaS stamp is deployed and the OSSRDBMS token audience must be verified against the real US-Gov endpoint; managed-identity Postgres roles need finer-grained grants than the Entra-administrator binding; a credentialed what-if / deployment-validation step is added to CI
impact: "Hardens the ADR-096 Azure SaaS deployment in two cloud-portable ways. (1) Passwordless Postgres: the Container App's managed identity is bound as the PostgreSQL Flexible Server's Entra administrator, password auth is disabled, and the app authenticates with a short-lived OSSRDBMS access token presented as the connection password (uiao.saas.pg_auth + a SQLAlchemy do_connect listener). This removes the single highest-value long-lived secret (the DB password) from Bicep, the deploy workflow, and Container Apps secrets. (2) A credential-free Bicep validation CI gate (.github/workflows/bicep-validate.yml) compiles the whole template graph and validates the parameter file on every deploy/azure change. Private networking (VNet + private endpoints + public-access disable) is explicitly deferred to a follow-up that can be deploy-validated. Lands pg_auth.py + test_saas_pg_auth.py; no new core runtime dependency (azure-identity stays behind the [saas] extra, lazy-imported)."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-116-azure-saas-deployment-hardening.html
---

# ADR-116: Azure SaaS deployment hardening — passwordless Postgres and an IaC validation gate

## Status

**PROPOSED** — June 19, 2026

Extends **ADR-096** (Azure SaaS architecture) and complements **ADR-115** (SaaS
production-readiness). ADR-115 hardened the *application*; this ADR hardens the
*deployment*.

## Context

ADR-096 stood up the Azure SaaS deployment: a PostgreSQL Flexible Server tenant
registry, a user-assigned managed identity, Key Vault, Storage, and the
Container App, all stamped by Bicep under `deploy/azure/`. Two deployment-layer
weaknesses remained — both cloud-portable concerns, independent of any feature:

1. **A long-lived database password.** The Postgres admin password was a
   `@secure()` Bicep parameter, composed into a DSN in `main.bicep`, injected
   from a `PG_ADMIN_PASSWORD` CI secret, and stored as a Container Apps secret.
   It was the single highest-value secret in the deployment: it never rotated
   automatically, sat in three places (CI, the deployment, the app's secret
   store), and a leak granted standing database access. The managed identity
   already existed and already authenticated to Graph/ARM — but the database
   alone still used a password.

2. **No template validation before deploy.** Bicep reached
   `az deployment group create` unchecked. A malformed template, a bad resource
   API shape, or a stale parameter reference would only surface mid-deploy,
   after credentials, against a live resource group. There was no cheap,
   credential-free gate to catch template defects on a PR.

## Decision

Two changes, both cloud-portable and verifiable without a live subscription.

**1. Passwordless Postgres via Microsoft Entra (managed identity).**
Azure Database for PostgreSQL Flexible Server accepts a short-lived Entra
access token *as the connection password*. We:

* Bind the SaaS managed identity as the server's **Entra administrator**
  (`flexibleServers/administrators`) and **disable password auth**
  (`authConfig.passwordAuth: 'Disabled'`, `activeDirectoryAuth: 'Enabled'`).
  The managed identity becomes the only way in; no admin login or password is
  provisioned. The `pgAdminPassword` parameter, the `PG_ADMIN_PASSWORD` CI
  secret, and the password-bearing DSN are all deleted.
* Add :mod:`uiao.saas.pg_auth`: an `EntraPostgresTokenProvider` that caches an
  OSSRDBMS token and refreshes it before expiry, plus an `apply_entra_auth`
  helper that injects a fresh token as the connection password on every new
  asyncpg connection via a SQLAlchemy `do_connect` listener. The token
  *acquirer* is injectable, so the cache/refresh logic is unit-tested with a
  fake credential and clock; the real `DefaultAzureCredential` and SQLAlchemy
  are **lazy-imported**, keeping the module free of the `[saas]` extra at
  import time (same dependency-isolation doctrine as the rest of `uiao.saas`).
* The token audience is sovereign-cloud aware (`ossrdbms_scope_for`): commercial
  / GCC-Moderate use `ossrdbms-aad.database.windows.net`; GCC-High / DoD use
  `ossrdbms-aad.database.usgovcloudapi.net`.
* Wire it through settings (`database_use_entra_auth`, `database_entra_user`),
  `build_repository`, and the Bicep (`UIAO_SAAS_DATABASE_USE_ENTRA_AUTH=true`,
  `UIAO_SAAS_DATABASE_ENTRA_USER=<identity name>`).

**2. A credential-free Bicep validation CI gate.**
`.github/workflows/bicep-validate.yml` runs on every change under
`deploy/azure/`: it compiles the entire template graph (`az bicep build` on
`main.bicep`, which transitively pulls every module) and validates the example
parameter file (`az bicep build-params`). It needs no Azure login, no
subscription, and no deployment — a pure compile + lint — so it runs on any PR
and catches malformed templates, bad API shapes, and stale parameter references
before they reach a live deploy. A credentialed `what-if` preview remains a
deploy-time step in `azure-saas-deploy.yml`.

## Consequences

### Positive

- **No long-lived database secret.** The DB password is gone from CI, the
  deployment, and the app's secret store; access is a short-lived,
  auto-refreshing token bound to the managed identity.
- **Tighter blast radius.** A leaked Container Apps secret or CI secret no
  longer yields standing database access.
- **Template defects caught on PRs**, credential-free, including retroactive
  validation of the existing modules.
- **Cloud-portable pattern.** Token-as-password is the same shape AWS IAM
  database authentication uses (ADR for the AWS surface pending), so the
  `pg_auth` seam generalises.

### Negative / trade-offs

- **Token plumbing.** Connections now depend on Entra token acquisition; a
  credential/identity misconfiguration surfaces as a connection failure (caught
  by the `/readyz` probe from ADR-115) rather than a password error.
- **Public network access is unchanged.** This ADR does not add private
  networking; the server still permits Azure-services egress via the firewall
  rule. Disabling public access is coupled with VNet injection + private
  endpoints and is deferred (see below) because it cannot be deploy-validated
  in this change.
- **The CI gate compiles, it does not deploy.** It proves the template is
  well-formed, not that a deployment succeeds against real Azure state; the
  `what-if` step remains the deploy-time check.

### Security

- The managed identity is now a database administrator. That is the intended
  trust boundary (it is already the governance principal), but it means the
  identity's blast radius includes full DB access — finer-grained roles are a
  listed review trigger.
- Token audience selection is sovereign-cloud aware to avoid issuing a
  commercial-audience token against a US-Gov endpoint.

## Deferred (explicit follow-up)

**Private networking** — VNet injection for the Container Apps environment,
private endpoints for Postgres / Storage / Key Vault, private DNS zones, and
`publicNetworkAccess: 'Disabled'`. This is the natural next hardening step but
is coupled with disabling public access (which would break connectivity without
the VNet) and requires deploy-time validation that the credential-free CI gate
cannot provide. It is scoped to its own ADR + PR so it can be stood up and
verified against a real resource group rather than shipped blind.

## Boundary note

Inherits ADR-096's boundary: GCC-Moderate / commercial (ADR-033). The OSSRDBMS
US-Gov token audience is wired for GCC-High / DoD but is unverified until a
sovereign stamp is deployed (a review trigger).

## Implementation

- Code: `src/uiao/saas/pg_auth.py`; wiring in `pg_repository.py`,
  `repository.py`, `settings.py`.
- IaC: `deploy/azure/bicep/modules/postgres.bicep` (Entra admin + passwordless),
  `main.bicep` / `main.bicepparam` (drop password, wire identity),
  `modules/containerapp.bicep` (Entra-auth env), `azure-saas-deploy.yml`
  (drop the password secret).
- CI: `.github/workflows/bicep-validate.yml`.
- Tests: `tests/test_saas_pg_auth.py`.
