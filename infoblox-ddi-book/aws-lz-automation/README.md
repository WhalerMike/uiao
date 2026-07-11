# Automating AWS Landing Zones with Infoblox DDI

A companion to **Vol VII / FedAAN — Infoblox Multi-Cloud DDI** (specifically
`Vol_VII_Book_02` / [`02-aws.md`](../02-aws.md), the AWS chapter). Where the AWS
chapter is the **deploy-oriented runbook**, this package is the **automation-grade
layer**: how to add Infoblox DDI to an AWS Landing Zone as a modular, IaC-driven,
drift-resistant component that layers cleanly on top of AWS Control Tower and the
Landing Zone Accelerator on AWS.

This is the **Terraform-only** AWS analog of the Azure ALZ package
([`../azure-alz-automation/`](../azure-alz-automation/)) — same structure, same
boundary rule, adapted to AWS primitives.

## Why this exists

The building blocks are all vendor-supported, but **no single vendor document ties
them together**:

- **AWS** ships [Control Tower and the Landing Zone Accelerator on AWS](https://github.com/awslabs/landing-zone-accelerator-on-aws)
  — they build the organization, guardrails, and the Network-account hub VPC +
  Transit Gateway, but know nothing about Infoblox.
- **Infoblox** ships the [official Terraform provider](https://github.com/infobloxopen/terraform-provider-infoblox)
  and a [vNIOS-on-AWS deployment path](https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs)
  — they deploy/manage Infoblox, but know nothing about the Landing Zone
  Accelerator.

This package is the missing seam: **Stage 1 (Control Tower / LZA) → Stage 2 (this
Infoblox DDI module) → Stage 3 (validation)**, with the hub-network outputs of
Stage 1 flowing in as the inputs of Stage 2.

## Scope discipline (unchanged from the volume)

Infoblox does **not** build the landing zone (organization, accounts, guardrails,
compute). Those are Stage 1. This package owns the **DDI + DNS-security layer
inside the Network-account shared-services VPC** and nothing else.

## Boundary & compliance posture

Built for a **GCC-Moderate operating posture on the commercial AWS partition
(`.com` endpoints)** — not AWS GovCloud (`us-gov-*`). One decision follows directly
from that and is enforced in the code:

| `deployment_model` | Control plane location | GCC-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** your account / ATO boundary | **Boundary-clean.** Recommended. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443) | Requires a FedRAMP/authorization review; the module hard-fails unless `acknowledge_saas_boundary = true`. |

See [`_module-contract.md`](./_module-contract.md) for the full boundary rule.
(vNIOS, multi-account vDiscovery from NIOS 9.0.4+, and Route 53 integration from
NIOS 8.6.3+ all run in **AWS GovCloud** too, but that partition is out of scope for
this deliverable.)

## What's in here

| Path | What it is |
|---|---|
| [`_module-contract.md`](./_module-contract.md) | The shared contract — variables, ports, IAM, naming, outputs. Read this first. |
| `AWS-LZ-Infoblox-DDI-Automation-Guide.md` | The implementation guide: 11-section skeleton mapped to LZA automation, layered architecture, sequencing, FedRAMP-Moderate control mapping. |
| [`AWS-LZ-DDI-Step-by-Step-Runbook.md`](./AWS-LZ-DDI-Step-by-Step-Runbook.md) | The **detailed step-by-step deployment runbook** — 14 sequential phases with exact `aws`/`terraform`/`git` commands, per-step verification, troubleshooting, and an **Appendix A — Variable Worksheets**. Start here to actually deploy. |
| `terraform/` | Starter Terraform module (`hashicorp/aws` + `infobloxopen/infoblox`), `deployment_model`-driven, with a hub-integration example. |
| `pipelines/` | Multi-stage GitOps examples (GitHub Actions + a CodePipeline design note): LZA → DDI → validation. |
| `validation/` | Day-0/Day-2 validation scripts (DNS resolution, discovery-sync status, conflict checks). |
| `figs/` | Mermaid figure sources (reference architecture, discovery/IPAM sync, DNS resolution). |

## Status

The IaC here is a **coherent starter skeleton**, explicitly labeled as such — it
encodes the right structure, variables, resources, and guardrails, but is not a
certified production module. Pin your own provider/module versions, subscribe to
the Infoblox Marketplace listing and supply your AMI ID and instance type
(region/model-dependent — never hard-coded here), and test in a sandbox account
first.

---

*Independent of UIAO governance canon; vendor-integration documentation,
self-contained under `infoblox-ddi-book/aws-lz-automation/`.*
