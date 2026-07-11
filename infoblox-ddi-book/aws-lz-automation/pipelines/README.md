# Pipelines — LZA → DDI → Validate (Stage 2 + Stage 3)

> **Starter skeleton.** Valid, internally consistent CI definitions that encode
> the right stages, contract variables, and guardrails — but you must pin action
> / image versions, wire your own accounts / backend / Secrets Manager, and
> supply region-dependent inputs (instance type, Marketplace AMI) before
> production use.

Two equivalent CI examples:

| File | Platform | AWS auth |
|---|---|---|
| `github-actions-aws-ddi.yml` | GitHub Actions | `aws-actions/configure-aws-credentials` **OIDC role-to-assume** (no stored keys) |
| `codepipeline-aws-ddi.md` | AWS CodePipeline + CodeBuild (design note) | CodeBuild **service role** → cross-account `sts:AssumeRole` (no stored keys) |

Both run the **commercial AWS partition `.com`** (`sts.amazonaws.com`) — **not**
GovCloud (`us-gov-*`).

## How this layers on Stage 1

Stage 1 is **AWS Control Tower / the Landing Zone Accelerator on AWS** (the
organization, account factory, guardrails, and the Network-account shared-services
hub VPC + Transit Gateway) — typically its **own** pipeline owned by the platform
team. These pipelines are **Stage 2 + Stage 3** and never build the landing zone.
The first stage (`lza`) is a **read-only handoff**: it consumes Stage 1's outputs
and passes them as inputs to the DDI module (contract §2):

```
Stage 1 Control Tower / LZA (separate pipeline)
   └── outputs: network_account_id, hub_vpc_id, transit_gateway_id,
                r53_resolver_inbound_ip
                        │  (remote state / SSM parameters read by the lza stage)
                        ▼
Stage 2 ddi         terraform init/plan/apply of ../terraform
   └── outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                discovery_identity_id, ddi_subnet_ids
                        │
                        ▼
Stage 3 validate    validation/*.sh — any non-zero exit fails the run
```

## OIDC / role setup (no stored keys)

### GitHub Actions
1. Create an **IAM OIDC identity provider** for
   `token.actions.githubusercontent.com` in the deploy account, and an **IAM
   role** whose trust policy scopes the `sub` claim to your repo/branch/environment
   (e.g. `repo:<org>/<repo>:environment:prod`) with audience `sts.amazonaws.com`.
2. Grant that role least-privilege permissions on the target scope (create the DDI
   subnets/SG/instances; read Stage 1 state). If deploying into the Network
   account from a tooling account, have this role **assume** a role there.
3. Store the role ARN as secret `AWS_DEPLOY_ROLE_ARN`, and the discovery
   **ExternalId** as secret `DISCOVERY_EXTERNAL_ID`. The job sets
   `permissions: id-token: write`; there are **no long-lived access keys**.

### AWS CodePipeline / CodeBuild
See [`codepipeline-aws-ddi.md`](./codepipeline-aws-ddi.md). The CodeBuild service
role assumes a role in the Network account; a **manual-approval Action** gates
Apply on `test`/`prod`.

## Variable / secret wiring

Non-secret config is plain variables; **secrets come from AWS Secrets Manager**
(or SSM `SecureString`) and are never committed. Ports, IAM scopes, and variable
names follow `_module-contract.md`.

| Purpose | GitHub Actions | CodePipeline |
|---|---|---|
| AWS deploy identity | secret `AWS_DEPLOY_ROLE_ARN` (OIDC role-to-assume) | CodeBuild service role → AssumeRole |
| TF remote-state backend | vars `TFSTATE_BUCKET` / `TFSTATE_LOCK_TABLE` (S3 + DynamoDB) | env `TFSTATE_BUCKET` / `TFSTATE_LOCK_TABLE` |
| Stage 1 outputs | vars `LZA_STATE_BUCKET` / `LZA_STATE_KEY` (or SSM) | SSM `/lza/network/*` |
| Infoblox WAPI creds | Secrets Manager `infoblox/wapi-username` / `infoblox/wapi-password` | same |
| Infoblox CSP token (universal_ddi) | Secrets Manager `infoblox/csp-token` | same |
| Discovery ExternalId | secret `DISCOVERY_EXTERNAL_ID` (Secrets Manager) | Secrets Manager `infoblox/discovery-external-id` |
| DNS test inputs | vars `TEST_FQDN` / `EXPECTED_IP` / `PRIVATELINK_FQDN` | CodeBuild env |

## Boundary gate (contract §1)

Both examples carry a `deployment_model` (`grid` default) and
`acknowledge_saas_boundary` (`false` default). Before any init/apply, a gate step
**hard-fails** if `deployment_model = universal_ddi` and
`acknowledge_saas_boundary != true`, because that path routes the control plane to
the Infoblox Portal SaaS **outside the ATO boundary**. The Terraform module
enforces the same rule; the pipeline fails fast so the SaaS path is never even
planned without an authorization review.

## Promotion flow (dev sandbox → prod)

1. **PR** → plan-only. PRs never apply; the `validate` stage is skipped (nothing
   deployed). Review the plan.
2. **dev sandbox** → `workflow_dispatch` (GitHub) / run with a `dev` account,
   apply + full validation against a sandbox landing zone.
3. **test** → same, `environment=test`. Environment protection / manual-approval
   Action gates entry.
4. **prod** → `environment=prod`; **required reviewers** (GitHub Environments) /
   **manual-approval Action** (CodePipeline) provide the human gate. Keep prod
   behind explicit approval.

Each environment uses a distinct state key (`ddi-<env>.tfstate`) so promotions are
isolated.

## Runner tooling

The `validate` stage installs `dnsutils` (`dig`), `jq`, and `curl`. Runners need
network reachability to the DDI anycast VIP, the Grid Master WAPI, and (for
`universal_ddi`) `csp.infoblox.com`.
