---
adr_id: adr-118
title: "Distributed rate limiting for the SaaS data plane — a shared-store, globally-exact limiter"
status: PROPOSED
decided: 2026-06-20
deciders: Michael Stratton
updated: 2026-06-20
next_review: 2026-12-20
review_trigger: A limiting algorithm other than fixed-window is required (sliding-window / token-bucket for smoother bursts); the shared store changes from Redis to another backend; rate-limit state must be co-located with the durable audit store; per-principal (not per-tenant) limiting is needed; the data-plane middleware moves off Starlette BaseHTTPMiddleware
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-118-distributed-rate-limiting.html
impact: "Closes the globally-exact rate-limit gap named in ADR-115: adds DistributedTenantRateLimiter, which runs the same per-plan budget over a shared WindowStore (RedisWindowStore in production, InMemoryWindowStore for tests/single-node), as a drop-in behind the existing check(tenant) -> RateLimitDecision contract. The tenant middleware now awaits the decision when it is a coroutine, so the sync in-process limiter and the async distributed limiter are interchangeable with no other change. Selected by UIAO_SAAS_RATE_LIMIT_REDIS_URL; redis is a new optional [redis] extra, lazy-imported so importing uiao.saas never requires it. Cloud-neutral — the same limiter serves the Azure and AWS surfaces. Lands the limiter + InMemory/Redis stores + tests; no new core runtime dependency."
---

# ADR-118: Distributed rate limiting for the SaaS data plane — a shared-store, globally-exact limiter

## Status

**PROPOSED** — June 20, 2026

Extends **ADR-115** (SaaS production-readiness), which shipped the per-plan,
per-replica rate limiter and explicitly named a globally-exact limit as future
work.

## Context

ADR-115 added per-tenant rate limiting on the data plane: each
`TenantPlan` maps to a budget (sustained rate + burst), enforced over a fixed
window by `TenantRateLimiter`. That limiter is **in-process and per-replica** —
each Container App / ECS replica keeps its own window in memory. With *N*
replicas the effective ceiling is up to *N×* the per-plan limit.

For a courtesy/abuse guard that is the standard, acceptable shape, and ADR-115
shipped it deliberately as such. But a deployment that needs a tenant's budget
to be **exact regardless of replica count** — for contractual quotas, or to
make the limit meaningful under autoscaling — cannot get it from per-replica
state. ADR-115 named the fix ("a globally-exact limit requires a shared store
(Redis); that is a deployment swap behind the same interface") and deferred it.
This ADR is that swap.

## Decision

Add a **distributed rate limiter** that runs the *same* per-plan logic over a
*shared* store, as a drop-in behind the existing limiter contract.

**1. A `WindowStore` seam.**
A minimal async protocol — `hit(key, window_seconds) -> (count, reset_after)` —
that atomically increments a tenant's counter within the current fixed window.
Two implementations:

* `RedisWindowStore` — the production backing. Canonical fixed-window pattern:
  `INCR` the per-tenant key, `EXPIRE` on the first hit of a window, read the
  remaining `TTL`. `redis.asyncio` is **lazy-imported** behind the new
  `[redis]` extra; a client may be injected for tests.
* `InMemoryWindowStore` — an async, single-process store with an injectable
  clock, for tests and single-node deployments. It counts every hit (including
  rejected ones), matching the Redis semantics, so the two are interchangeable.

**2. `DistributedTenantRateLimiter`.**
Mirrors `TenantRateLimiter` — same per-plan quota lookup, same
`RateLimitDecision`, same `RateLimit-*` / `Retry-After` headers — but **async**,
awaiting the shared store. Unlimited plans short-circuit without touching the
store. Because the store is shared, the count is exact across every replica.

**3. An await-aware middleware, unchanged otherwise.**
The tenant-resolution middleware previously called `rate_limiter.check(tenant)`
synchronously. It now awaits the result when it is a coroutine
(`inspect.isawaitable`). That one-line change makes the sync in-process limiter
and the async distributed limiter fully interchangeable; nothing else in the
request path changes, and the existing per-replica path is untouched.

**4. Selection by configuration.**
`UIAO_SAAS_RATE_LIMIT_REDIS_URL`, when set, makes `attach_saas` build the
distributed limiter over a `RedisWindowStore`; unset, it builds the in-process
`TenantRateLimiter` exactly as before. The default is unchanged.

## Consequences

### Positive

- **Globally-exact limits** are available without changing the limiter contract,
  the plan model, or the request path — only the store and a config value.
- **Backward compatible.** The default stays the per-replica limiter; existing
  deployments and tests are unaffected. The await-aware middleware accepts both.
- **Cloud-neutral.** The same limiter serves the Azure (ADR-116) and AWS
  (ADR-117) surfaces; Redis is a managed cache on either cloud.
- **Dependency-isolated.** `redis` is an optional `[redis]` extra, lazy-imported
  — `import uiao.saas` still pulls neither it nor any cloud SDK, so the
  blocking `.[api]` CI job exercises the limiter logic via the in-memory store.

### Negative / trade-offs

- **A new moving part.** Distributed limiting adds a Redis dependency to the
  deployment; if the store is unreachable the limiter call fails rather than
  silently degrading. A fail-open fallback to the per-replica limiter is a
  possible refinement, deliberately not added here to keep the behaviour
  predictable.
- **Per-connection round-trip.** Each limited request makes a small Redis
  round-trip (a pipelined `INCR`/`TTL`). Acceptable for the governance workload;
  a token-bucket or local-cache hybrid is a listed review trigger if it matters.
- **Fixed-window, still.** The algorithm is unchanged (fixed window, not sliding
  / token-bucket), so the burst behaviour at window edges is the same — now just
  counted globally.

### Security

- Rate limiting remains an application-tier guard, not a replacement for
  platform DDoS protection. Making the limit globally exact tightens abuse
  control under autoscaling but does not change the trust model.
- Redis holds only opaque per-tenant counters keyed by tenant id under a
  namespaced prefix — no token contents, no PII.

## Boundary note

Inherits the ADR-096 boundary (GCC-Moderate / commercial). Redis is a generic
cache primitive available on both clouds; no new external endpoint or
sovereign-cloud surface is introduced.

## Implementation

- Code: `src/uiao/saas/ratelimit.py` (`WindowStore`, `InMemoryWindowStore`,
  `RedisWindowStore`, `DistributedTenantRateLimiter`); `middleware.py`
  (await-aware check); `settings.py` (`rate_limit_redis_url`); `app.py`
  (selection); the `[redis]` extra in `pyproject.toml`.
- Tests: `tests/test_saas_ratelimit_distributed.py` (algorithm + store) and a
  middleware-await integration case in `tests/test_saas_hardening.py`.
