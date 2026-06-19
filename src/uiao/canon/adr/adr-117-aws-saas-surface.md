---
adr_id: adr-117
title: "AWS SaaS surface — multi-tenant UIAO on ECS Fargate + RDS, via AWS CDK"
status: PROPOSED
decided: 2026-06-19
deciders: Michael Stratton
updated: 2026-06-19
next_review: 2026-12-19
review_trigger: The AWS compute target changes (ECS Fargate → EKS / App Runner); private networking and the cross-cloud abstraction diverge enough to warrant a unified provider interface; a GovCloud (US) SaaS stamp is deployed and the RDS IAM endpoint / partition ARNs must be verified; per-tenant AWS stamping needs finer-grained IAM than the task-role grants; the AWS image build/push pipeline is added to CI; aws-cdk-lib majors to v3
impact: "Adds an AWS deployment surface for the multi-tenant SaaS plane, parallel to the Azure surface (ADR-096) — same uiao.saas application, different cloud substrate. IaC is AWS CDK (Python) under deploy/aws/ (VPC, RDS PostgreSQL, ECS Fargate behind an ALB, S3 evidence bucket, IAM task role). Mirrors the Azure hardening (ADR-116): passwordless Postgres via RDS IAM database authentication (uiao.saas.aws_pg_auth, reusing the SQLAlchemy do_connect token seam), private/encrypted data tier. Adds an AWS per-tenant stamp executor (uiao.saas.aws_stamp + aws_provisioners: RDS schema / S3 prefix / Secrets Manager scope), an [aws] optional-dependency extra (boto3), and a credential-free `cdk synth` CI gate. Lands aws_pg_auth.py, aws_stamp.py, aws_provisioners.py, deploy/aws/, and tests; no new core runtime dependency (boto3 + the CDK are isolated)."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-117-aws-saas-surface.html
---

# ADR-117: AWS SaaS surface — multi-tenant UIAO on ECS Fargate + RDS, via AWS CDK

## Status

**PROPOSED** — June 19, 2026

The AWS analogue of **ADR-096** (Azure SaaS architecture), carrying the same
application (`uiao.saas`) and the same hardening doctrine as **ADR-116**
(passwordless Postgres) onto a second cloud.

## Context

UIAO's multi-tenant SaaS plane (`uiao.saas`) was stood up on Azure (ADR-096):
per-request tenant resolution, a control plane, dry-run-by-default provisioning,
production-readiness (ADR-115), and passwordless deployment hardening
(ADR-116). The application layer is deliberately cloud-neutral — FastAPI +
SQLAlchemy + a thin set of cloud adapters behind protocols — but the **only
deployment target was Azure**. Customers and programs standardised on AWS had
no first-class way to run UIAO's SaaS plane, and the cloud-neutrality claim was
untested against a second substrate.

The pieces that are genuinely cloud-specific are narrow: the IaC, the
passwordless-DB token source, and the per-tenant resource stamps. Everything
else (the control plane, tenancy, quotas, audit, problem+json) is identical.

## Decision

Add an **AWS SaaS surface** parallel to (not replacing) the Azure surface,
reusing the application unchanged and mirroring the Azure hardening.

**1. IaC as AWS CDK (Python), under `deploy/aws/`.**
A single `UiaoSaasStack` (the analogue of `main.bicep`) stamps the shared
platform: a VPC, an **RDS PostgreSQL** tenant registry, an **ECS Fargate**
service behind an **Application Load Balancer** running `uiao.saas.asgi:app`, an
**S3** evidence bucket, and the **IAM task role** that binds them. CDK (Python)
was chosen over CloudFormation/Terraform to keep the IaC in the repo's primary
language and to get type-checked, testable synthesis. Configuration is by CDK
context, mirroring Bicep parameters.

