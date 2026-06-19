---
adr_id: adr-115
title: "SaaS production-readiness — quotas, rate limiting, audit trail, and problem+json"
status: PROPOSED
decided: 2026-06-19
deciders: Michael Stratton
updated: 2026-06-19
next_review: 2026-12-19
review_trigger: A globally-exact (cross-replica) rate limit is required and a shared store (Redis) is introduced; the audit trail must become durable / tamper-evident and moves to Postgres or an append-only evidence bundle; per-plan quotas gain billing-metering semantics; a customer SLA requires a different fairness model (per-principal rather than per-tenant); the data plane adopts a different error envelope than RFC 9457
impact: "Adds a cloud-agnostic production-readiness layer to the uiao.saas multi-tenant runtime introduced in ADR-096: per-plan service quotas (uiao.saas.quotas), best-effort per-tenant request-rate limiting (uiao.saas.ratelimit), an append-only control-plane audit trail (uiao.saas.audit) surfaced at GET /control/v1/audit, RFC 9457 problem+json error documents across both planes (uiao.saas.errors), and a real readiness probe (/readyz) that confirms the tenant registry is reachable. No new runtime dependency — the layer is stdlib + pydantic + Starlette, so the blocking CI job (.[api]) covers it. The Azure Container App readiness probe is repointed from /healthz to /readyz."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-115-saas-production-readiness.html
---

# ADR-115: SaaS production-readiness — quotas, rate limiting, audit trail, and problem+json

## Status

**PROPOSED** — June 19, 2026

## Context

ADR-096 stood up the multi-tenant SaaS runtime (`uiao.saas`): per-request
tenant resolution, a control plane for onboarding/lifecycle, and dry-run-by-
default provisioning, deployed on Azure Container Apps. That established the
*shape* of the SaaS, but four gaps stood between it and a shippable service —
all of them **cloud-agnostic** (they belong to the SaaS core, not to Azure or
to a future AWS surface):

1. **No fairness control.** One tenant could exhaust the shared data plane's
   capacity, starving the others. A multi-tenant service needs a per-tenant
   request budget tied to the commercial plan the tenant pays for.
2. **No self-evidence.** A governance substrate that cannot answer "who
   onboarded / suspended / deprovisioned which tenant, and when" fails its own
   audit doctrine. Control-plane lifecycle actions left no trail.
3. **Inconsistent errors.** The data-plane middleware emitted an ad-hoc
   `{"error", "message"}` body while the control plane emitted FastAPI's
   `{"detail": …}`. Clients had to special-case two shapes, and neither was a
   recognised standard.
4. **A fake readiness probe.** The Container App's readiness probe pointed at
   `/healthz`, a static liveness check — it returned 200 even when the tenant
   registry (Postgres) was unreachable, so a broken revision could be added to
   the ingress pool and serve 5xx to live traffic.

## Decision

Add a **production-readiness layer** to `uiao.saas`. It is deliberately
dependency-free (stdlib + `pydantic` + Starlette, the `[api]` extra) so the
blocking CI test job covers every line, and so it ships identically on any
compute target — Azure Container Apps today, AWS ECS/Fargate later (ADR for
that surface pending). Five decisions:

**1. Per-plan quotas as pure data (`uiao.saas.quotas`).**
Each `TenantPlan` (trial / standard / enterprise / gov) maps to a `PlanQuota`
with a sustained `requests_per_minute`, a `burst` head-room, and advisory caps
(`max_concurrent_passes`, `max_evidence_bundles`). The defaults are
conservative and monotonic (trial ≪ standard ≪ enterprise = gov). A deployment
overrides the table without code changes. An unknown plan falls back to the
*trial* (most restrictive) ceilings — fail-closed, never unlimited.

**2. Best-effort, per-replica rate limiting (`uiao.saas.ratelimit`).**
A fixed-window counter enforces each tenant's `window_limit` (rate + burst)
over a 60-second window, keyed by tenant id. It is **in-memory and per-
replica**: with *N* replicas the effective ceiling is up to *N×* the per-plan
limit. This is the standard L7 courtesy/abuse guard; a globally-exact limit
requires a shared store (Redis) and is an explicit, deferred review trigger —
the swap sits behind the same `TenantRateLimiter` interface. The window clock
is injectable, so the logic is deterministic under test. Blocked requests
return `429` with `Retry-After` and `RateLimit-*` headers; admitted requests
carry the same `RateLimit-*` headers so clients can self-throttle.

