---
id: governance-runtime-deploy
title: "UIAO Governance Runtime -- Deployment Guide"
owner: governance-team
status: DRAFT
---

# UIAO Governance Runtime -- Deployment Guide

Operational deployment procedures for the governance runtime.
For architecture see `runtime-architecture.md`.
For health checks see `runtime-healthchecks.md`.

---

## 1. Prerequisites

- Docker 24+ and Docker Compose 2.20+
- Node.js 20+ (for local CLI)
- Access to `WhalerMike/uiao-docs` repository
- GitHub App credentials (APP_ID, PRIVATE_KEY, INSTALLATION_TOKEN, WEBHOOK_SECRET)
- PostgreSQL 15+ (included in docker-compose stack)

---

## 2. Environment Variables

| Variable | Description |
|---------|-------------|
| `GITHUB_APP_ID` | GitHub App ID |
| `GITHUB_APP_PRIVATE_KEY` | PEM-encoded private key |
| `WEBHOOK_SECRET` | HMAC-SHA256 webhook secret |
| `GITHUB_INSTALLATION_TOKEN` | Installation access token |
| `GITHUB_TOKEN` | PAT for API access |
| `GITHUB_OWNER` | Repository owner (WhalerMike) |
| `GITHUB_REPO` | Repository name (uiao-docs) |
| `DATABASE_URL` | PostgreSQL connection string |
| `PORT` | Service port (defaults: webhook=3001, api=4000) |

---

## 3. Local Deployment (docker-compose)

```bash
# Clone and configure
cd governance-runtime
cp .env.example .env
# Fill in all required env vars in .env

# Start stack
docker compose pull
docker compose build
docker compose up -d

# Verify
docker compose ps
curl http://localhost:3001/health
curl http://localhost:4000/api/health
```

---

## 4. Production Deployment (Helm)

```bash
# Create secrets
kubectl create secret generic uiao-secrets \
  --from-env-file=.env

# Install chart
helm install uiao-governance ./helm/uiao-governance \
  --set ingress.host=governance.example.com

# Verify
kubectl get pods -l app=uiao-governance
kubectl port-forward svc/uiao-governance 4000:4000
curl http://localhost:4000/api/health
```

---

## 5. Database Initialization

On first deployment, run the schema migration:

```bash
psql $DATABASE_URL -f db/schema.sql
```

---

## 6. Post-Deployment Validation

1. Verify all health endpoints respond (see `runtime-healthchecks.md`).
2. Create a test drift issue with label `metadata-drift`.
3. Confirm webhook applies `needs-owner-ack` label within 60 seconds.
4. Confirm API returns updated corpus_index.
5. Confirm dashboard reflects state change.

---

## 7. Rollback Procedure

```bash
# docker-compose
docker compose down
docker compose up -d --scale api=0
# Restore previous image tag in docker-compose.yml
docker compose up -d

# Helm
helm rollback uiao-governance
```

---

## 8. Acceptance Criteria

- All containers pass health checks within 60 seconds of startup.
- Webhook receives and processes test event within 60 seconds.
- Database schema applied without errors.
- Rollback procedure documented and tested quarterly.
