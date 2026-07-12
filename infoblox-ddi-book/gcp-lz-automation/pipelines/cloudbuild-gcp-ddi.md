# Cloud Build equivalent — foundation → DDI → validate

A concise **Cloud Build** rendering of the same three-stage flow as
`github-actions-gcp-ddi.yml`, for teams standardized on Cloud Build instead of
GitHub Actions. Same contract, same boundary gate, same Secret-Manager sourcing —
only the CI syntax differs.

> **Starter skeleton.** Pin builder image digests, wire your own project IDs /
> state bucket / trigger, and supply the image + machine type before production
> use. Choose **one** CI system per environment — GitHub Actions **or** Cloud Build
> — do not run both against one state.

## Auth model (no exported keys)

- Cloud Build runs as a **service account** (the default Cloud Build SA or a
  dedicated `ddi-deploy@…` SA). Grant it least-privilege IAM on the deploy scope
  (create the DDI subnet/firewall/instances in the host project; read Stage-1 state
  bucket; `roles/secretmanager.secretAccessor` on the Infoblox secrets). This is a
  **separate, more-privileged** identity than the discovery `ddi-disco` SA.
- No service-account JSON key is exported — the build inherits the SA identity
  directly, the Cloud Build analog of GitHub's Workload Identity Federation.
- Remote state lives in a **GCS bucket** with object versioning + state locking.

## Boundary gate (contract §1)

The first build step **hard-fails** if `_DEPLOYMENT_MODEL=universal_ddi` and
`_ACKNOWLEDGE_SAAS_BOUNDARY!=true`, because that path routes the control plane to
the Infoblox Portal SaaS **outside the ATO boundary**. The Terraform module
enforces the same rule; the build fails fast so the SaaS path is never even planned
without an authorization review.

## `cloudbuild.yaml`

```yaml
# cloudbuild-gcp-ddi.yaml — Stage 2 (+ Stage 3) for the Infoblox DDI module.
# Trigger on push to main (apply) / PR (plan-only) via two triggers, or gate
# apply on the _APPLY substitution.
substitutions:
  _ENVIRONMENT: "dev"                 # dev | test | prod
  _DEPLOYMENT_MODEL: "grid"           # grid | universal_ddi
  _ACKNOWLEDGE_SAAS_BOUNDARY: "false"
  _APPLY: "false"                     # "true" to apply, else plan-only
  _TF_DIR: "infoblox-ddi-book/gcp-lz-automation/terraform"
  _VALIDATION_DIR: "infoblox-ddi-book/gcp-lz-automation/validation"
  _TFSTATE_BUCKET: "tf-state-example"
  _HOST_PROJECT_ID: "hostproj-shared-vpc"
  _SHARED_VPC_NETWORK: "vpc-hub"
  _REGION: "us-central1"
  _SECRET_PROJECT_ID: "hostproj-shared-vpc"

steps:
  # --- Stage 0: boundary gate (contract §1) ---
  - id: boundary-gate
    name: gcr.io/cloud-builders/gcloud
    entrypoint: bash
    args:
      - -c
      - |
        set -euo pipefail
        if [ "$_DEPLOYMENT_MODEL" = "universal_ddi" ] && [ "$_ACKNOWLEDGE_SAAS_BOUNDARY" != "true" ]; then
          echo "ERROR: universal_ddi routes control plane to Infoblox Portal SaaS (outside the ATO boundary)."
          echo "Set _ACKNOWLEDGE_SAAS_BOUNDARY=true only after the FedRAMP/authorization review (contract §1)."
          exit 1
        fi
        echo "Boundary gate OK (model=$_DEPLOYMENT_MODEL, ack=$_ACKNOWLEDGE_SAAS_BOUNDARY)"

  # --- Stage 2: terraform init/plan[/apply] ---
  - id: terraform
    name: hashicorp/terraform:1.9.5
    entrypoint: sh
    dir: "${_TF_DIR}"
    secretEnv: ["INFOBLOX_USERNAME", "INFOBLOX_PASSWORD"]
    args:
      - -c
      - |
        set -euo pipefail
        terraform init \
          -backend-config="bucket=${_TFSTATE_BUCKET}" \
          -backend-config="prefix=infoblox-ddi/${_ENVIRONMENT}"
        export TF_VAR_environment="${_ENVIRONMENT}"
        export TF_VAR_deployment_model="${_DEPLOYMENT_MODEL}"
        export TF_VAR_acknowledge_saas_boundary="${_ACKNOWLEDGE_SAAS_BOUNDARY}"
        export TF_VAR_host_project_id="${_HOST_PROJECT_ID}"
        export TF_VAR_shared_vpc_network="${_SHARED_VPC_NETWORK}"
        export TF_VAR_region="${_REGION}"
        export TF_VAR_secret_project_id="${_SECRET_PROJECT_ID}"
        terraform plan -input=false -out=tfplan
        if [ "${_APPLY}" = "true" ]; then terraform apply -input=false -auto-approve tfplan; fi

  # --- Stage 3: validation gates (only when applied) ---
  - id: validate
    name: gcr.io/cloud-builders/gcloud
    entrypoint: bash
    dir: "${_VALIDATION_DIR}"
    secretEnv: ["INFOBLOX_USERNAME", "INFOBLOX_PASSWORD"]
    args:
      - -c
      - |
        set -euo pipefail
        [ "${_APPLY}" = "true" ] || { echo "plan-only build — skipping validation"; exit 0; }
        apt-get update && apt-get install -y dnsutils jq curl
        export DDI_VIP="$(cd ../terraform && terraform output -raw ddi_anycast_vip)"
        export GRID_MASTER="$(cd ../terraform && terraform output -raw grid_master_ip)"
        export TEST_FQDN="${_TEST_FQDN:-app01.corp.example.com}"
        export EXPECTED_IP="${_EXPECTED_IP:-10.20.5.10}"
        bash dns-validation.sh
        export DDI_API_FLAVOR="$( [ "${_DEPLOYMENT_MODEL}" = universal_ddi ] && echo universal_ddi || echo nios )"
        export STALE_THRESHOLD_MIN="1440"
        bash discovery-sync-check.sh
        export NETWORK_VIEW="default"
        bash ipam-conflict-check.sh

# WAPI creds pulled from Secret Manager at run time (never in the build config).
availableSecrets:
  secretManager:
    - versionName: projects/${_SECRET_PROJECT_ID}/secrets/infoblox-wapi-username/versions/latest
      env: INFOBLOX_USERNAME
    - versionName: projects/${_SECRET_PROJECT_ID}/secrets/infoblox-wapi-password/versions/latest
      env: INFOBLOX_PASSWORD

options:
  logging: CLOUD_LOGGING_ONLY
```

## Promotion flow

Mirror the GitHub Actions flow: a **PR trigger** runs plan-only (`_APPLY=false`); a
**push-to-main trigger** (or a manual run with `_APPLY=true`) applies and validates.
Gate `prod` with a **manual approval** on the trigger and a distinct state prefix
(`infoblox-ddi/prod`) so promotions stay isolated. The Stage-1 foundation is its own
build/pipeline; this config only consumes its outputs.
