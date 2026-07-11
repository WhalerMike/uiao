# OCI Resource Manager — the native Terraform path

**OCI Resource Manager (RM) *is* Terraform** — a managed service that runs the same
`terraform/` module in this package as a **stack**, with OCI-managed state and
**credentials injected automatically**. It is the OCI-native equivalent of a second
IaC path: where the Azure package pairs Terraform with Bicep, OCI pairs the same
Terraform with Resource Manager. This note is deliberately concise — the module and
the runbook do the heavy lifting; RM just changes *how* the plan/apply runs.

> **Why RM over key-based CI.** The GitHub Actions pipeline
> ([`github-actions-oci-ddi.yml`](./github-actions-oci-ddi.yml)) has to assemble an
> OCI API-key config from secrets because OCI's OIDC-to-GitHub federation is limited.
> Resource Manager sidesteps that entirely: the stack runs **inside OCI** under a
> **resource principal**, so there is **no OCI key in any pipeline**. That is a
> boundary win for a FedRAMP-Moderate posture.

## What a stack is

A **stack** is a Resource Manager object bound to a Terraform configuration + its
variables. Running a **job** against the stack does `plan` / `apply` / `destroy`,
with state stored and locked by OCI. Stacks can be sourced from a zip, an Object
Storage object, or a **Git source control** provider (GitHub/GitLab) — the same repo
this module lives in.

## Mapping to the three stages

Same shape as the runbook and the GitHub Actions pipeline:

| Stage | Resource Manager expression |
|---|---|
| **Stage 1 — LZ** | The CIS Landing Zone is often *itself* an RM stack (the quickstart ships as one). Publish its network outputs (`hub_vcn_ocid`, `network_compartment_ocid`, `drg_ocid`, `vault_ocid`, hub resolver OCID). |
| **Stage 2 — DDI** | A **stack** pointed at `oci-lz-automation/terraform`, its variables set to the §3 canonical inputs (Stage-1 OCIDs, `vnios_image_ocid`, Vault secret OCIDs). `plan` job on PR; `apply` job on approval. |
| **Stage 3 — Validate** | The `validation/*.sh` scripts run in a **CI runner or an OCI Functions/Cloud Shell step** after the apply job (RM runs Terraform, not arbitrary shell), reading Stage-2 outputs. |

## Wiring the DDI stack (outline)

1. **Create the stack** from the Git source (`oci resource-manager stack create`
   with `--config-source` pointing at the repo/branch and the module subdirectory),
   or in the console: *Developer Services → Resource Manager → Stacks → Create Stack
   → Source: Source Code Control System*.
2. **Set variables** to the §3 contract inputs. Sensitive values (Vault secret OCIDs
   are references, not secrets; the actual admin password/license stay in OCI Vault
   and are read by the module at apply time via `oci_secrets_secretbundle`).
3. **Consume Stage-1 outputs.** Either wire `terraform_remote_state` to the CIS LZ
   state, or set the Stage-1 OCIDs as stack variables from the LZ stack's outputs.
4. **Run a `plan` job** (review), then an **`apply` job** behind an approval. The
   boundary guard (`terraform_data.boundary_guard`) still hard-fails `universal_ddi`
   unless `acknowledge_saas_boundary = true` — RM surfaces the precondition error in
   the job log exactly as local Terraform does.
5. **Least-privilege for the stack.** Grant the RM stack's identity (resource
   principal) only what Stage 2 needs — create the DDI subnet/instances/DNS in the
   network compartment, manage IAM for the discovery identity, read the Vault
   secret-bundles. This is a **separate, more-privileged** identity than the
   `ddi-disco-dg` discovery dynamic group (contract §5).

## CLI sketch

```bash
# Create a Git-sourced DDI stack (illustrative flags; confirm against your oci CLI).
oci resource-manager stack create-from-git-provider \
  --compartment-id "$NETWORK_COMPARTMENT_OCID" \
  --display-name "infoblox-ddi-stage2" \
  --working-directory "infoblox-ddi-book/oci-lz-automation/terraform" \
  --config-source-configuration-source-provider-id "$GIT_PROVIDER_OCID" \
  --config-source-branch-name main \
  --variables file://ddi-stack-variables.json

# Plan, then apply behind approval.
oci resource-manager job create-plan-job --stack-id "$STACK_OCID"
oci resource-manager job create-apply-job --stack-id "$STACK_OCID" \
  --execution-plan-strategy FROM_PLAN_JOB_ID --execution-plan-job-id "$PLAN_JOB_OCID"
```

## When to use which

- **Resource Manager** — you want the OCI-native, no-key-in-CI path; the CIS LZ is
  already an RM stack; you value OCI-managed state + drift detection in the console.
- **GitHub Actions** (this repo's `.yml`) — you standardize CI on GitHub and accept
  managing the OCI API-key config in secrets, or you want the same pipeline shape
  across Azure/AWS/GCP/OCI.

Either way it is the **same Terraform module** — one code path, two runners. Choose
one per environment; do not run both against the same state.

## Sources

- [Oracle — OCI Terraform provider (Registry docs)](https://registry.terraform.io/providers/oracle/oci/latest/docs)
- [OCI CIS Landing Zone quickstart (ships as a Resource Manager stack)](https://github.com/oracle-quickstart/oci-cis-landingzone-quickstart)