**2. Passwordless Postgres via RDS IAM authentication.**
RDS IAM database authentication is enabled and the task role is granted
`rds-db:connect` for the `uiao_app` user. The app presents a short-lived IAM
token as the connection password through the **same SQLAlchemy `do_connect`
seam** introduced in ADR-116 — `uiao.saas.aws_pg_auth.RdsIamTokenProvider`
satisfies the same duck-typed provider interface as the Entra provider, and
`uiao.saas.pg_auth.apply_token_auth` serves both. No long-lived database
password reaches the task. The data tier is private (no public access) and
encrypted; the evidence bucket enforces TLS, blocks public access, and is
encrypted + versioned.

**3. AWS per-tenant stamp executor.**
`uiao.saas.aws_stamp.AwsStampExecutor` mirrors `AzureStampExecutor` across the
three isolation planes — Postgres schema (RDS), S3 key prefix, Secrets Manager
scope — reusing the cloud-neutral `Provisioner` protocol and the
`require_safe_namespace` guard. The boto3-backed provisioners
(`uiao.saas.aws_provisioners`) lazy-import behind the `[aws]` extra and are only
built when stamp execution is enabled; the state machine is fake-tested in the
`[api]` CI job.

**4. An `[aws]` extra + a credential-free `cdk synth` CI gate.**
The application's AWS runtime deps (`boto3`, plus the shared
SQLAlchemy/asyncpg) are isolated as the `[aws]` extra — same dependency
isolation as `[saas]`, so `import uiao.saas` pulls neither boto3 nor the Azure
SDKs. `.github/workflows/cdk-synth.yml` synthesizes the CDK app to
CloudFormation on every `deploy/aws/` change — no AWS account, no credentials —
the AWS analogue of the Bicep validation gate (ADR-116).

## Consequences

### Positive

- **UIAO's SaaS plane runs on AWS**, with the same control plane, tenancy,
  quotas, audit, and problem+json as Azure — the application is unchanged.
- **The cloud-neutrality claim is now tested** against a second substrate; the
  cloud-specific surface area is small and lives behind existing seams.
- **Passwordless on both clouds** through one connection seam — the
  token-as-password pattern generalised cleanly from Entra to RDS IAM.
- **Synthesis is gated** credential-free on every PR.

### Negative / trade-offs

- **Two IaC dialects** (Bicep + CDK) to maintain. Accepted: each is idiomatic
  for its cloud, and the shared application is the part that matters.
- **The CDK gate synthesizes, it does not deploy.** It proves the app produces
  valid CloudFormation, not that a deployment succeeds against real AWS state.
- **`uiao_app` DB role bootstrap is a data-plane step.** RDS IAM requires the
  `uiao_app` role (granted `rds_iam`) to exist in the database; this is a
  one-time post-deploy SQL step (documented in `deploy/aws/README.md`), not
  expressible in CDK.
- **No private networking for ingress yet** beyond the private data tier — the
  same deferral as the Azure surface (ADR-116).

### Security

- The task role is a database principal (`rds-db:connect` on `uiao_app`) and
  holds scoped S3 + Secrets Manager permissions (`uiao/*`). No standing DB
  password exists.
- RDS is not publicly accessible and is reachable only from the service
  security group; the evidence bucket blocks public access and enforces TLS.

## Boundary note

Inherits ADR-096's boundary: GCC-Moderate / commercial (ADR-033). GovCloud (US)
is not a target of this ADR; the RDS IAM endpoint and partition ARNs would need
verification for a GovCloud stamp (a review trigger).

## Implementation

- Code: `src/uiao/saas/aws_pg_auth.py`, `aws_stamp.py`, `aws_provisioners.py`;
  the shared seam generalised in `pg_auth.py` (`apply_token_auth`); wiring in
  `pg_repository.py`, `repository.py`, `settings.py`
  (`database_use_aws_iam_auth`, `aws_region`, `aws_s3_bucket`,
  `aws_secrets_prefix`).
- IaC: `deploy/aws/` (`app.py`, `uiao_saas_stack.py`, `cdk.json`,
  `requirements.txt`, `README.md`).
- CI: `.github/workflows/cdk-synth.yml`; the `[aws]` extra in `pyproject.toml`.
- Tests: `tests/test_saas_aws_pg_auth.py`, `tests/test_saas_aws_stamp.py`.
