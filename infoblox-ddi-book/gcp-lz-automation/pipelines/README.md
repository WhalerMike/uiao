# Pipelines — Foundation → DDI → Validate (Stage 2 + Stage 3)

> **Starter skeleton.** Valid, internally consistent CI definitions that encode the
> right stages, contract variables, and guardrails — but you must pin action / builder
> versions, wire your own projects / backend bucket / Secret Manager, and supply
> region-dependent inputs (machine type, image) before production use.

Two equivalent renderings of the same three-stage flow:

| File | Platform | Google Cloud auth |
|---|---|---|
| `github-actions-gcp-ddi.yml` | GitHub Actions | `google-github-actions/auth@v2` **Workload Identity Federation** (no exported key) |
| `cloudbuild-gcp-ddi.md` | Cloud Build (concise doc) | Cloud Build **service-account identity** (no exported key) |

Both run **commercial Google Cloud** and source Infoblox WAPI/CSP creds from
**Secret Manager** at run time.

## How this layers on Stage 1

Stage 1 is the **landing-zone foundation** — Terraform Example Foundation or Cloud
Foundation Fabric / FAST (org hierarchy, projects, org policy, the Shared VPC) —
typically its **own** pipeline owned by the platform team. These pipelines are
**Stage 2 + Stage 3** and never build the landing zone. The first stage (`lz`) is a
**read-only handoff**: it consumes Stage 1's remote-state outputs and passes them as
inputs to the DDI module (contract §2):

```
Stage 1 Foundation (separate pipeline)
   └── outputs: host_project_id, shared_vpc_network, region,
                (cloud_dns_inbound_ip, secret_project_id)
                        │  (remote state read by the lz stage)
                        ▼
Stage 2 ddi         terraform init/plan/apply of ../terraform
   └── outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                discovery_service_account_email, ddi_subnet_id
                        │
                        ▼
Stage 3 validate    validation/*.sh — any non-zero exit fails the run
```

## Workload Identity Federation setup (no exported keys)

### GitHub Actions
1. Create a **Workload Identity Pool + Provider** trusting the GitHub OIDC issuer
   (`token.actions.githubusercontent.com`), with an attribute condition scoping to
   your repo/branch/environment.
2. Create a deploy **service account** and let the WIF provider impersonate it; grant
   it least-privilege IAM on the deploy scope (create the DDI subnet / firewall /
   instances; read Stage-1 state bucket; `secretAccessor` on the Infoblox secrets).
   Follow contract §5 for the *discovery* SA — that is a separate, even-less-privileged
   identity.
3. Store the WIF provider resource name and the deploy SA email as **vars**
   (`WIF_PROVIDER`, `DEPLOY_SA_EMAIL`) — identifiers, not credentials; the token is
   fetched via OIDC. The job sets `permissions: id-token: write`.

### Cloud Build
1. Run the build as the default Cloud Build SA or a dedicated deploy SA.
2. Grant it the same least-privilege IAM as above.
3. Gate `prod` with a manual approval on the trigger. See `cloudbuild-gcp-ddi.md`.

## Variable / secret wiring

Non-secret config is plain variables; **secrets come from Secret Manager** and are
never committed. Ports, IAM scopes, and variable names follow `_module-contract.md`.

| Purpose | GitHub Actions | Cloud Build |
|---|---|---|
| Google identity | vars `WIF_PROVIDER` / `DEPLOY_SA_EMAIL` | build service account |
| TF remote-state backend | var `TFSTATE_BUCKET` | substitution `_TFSTATE_BUCKET` |
| Stage 1 state location | vars `LZ_STATE_BUCKET` / `LZ_STATE_PREFIX` | substitutions |
| Secret Manager project | var `SECRET_PROJECT_ID` | `_SECRET_PROJECT_ID` |
| Infoblox WAPI creds | Secret Manager `infoblox-wapi-username/password` | `availableSecrets` |
| Infoblox CSP token (universal_ddi) | Secret Manager `infoblox-csp-token` | `availableSecrets` |
| DNS test inputs | vars `TEST_FQDN` / `EXPECTED_IP` / `PRIVATELINK_FQDN` | substitutions |

## Boundary gate (contract §1)

Both pipelines carry a `deployment_model` (`grid` default) and
`acknowledge_saas_boundary` (`false` default). Before any init/apply, a gate step
**hard-fails** if `deployment_model = universal_ddi` and `acknowledge_saas_boundary
!= true`, because that path routes the control plane to the Infoblox Portal SaaS
**outside the ATO boundary**. The Terraform module enforces the same rule; the
pipeline fails fast so the SaaS path is never even planned without an authorization
review.

## Promotion flow (dev sandbox → prod)

1. **PR** → plan-only. PRs never apply; the `validate` stage is skipped (nothing
   deployed). Review the plan.
2. **dev sandbox** → `workflow_dispatch` (GitHub) / manual run with `_APPLY=true`
   (Cloud Build), `environment=dev`. Apply + full validation against a sandbox project.
3. **test** → same, `environment=test`. Environment protection / approval gate entry.
4. **prod** → `environment=prod`; **required reviewers** (GitHub Environments) /
   **manual approval** (Cloud Build trigger) provide the human gate. Merge to `main`
   can auto-apply to the configured default environment; keep prod behind explicit
   approval.

Each environment uses a distinct state prefix (`infoblox-ddi/<env>`) so promotions
are isolated.

## Runner tooling

The `validate` stage installs `dnsutils` (`dig`), `jq`, and `curl`. Runners need
network reachability to the DDI anycast VIP, the Grid Master WAPI, and (for
`universal_ddi`) `csp.infoblox.com`.
</content>
