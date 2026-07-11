# Automating Azure Landing Zones with Infoblox DDI

A companion to **Vol VII / FedAAN — Infoblox Multi-Cloud DDI** (specifically
`Vol_VII_Book_02` / [`01-azure.md`](../01-azure.md), the Azure chapter). Where the Azure
chapter is the **deploy-oriented runbook**, this package is the **automation-grade layer**:
how to add Infoblox DDI to an Azure Landing Zone (ALZ) as a modular, IaC-driven,
drift-resistant component that layers cleanly on top of Microsoft's ALZ Accelerator.

## Why this exists

The building blocks are all vendor-supported, but **no single vendor document ties them
together**:

- **Microsoft** ships the [ALZ Bicep/Terraform Accelerators](https://github.com/Azure/Azure-Landing-Zones)
  and Azure Verified Modules — they build the platform + hub, but know nothing about Infoblox.
- **Infoblox** ships the [official Terraform provider](https://github.com/infobloxopen/terraform-provider-infoblox),
  a [vNIOS-on-Azure deployment guide](https://docs.infoblox.com/space/vniosazure/37486729/Deploying+vNIOS+for+Azure+from+the+Marketplace),
  and the [Terraform NIOS deployment guide](https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs)
  — they deploy/manage Infoblox, but know nothing about the ALZ Accelerator.

This package is the missing seam: **Stage 1 (ALZ Accelerator) → Stage 2 (this Infoblox DDI
module) → Stage 3 (validation)**, with the hub-network outputs of Stage 1 flowing in as the
inputs of Stage 2.

## Scope discipline (unchanged from the volume)

Infoblox does **not** build the landing zone (management groups, identity, governance,
compute). Those are Stage 1. This package owns the **DDI + DNS-security layer inside the
Connectivity hub** and nothing else.

## Boundary & compliance posture

Built for a **GCC-Moderate operating posture on commercial Azure (`.com` endpoints)** — not
Azure Government (`.us`). One decision follows directly from that and is enforced in the code:

| `deployment_model` | Control plane location | GCC-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** your tenant / ATO boundary | **Boundary-clean.** Recommended. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443) | Requires a FedRAMP/authorization review; the module hard-fails unless `acknowledge_saas_boundary = true`. |

See [`_module-contract.md`](./_module-contract.md) for the full boundary rule.

## What's in here

| Path | What it is |
|---|---|
| [`_module-contract.md`](./_module-contract.md) | The shared contract — variables, ports, IAM, naming, outputs. Read this first. |
| `Azure-ALZ-Infoblox-DDI-Automation-Guide.md` | The implementation guide: 11-section skeleton mapped to ALZ automation, layered architecture, sequencing, GCC-Moderate control mapping. |
| [`Azure-ALZ-DDI-Step-by-Step-Runbook.md`](./Azure-ALZ-DDI-Step-by-Step-Runbook.md) | The **detailed step-by-step deployment runbook** — 14 sequential phases with exact `az`/`terraform`/`git` commands, per-step verification, and troubleshooting. Start here to actually deploy. |
| `terraform/` | Starter Terraform module (`azurerm` + `infobloxopen/infoblox`), `deployment_model`-driven, with a hub-integration example. |
| `bicep/` | Parallel Bicep module + params; API/Ansible handoff where no Bicep-native Infoblox resource exists. |
| `pipelines/` | Multi-stage GitOps examples (GitHub Actions + Azure DevOps): ALZ → DDI → validation. |
| `validation/` | Day-0/Day-2 validation scripts (DNS resolution, discovery-sync status, conflict checks). |

## Status

The IaC here is a **coherent starter skeleton**, explicitly labeled as such — it encodes the
right structure, variables, resources, and guardrails, but is not a certified production
module. Pin your own provider/module versions, supply your Marketplace image and VM SKU
(region/model-dependent — never hard-coded here), and test in a sandbox ALZ first.

---

*Independent of UIAO governance canon; vendor-integration documentation, self-contained under
`infoblox-ddi-book/azure-alz-automation/`.*
