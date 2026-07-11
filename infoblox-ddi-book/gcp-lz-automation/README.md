# Automating Google Cloud Landing Zones with Infoblox DDI

A companion to **Vol VII / FedAAN — Infoblox Multi-Cloud DDI** (specifically the
Google Cloud chapter, [`03-gcp.md`](../03-gcp.md)). Where the GCP chapter is the
**deploy-oriented runbook**, this package is the **automation-grade layer**: how to
add Infoblox DDI to a Google Cloud landing zone as a modular, IaC-driven,
drift-resistant component that layers cleanly on top of a foundation blueprint
(Terraform Example Foundation / Cloud Foundation Fabric FAST).

It is the **Google Cloud sibling** of `azure-alz-automation/`, mirroring that package
one-for-one — same canonical variables, same control-plane boundary rule, same port
set, same validation contracts — adapted to Google Cloud primitives. **Terraform
only** (no Bicep/Deployment-Manager sibling).

## Why this exists

The building blocks are all vendor-supported, but **no single vendor document ties
them together**:

- **Google** ships landing-zone foundations
  ([Terraform Example Foundation](https://github.com/terraform-google-modules/terraform-example-foundation),
  [Cloud Foundation Fabric / FAST](https://github.com/GoogleCloudPlatform/cloud-foundation-fabric))
  — they build the org, projects, and Shared VPC, but know nothing about Infoblox.
- **Infoblox** ships the [official Terraform provider](https://github.com/infobloxopen/terraform-provider-infoblox)
  and a vNIOS-for-Google-Cloud deployment path
  ([provider docs](https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs))
  — they deploy/manage Infoblox, but know nothing about the foundation.

This package is the missing seam: **Stage 1 (foundation) → Stage 2 (this Infoblox DDI
module) → Stage 3 (validation)**, with the Shared-VPC outputs of Stage 1 flowing in as
the inputs of Stage 2.

## Scope discipline (unchanged from the volume)

Infoblox does **not** build the landing zone (org hierarchy, projects, org policy,
Shared VPC). Those are Stage 1. This package owns the **DDI + DNS-security layer
inside the Shared VPC host project** and nothing else.

## Boundary & compliance posture

Built for a **GCC-Moderate-equivalent posture on commercial Google Cloud**. One
decision follows directly from that and is enforced in the code:

| `deployment_model` | Control plane location | GCC-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** your project / ATO boundary | **Boundary-clean.** Recommended. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443 to `csp.infoblox.com`) | Requires a FedRAMP/authorization review; the module hard-fails unless `acknowledge_saas_boundary = true`. |

Data residency / personnel controls on GCP are delivered via **Assured Workloads**
folders (a Stage-1 concern). See [`_module-contract.md`](./_module-contract.md) for the
full boundary rule.

## What's in here

| Path | What it is |
|---|---|
| [`_module-contract.md`](./_module-contract.md) | The shared contract — variables, ports, IAM, naming, outputs. Read this first. |
| `GCP-LZ-Infoblox-DDI-Automation-Guide.md` | The implementation guide: 11-section skeleton mapped to GCP automation, layered architecture, sequencing, FedRAMP-Moderate control mapping. |
| [`GCP-LZ-DDI-Step-by-Step-Runbook.md`](./GCP-LZ-DDI-Step-by-Step-Runbook.md) | The **detailed step-by-step deployment runbook** — sequential phases with exact `gcloud`/`terraform`/`git` commands, per-step verification, troubleshooting, and **Appendix A — Variable Worksheets**. Start here to actually deploy. |
| `terraform/` | Starter Terraform module (`google` + `infobloxopen/infoblox`), `deployment_model`-driven, with a hub-integration example. |
| `pipelines/` | Multi-stage GitOps examples (GitHub Actions + a Cloud Build note): foundation → DDI → validation. |
| `validation/` | Day-0/Day-2 validation scripts (DNS resolution, discovery-sync status, conflict checks). |
| `figs/` | Mermaid figure sources (reference architecture, discovery/IPAM sync, DNS resolution). |

## Status

The IaC here is a **coherent starter skeleton**, explicitly labeled as such — it
encodes the right structure, variables, resources, and guardrails, but is not a
certified production module. Pin your own provider/module versions, supply your image
and machine type (model/version-dependent — never hard-coded here), and test in a
sandbox project first.

---

*Independent of UIAO governance canon; vendor-integration documentation, self-contained
under `infoblox-ddi-book/gcp-lz-automation/`.*
</content>
