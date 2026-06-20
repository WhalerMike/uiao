---
adr_id: adr-119
title: "Private networking for the SaaS data tier — VNet-integrated Postgres (Azure) and VPC endpoints (AWS)"
status: PROPOSED
decided: 2026-06-20
deciders: Michael Stratton
updated: 2026-06-20
next_review: 2026-12-20
review_trigger: A deployment is stood up with enablePrivateNetworking and the VNet/endpoint topology is validated against a real account (this ADR moves toward ACCEPTED); private ingress (internal load balancer / Private Link service) is required, not just a private data tier; the address space or subnet sizing needs to be parameterised per environment; a hub-and-spoke / peered network model replaces the standalone VNet; Container Apps changes its VNet-injection contract
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-119-saas-private-networking.html
impact: "Adds an opt-in private-networking posture to the SaaS deployments (the follow-up ADR-116/117 deferred). Azure: a new network.bicep (VNet + a subnet delegated to the Container Apps environment + a subnet delegated to the Postgres flexible server + the private DNS zone), wired behind a new enablePrivateNetworking parameter (default false). When set, the Container Apps environment is VNet-injected, Postgres is VNet-integrated with public network access disabled and the Azure-services firewall rule omitted. AWS: opt-in VPC endpoints (S3 gateway; ECR api/dkr, Secrets Manager, CloudWatch Logs interface) so service traffic stays in the VPC; the RDS data tier was already private. Both default off, so the existing public-access deployments are unchanged and the IaC validation gates (bicep-validate, cdk-synth) cover both paths. Compile/synth-validated only — deploy-validation against a real account is a tracked review trigger."
---

# ADR-119: Private networking for the SaaS data tier — VNet-integrated Postgres (Azure) and VPC endpoints (AWS)

## Status

**PROPOSED** — June 20, 2026

The deferred follow-up named in **ADR-116** (Azure) and **ADR-117** (AWS):
"private networking … is the natural next hardening step but … requires
deploy-time validation."

## Context

ADR-116 made the Azure Postgres tier passwordless but left it on **public
network access** with an "allow all Azure services" firewall rule — deliberately,
because disabling public access is coupled with building a VNet, and that could
not be deploy-validated at the time. ADR-117's AWS RDS tier was already in
private subnets and not publicly accessible, but the Fargate tasks reach AWS
services (ECR, Secrets Manager, CloudWatch, S3) over NAT/the internet rather
than through VPC endpoints.

Both ADRs named the same caveat: private networking is intricate, cloud-specific
IaC whose correctness ultimately rests on a real deployment, and shipping it
"blind" would undercut the verifiability the SaaS work otherwise maintains.

## Decision

Add private networking to both clouds as an **opt-in, feature-flagged** path,
so the default (public-access) deployments — which the IaC validation gates
already cover — are unchanged, and the private path is compile/synth-validated
now and deploy-validated when an operator stands it up.

**Azure — VNet-integrated Postgres + VNet-injected Container Apps.**
A new `network.bicep` module provisions a VNet with two delegated subnets — one
for the Container Apps environment (VNet injection) and one for the
VNet-integrated Postgres Flexible Server — plus the
`privatelink.postgres.database.azure.com` private DNS zone linked to the VNet.
A new `enablePrivateNetworking` parameter on `main.bicep` (default **false**)
gates it. When set:

* the Container Apps environment is VNet-injected (`infrastructureSubnetId`);
* the Postgres server is VNet-integrated (`delegatedSubnetResourceId` +
  `privateDnsZoneArmResourceId`), which implicitly **disables public network
  access**, and the Azure-services firewall rule is omitted entirely;
* the server is then reachable only from the VNet.

When unset, every module keeps its current public-access shape exactly.

**AWS — VPC endpoints.**
The RDS data tier is already private. The opt-in
(`-c enablePrivateNetworking=true`) adds an **S3 gateway endpoint** and
**interface endpoints** for ECR (api + dkr), Secrets Manager, and CloudWatch
Logs, so image pulls, secret reads, and log writes stay inside the VPC rather
than traversing NAT/the internet. Default off.

## Consequences

### Positive

- **The Postgres tier can be fully private on Azure** — no public network
  access, no Azure-services firewall hole — closing the last ADR-116 caveat.
- **AWS egress to AWS services stays in-VPC** when enabled, reducing the
  internet/NAT dependency for the task role's calls.
- **Default unchanged + gate-covered.** Both `enablePrivateNetworking` paths
  compile (`bicep-validate`) and synth (`cdk-synth`); the public default is
  byte-for-byte what shipped, so existing deployments are unaffected.

### Negative / trade-offs

- **Compile/synth-validated, not deploy-validated.** This is the honest limit:
  CI proves the templates are well-formed, not that a private deployment
  succeeds end-to-end (VNet injection, DNS resolution, subnet sizing, and
  endpoint policies are the kind of thing only a real account confirms). Moving
  this ADR toward ACCEPTED is gated on that validation — a listed review trigger.
- **Fixed address space.** The VNet/subnets use fixed default prefixes
  (`10.20.0.0/16`); environments that need different ranges or peering will
  parameterise them (a review trigger).
- **Private ingress not included.** The load balancer / Container Apps ingress
  stays external; this ADR privatises the *data tier and egress*, not the public
  entry point. An internal-ingress / Private Link option is future work.
- **Cost.** A VNet + interface endpoints (and, on Azure, VNet-integrated
  Postgres) add resources; acceptable for the production posture they enable,
  and off by default for dev.

### Security

- Removing public network access from Postgres and the Azure-services firewall
  rule materially shrinks the database's exposure: it is reachable only from
  inside the VNet, on top of the existing passwordless (token) auth.
- AWS interface endpoints keep ECR/Secrets/Logs traffic on the AWS network and
  allow endpoint policies to further constrain it.

## Boundary note

Inherits the ADR-096 boundary (GCC-Moderate / commercial). VNets, private DNS,
and VPC endpoints are generic primitives on both clouds; no new external
endpoint or sovereign-cloud surface is introduced.

## Implementation

- Azure: `deploy/azure/bicep/modules/network.bicep` (new);
  `postgres.bicep` (conditional VNet-integrated `network` block + firewall rule
  gated off under private access); `containerapp-env.bicep` (conditional
  `vnetConfiguration`); `main.bicep` (`enablePrivateNetworking` param + network
  module + wiring). Covered by `.github/workflows/bicep-validate.yml`.
- AWS: `deploy/aws/uiao_saas_stack.py` (VPC endpoints) + `app.py`
  (`enablePrivateNetworking` context). Covered by `.github/workflows/cdk-synth.yml`.
- Docs: `deploy/azure/README.md`, `deploy/aws/README.md`, and the Azure/AWS
  operator guides note the opt-in flag and the deploy-validation caveat.
