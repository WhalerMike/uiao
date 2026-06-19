# UIAO AWS SaaS deployment (ADR-117)

The AWS surface for the multi-tenant UIAO SaaS plane (`uiao.saas`) — the
parallel of [`deploy/azure/`](../azure/). Same application, different cloud:
**ECS Fargate** runs `uiao.saas.asgi:app` behind an **Application Load
Balancer**, against an **RDS PostgreSQL** tenant registry, with an **S3**
evidence bucket. IaC is **AWS CDK (Python)**.

## Layout

| File | Purpose |
|---|---|
| `app.py` | CDK app entrypoint — reads context, instantiates the stack |
| `uiao_saas_stack.py` | The stack: VPC · RDS · ECS Fargate + ALB · S3 · IAM task role |
| `cdk.json` | CDK config (`app: python3 app.py`) |
| `requirements.txt` | Deploy-time deps (`aws-cdk-lib`, `constructs`) — **not** runtime deps |

## Hardening (mirrors ADR-116)

- **Passwordless Postgres.** RDS IAM database authentication is enabled; the
  task role is granted `rds-db:connect` on the `uiao_app` user. The app mints a
  short-lived IAM token as the connection password (`uiao.saas.aws_pg_auth`) —
  no long-lived DB password reaches the task. Env: `UIAO_SAAS_DATABASE_USE_AWS_IAM_AUTH=true`.
- **Private, encrypted data tier.** RDS is in private subnets, not publicly
  accessible, reachable only from the service security group. The evidence
  bucket enforces TLS, blocks public access, and is encrypted + versioned.

## Deploy

```bash
cd deploy/aws
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
npm install -g aws-cdk@2          # CDK CLI (needs Node)

# Synthesize (no AWS account needed — same as the CI gate)
cdk synth -c environmentName=dev

# Deploy (uses your AWS credentials; pass the pushed ECR image)
cdk bootstrap                      # once per account/region
cdk deploy -c environmentName=dev \
  -c imageUri=<acct>.dkr.ecr.<region>.amazonaws.com/uiao-saas:latest \
  -c appClientId=<client-id> -c publisherTenantId=<tenant-guid>
```

The container image is the cloud-neutral `uiao-saas` image (same
`deploy/azure/Dockerfile`); build + push it to ECR before `cdk deploy`.

### One-time DB role bootstrap

RDS IAM auth requires the `uiao_app` role to exist with the `rds_iam` role
granted. After the first deploy, connect once as the master user (from the
generated Secrets Manager secret) and run:

```sql
CREATE USER uiao_app;
GRANT rds_iam TO uiao_app;
GRANT ALL PRIVILEGES ON DATABASE uiao TO uiao_app;
```

This is the AWS counterpart of binding the managed identity as the Postgres
Entra administrator on Azure — it cannot be expressed in CDK because it is a
data-plane (SQL) operation.

## Validation

`.github/workflows/cdk-synth.yml` runs `cdk synth` on every change under
`deploy/aws/` — credential-free, no account — catching construct/API errors
before `cdk deploy`. The AWS analogue of the Bicep validation gate.

> Per-tenant stamp execution (RDS schema / S3 prefix / Secrets Manager scope)
> is provided by `uiao.saas.aws_stamp` + `aws_provisioners`, enabled with
> `UIAO_SAAS_STAMP_EXECUTION_ENABLED=true` (dry-run by default).
