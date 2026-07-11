# AWS-native CI equivalent — CodePipeline + CodeBuild (concise)

> **Starter skeleton / reference.** The primary CI example is
> [`github-actions-aws-ddi.yml`](./github-actions-aws-ddi.yml). This document
> describes the **AWS-native** equivalent using **CodePipeline + CodeBuild** for
> teams standardized on it. The CodePipeline/CodeBuild definitions are
> IaC-JSON/YAML-heavy, so this is kept as a concise design note rather than a full
> template — the stage shape, IAM model, and boundary gate are identical to the
> GitHub Actions workflow.

## Same three stages (contract §2)

```
Stage 1  Control Tower / LZA (separate pipeline/account factory)
   └── outputs: network_account_id, hub_vpc_id, transit_gateway_id,
                r53_resolver_inbound_ip  (read via SSM parameters / remote state)
                        │
                        ▼
Stage 2  DDI      CodeBuild: terraform init/plan/apply of ../terraform
   └── outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                discovery_identity_id, ddi_subnet_ids
                        │
                        ▼
Stage 3  Validate  CodeBuild: validation/*.sh — any non-zero exit fails the run
```

Model it as one **CodePipeline** with three **Actions** (or three CodeBuild
projects): `Source` → `Plan/Apply (DDI)` → `Validate`. A **manual approval**
action before Apply on `test`/`prod` is the human gate (the CodePipeline analog of
GitHub Environment reviewers).

## Auth & state (no long-lived keys)

- **Roles, not keys.** Each CodeBuild project runs under an IAM **service role**.
  To deploy into the **Network/connectivity account**, the CodeBuild role
  **assumes a role** there (cross-account `sts:AssumeRole`) — the same target role
  the GitHub Actions OIDC flow assumes. No static access keys anywhere.
- **Remote state.** Terraform state in an **S3 bucket** (SSE-KMS, versioned,
  `BlockPublicAccess`) with a **DynamoDB table** for state locking — identical to
  the GitHub Actions backend config.
- **Secrets.** Infoblox WAPI/CSP creds and the discovery **ExternalId** come from
  **AWS Secrets Manager** (or SSM `SecureString`) at build time via the CodeBuild
  role — never in the buildspec, never in the repo.

## Boundary gate (contract §1)

The first CodeBuild command block runs the same check as the Actions workflow:

```yaml
# buildspec (Plan/Apply project) — pre_build phase
pre_build:
  commands:
    - |
      if [ "$DEPLOYMENT_MODEL" = "universal_ddi" ] && [ "$ACKNOWLEDGE_SAAS_BOUNDARY" != "true" ]; then
        echo "BOUNDARY: universal_ddi routes control plane to Infoblox Portal SaaS (outside the ATO boundary)."
        echo "Set ACKNOWLEDGE_SAAS_BOUNDARY=true only after the FedRAMP/authorization review. See _module-contract.md §1."
        exit 1
      fi
```

The Terraform module enforces the same rule via `terraform_data.boundary_guard`;
the buildspec fails fast so the SaaS path is never even planned without a review.

## Buildspec sketch (Stage 2 project)

```yaml
version: 0.2
env:
  variables:
    TF_VERSION: "1.9.5"
    AWS_REGION: "us-east-1"        # commercial; NOT us-gov-*
    DEPLOYMENT_MODEL: "grid"
    ACKNOWLEDGE_SAAS_BOUNDARY: "false"
  secrets-manager:
    DISCOVERY_EXTERNAL_ID: "infoblox/discovery-external-id"
phases:
  install:
    commands:
      - curl -fsSLo tf.zip https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip
      - unzip -o tf.zip -d /usr/local/bin
  build:
    commands:
      - cd infoblox-ddi-book/aws-lz-automation/terraform
      - terraform init -backend-config="bucket=$TFSTATE_BUCKET" -backend-config="key=ddi-$ENVIRONMENT.tfstate" -backend-config="region=$AWS_REGION" -backend-config="dynamodb_table=$TFSTATE_LOCK_TABLE" -backend-config="encrypt=true"
      - terraform plan -input=false -out=tfplan
      - terraform apply -input=false -auto-approve tfplan   # gate behind a manual-approval Action for prod
```

## Variable / secret wiring

| Purpose | CodePipeline / CodeBuild |
|---|---|
| Deploy identity | CodeBuild service role → `sts:AssumeRole` into the Network account |
| TF remote-state backend | env `TFSTATE_BUCKET` / `TFSTATE_LOCK_TABLE` |
| Stage 1 outputs | SSM parameters `/lza/network/*` or Terraform remote state |
| Infoblox WAPI creds | Secrets Manager `infoblox/wapi-username` / `infoblox/wapi-password` |
| Infoblox CSP token (universal_ddi) | Secrets Manager `infoblox/csp-token` |
| Discovery ExternalId | Secrets Manager `infoblox/discovery-external-id` |
| DNS test inputs | CodeBuild env `TEST_FQDN` / `EXPECTED_IP` / `PRIVATELINK_FQDN` |

## Promotion flow

`dev` sandbox (auto-apply) → `test` (manual-approval Action) → `prod`
(manual-approval Action + separate account). Each environment uses a distinct
state key (`ddi-<env>.tfstate`) so promotions are isolated — exactly as the
GitHub Actions workflow does.
