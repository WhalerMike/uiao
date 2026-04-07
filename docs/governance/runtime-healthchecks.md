---
id: governance-runtime-healthchecks
title: "UIAO Governance Runtime -- Health Checks"
owner: governance-team
status: DRAFT
---

# UIAO Governance Runtime -- Health Checks

Health check specifications for all governance runtime components.
For architecture overview see `runtime-architecture.md`.

---

## 1. Component Health Endpoints

| Component | Endpoint | Method | Expected Response |
|-----------|---------|--------|-------------------|
| Webhook Handler | /health | GET | HTTP 200, body: `{"status":"ok"}` |
| Governance API | /api/health | GET | HTTP 200, body: `{"status":"ok"}` |
| Dashboard | / | GET | HTTP 200, static HTML |
| Database | pg_isready | N/A | Responds on port 5432 |

---

## 2. Health Check Cadence

- Internal health checks: every 30 seconds (docker-compose healthcheck interval).
- External uptime monitoring: every 60 seconds.
- CI health gate: run before any deployment.

---

## 3. Degraded State Definitions

| Condition | Severity | Response |
|-----------|---------|---------|
| Webhook unhealthy | Critical | Alert governance team; halt event processing |
| API unhealthy | Critical | Dashboard shows stale data banner |
| Database unhealthy | Critical | All components degrade gracefully; queue events |
| Dashboard unhealthy | Low | Governance ops shift to GitHub Issues view |

---

## 4. Recovery Procedures

**Webhook failure:** Restart container. Check `GITHUB_APP_PRIVATE_KEY` and `WEBHOOK_SECRET` env vars.

**API failure:** Restart container. Verify `DATABASE_URL` connectivity.

**Database failure:** Check disk space and pg_log. Restore from latest backup if data loss occurred.

**Dashboard failure:** Rebuild container from source. Check `API_URL` env var.

---

## 5. Acceptance Criteria

- All health endpoints respond within 2 seconds.
- Degraded state alerts fire within 5 minutes of failure.
- Recovery procedures are documented and tested quarterly.
