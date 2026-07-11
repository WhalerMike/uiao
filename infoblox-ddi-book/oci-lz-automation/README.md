# Automating OCI Landing Zones with Infoblox DDI

A companion to **Vol VII / FedAAN — Infoblox Multi-Cloud DDI** (specifically the OCI
chapter, [`04-oci.md`](../04-oci.md)). Where the OCI chapter is the **deploy-oriented
runbook**, this package is the **automation-grade layer**: how to add Infoblox DDI to an
OCI landing zone as a modular, Terraform-driven, drift-resistant component that layers
cleanly on top of the **OCI CIS / Core Landing Zone**.

## Why this exists

The building blocks are all vendor-supported, but **no single vendor document ties them
together**:

- **Oracle** ships the [CIS Landing Zone quickstart](https://github.com/oracle-quickstart/oci-cis-landingzone-quickstart)
  and the OCI Core Landing Zone — they build the tenancy, compartments, IAM, and the hub
  VCN + DRG, but know nothing about Infoblox.
- **Infoblox** ships the [official Terraform provider](https://github.com/infobloxopen/terraform-provider-infoblox)
  and a vNIOS-on-OCI custom-image deployment path — they deploy/manage Infoblox, but know
  nothing about the CIS Landing Zone.

This package is the missing seam: **Stage 1 (CIS Landing Zone) → Stage 2 (this Infoblox DDI
module) → Stage 3 (validation)**, with the hub-network outputs of Stage 1 flowing in as the
inputs of Stage 2.

## Candor up front — OCI is a thinner integration target

Mirroring [`04-oci.md`](../04-oci.md), this package is honest about two OCI realities:

- **No native Marketplace vNIOS listing.** You deploy vNIOS by **custom-image import** — pull
  the Infoblox OCI image into **Object Storage** and `oci compute image import` it. There is
  no Marketplace agreement to accept.
- **No deep, event-driven cloud-discovery connector.** Infoblox has no OCI adapter equivalent
  to its AWS/Azure/GCP Cloud Network Automation connectors. On OCI, IPAM synchronisation is
  **API/SDK/Terraform-driven** — a scheduled OCI-SDK job or the Infoblox provider running in
  the same pipeline that provisions the VCN. This package wires the **credential and the
  seam** and says so plainly.

## Scope discipline (unchanged from the volume)

Infoblox does **not** build the landing zone (tenancy, compartments, IAM, the hub network).
Those are Stage 1. This package owns the **DDI + DNS-security layer inside the hub VCN** and
nothing else.

## Boundary & compliance posture

Built for a **FedRAMP Moderate-equivalent posture on commercial OCI (the OC1 realm,
`*.oraclecloud.com`)** — not OCI Government (OC2/OC3) or National-Security realms. One
decision follows directly and is enforced in the code:

| `deployment_model` | Control plane location | FedRAMP-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** your tenancy / ATO boundary | **Boundary-clean.** Recommended. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443) | Requires an authorization review; the module hard-fails unless `acknowledge_saas_boundary = true`. |

In sovereign / gov realms the Portal is typically unreachable — default to Grid there. See
[`_module-contract.md`](./_module-contract.md) for the full boundary rule.

## What's in here

| Path | What it is |
|---|---|
| [`_module-contract.md`](./_module-contract.md) | The shared contract — variables, ports, IAM, naming, outputs. Read this first. |
| `OCI-LZ-Infoblox-DDI-Automation-Guide.md` | The implementation guide: 11-section skeleton mapped to OCI automation, layered architecture, sequencing, FedRAMP-Moderate control mapping. |
| [`OCI-LZ-DDI-Step-by-Step-Runbook.md`](./OCI-LZ-DDI-Step-by-Step-Runbook.md) | The **detailed step-by-step deployment runbook** — sequential phases with exact `oci`/`terraform`/`git` commands, per-step verification, troubleshooting, and **Appendix A — Variable Worksheets**. Start here to actually deploy. |
| `terraform/` | Starter Terraform module (`oracle/oci` + `infobloxopen/infoblox`), `deployment_model`-driven, with a hub-integration example. |
| `pipelines/` | GitHub Actions pipeline (LZ → DDI → validate) + an OCI Resource Manager note. |
| `validation/` | Day-0/Day-2 validation scripts (DNS resolution, discovery-sync status, conflict checks). |
| `figs/` | Mermaid figure sources (reference architecture, discovery/IPAM sync, DNS resolution). |

## Status

The IaC here is a **coherent starter skeleton**, explicitly labeled as such — it encodes the
right structure, variables, resources, and guardrails, but is not a certified production
module. Pin your own provider versions, import and supply your vNIOS custom image, choose a
flexible shape (model/region-dependent — never hard-coded here), and test in a sandbox
landing zone first.

---

*Independent of UIAO governance canon; vendor-integration documentation, self-contained under
`infoblox-ddi-book/oci-lz-automation/`.*