**3. Append-only audit trail (`uiao.saas.audit`).**
Every control-plane lifecycle action (onboard / suspend / resume /
deprovision) — success *and* rejection — is recorded as an immutable
`AuditEvent` (action, tenant, actor = publisher-admin subject, outcome,
detail, timestamp) and exposed to publisher admins at
`GET /control/v1/audit`. The default `InMemoryAuditSink` is a bounded ring
buffer; a durable, tamper-evident sink (Postgres / append-only evidence
bundle) is a drop-in behind the `AuditSink` protocol and is a listed review
trigger. Auditing the substrate's own governance actions is the same doctrine
the substrate imposes on the systems it governs.

**4. RFC 9457 problem+json everywhere (`uiao.saas.errors`).**
Both planes emit `application/problem+json` documents with the standard
members (`type`, `title`, `status`, `detail`, `instance`) plus two UIAO
extensions: a stable machine `error` code (clients branch on this, never on
prose) and the resolved `tenant`. The data-plane middleware builds the
response directly (it runs below FastAPI's exception handling); a registered
`HTTPException` handler renders control-plane and dependency errors in the
identical shape. The pre-existing machine codes (`tenant_not_onboarded`,
`tenant_not_active`, …) are preserved as the `error` extension, so existing
clients keep working.

**5. A real readiness probe (`/readyz`).**
`/readyz` calls `TenantRepository.ping()` — a cheap `SELECT 1` against the
Postgres registry (trivially true for the in-memory store) — and returns
`503 degraded` when the registry is unreachable. The Azure Container App's
readiness probe is repointed from `/healthz` to `/readyz`, so a revision that
cannot reach its registry is withheld from the ingress pool. `/healthz`
remains the static liveness probe.

## Consequences

### Positive

- A noisy or compromised tenant cannot monopolise the shared data plane; the
  budget tracks the plan the customer pays for.
- The substrate now keeps evidence about its *own* control-plane decisions —
  closing a self-governance gap.
- One error dialect (RFC 9457) across both planes; clients branch on a stable
  code, not on a status line or prose.
- Broken revisions are kept out of rotation instead of serving 5xx.
- Zero new runtime dependencies; the blocking `.[api]` CI job exercises the
  whole layer.

### Negative / trade-offs

- The rate limit is per-replica, not global — acceptable as an abuse guard but
  not a hard contractual ceiling until a shared store is added.
- The default audit sink is in-memory: it survives neither a restart nor a
  scale-in. Durable auditing is deferred to the follow-up sink.
- Per-plan defaults are guesses until real traffic informs them; they are
  override-friendly precisely because they will need tuning.

### Security

- Rate limiting is a denial-of-service mitigation at the application tier; it
  does not replace platform-level (WAF / front-door) protection.
- The audit endpoint is gated behind the same publisher-admin role
  (`UIAO.SaaS.Admin`) as the rest of the control plane.
- Problem documents deliberately carry only the tenant id and a machine code —
  no token contents, no internal stack detail — so the standardised envelope
  does not become an information-disclosure vector.

## Boundary note

This layer is cloud-agnostic and inherits ADR-096's boundary: GCC-Moderate /
commercial (per ADR-033). It introduces no new cloud endpoints and no
sovereign-cloud surface.

## Implementation

- Modules: `src/uiao/saas/quotas.py`, `ratelimit.py`, `audit.py`, `errors.py`.
- Wiring: `settings.py` (`rate_limiting_enabled`, `rate_limit_window_seconds`,
  `audit_enabled`), `middleware.py` (rate-limit + problem+json),
  `provisioning.py` (audit hooks), `control_plane.py`
  (`GET /control/v1/audit`), `app.py` (problem handlers, `/readyz`),
  `repository.py` / `pg_repository.py` (`ping()`).
- IaC: `deploy/azure/bicep/modules/containerapp.bicep` readiness probe →
  `/readyz`.
- Tests: `tests/test_saas_quotas.py`, `test_saas_audit.py`,
  `test_saas_hardening.py`.
