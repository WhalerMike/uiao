---
document_id: IFO_013
title: "Platform Annex — Arc-Managed Servers"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-13"
updated_at: "2026-05-14"
boundary: GCC-Moderate
canon_anchor: ADR-067
platform: server
publish_to_site: true
publication_style: narrative
published_at: docs/modernization/intune-first.qmd
---

# Platform Annex — Arc-Managed Servers

> Per-platform implementation of the five-phase Intune-first process
> for net-new servers. Process is the same as in
> [`../process.md`](../process.md); this annex specifies the
> server-specific mechanics.
>
> **Default management plane:** Azure Arc, with policy delivery via
> Azure Policy Guest Configuration and (where supported) the Intune
> Settings Catalog for Arc-enabled servers.
>
> **Canonical join target:** Microsoft Entra Join via the
> AADLoginForWindows extension (Windows Server 2025+) or
> Microsoft Entra Join equivalent for Linux servers via SSH-key
> integration.
>
> **Controlling precedent:** [ADR-002](../../../canon/adr/adr-002-arc-entra-join-no-domain-join.md) — Arc-Enabled Servers Require Non-Domain-Joined State. This annex operates entirely within ADR-002's constraint and treats it as the day-zero target for net-new servers.

---

## Phase 1 — Procure (server-specific)

The Phase 1 mechanics in [`../process.md`](../process.md) apply with
server-specific intake fields:

- `asset_class` = `windows-server` or `linux-server`
- `vendor_program` = `arc-direct`
- `asset_assignment_type` is typically `service` for servers (the
  asset belongs to the operating team, not to an end user)
- `recipient_upn` is the operating team's service-account UPN, not an
  end-user UPN
- `recipient_orgpath` is the operating team's OrgPath
- `asset_orgpath` = `recipient_orgpath` for service assignments

Additional server-specific fields:

| Field | Type | Validation |
|---|---|---|
| `os_version` | string | One of: `windows-server-2025`, `windows-server-2022`, `windows-server-2019`, `rhel-9`, `rhel-8`, `ubuntu-22-04`, `ubuntu-20-04`, `sles-15`, `oracle-linux-9`, `oracle-linux-8` |
| `hosting_environment` | enum | One of: `on-prem-datacenter`, `colo-facility`, `non-azure-cloud-aws`, `non-azure-cloud-gcp`, `azure-vm`, `azure-stack`, `edge-deployment` |
| `arc_resource_group` | string | The Azure resource group the Arc-enabled machine resource will land in; must follow the organizational naming convention |
| `arc_subscription` | string | The Azure subscription Arc onboarding writes to; must be the governance-managed subscription |

Servers in the `azure-vm` hosting environment are **NOT** Arc
candidates — Azure VMs are managed natively by Azure RM, not by Arc.
Arc applies only to servers outside Azure or in Azure Stack.

The Windows Server 2019 / 2022 selections automatically trigger
exception path C per [`../doctrine.md`](../doctrine.md) §4
(pre-Server-2025 cannot use AADLoginForWindows; Arc-managed-only is
the interim state).

---

## Phase 2 — Pre-stage (Arc onboarding token issuance)

Arc has no equivalent to Autopilot's Group Tag or ABM's device note
written into a vendor-program record. Pre-staging for Arc instead
takes the form of:

### 2.1 — Arc onboarding script generation

The procurement system generates an Arc onboarding script (PowerShell
for Windows, shell for Linux) per server using the `azcmagent`
tooling. The script is parameterized with:

- Tenant ID
- Subscription ID
- Resource group (`arc_resource_group` from the procurement record)
- Location (Azure region — typically the geographic region nearest
  the server's `hosting_environment`)
- Resource tags — including `OrgPath:{asset_orgpath}` and
  `OrgNodeId:{asset_orgnodeid}`
- Onboarding service principal credentials (short-lived, scoped to
  the resource group)

The script is written to a secure handoff location accessible to the
server's deployment team (a shared secrets vault, an out-of-band
deployment artifact store, or a one-time-use SAS URL). The script's
service principal credentials expire 7 days after generation; this
bounds the window during which a leaked script could provision an
unauthorized resource.

### 2.2 — Resource group preparation

The target resource group must exist and have:

- The Azure Arc onboarding RBAC role assignment for the procurement
  service principal
- Resource lock against accidental deletion
- Tags identifying it as an Intune-first-onboarded server resource
  group: `governance-onboarded: intune-first`,
  `orgtree-segment: {top-level-OrgPath-segment}`

Resource groups are created and configured by governance pipeline
infrastructure-as-code, not ad-hoc.

### 2.3 — Cross-reference back to procurement record

The procurement system writes the Arc onboarding token reference,
target resource group, and onboarding script artifact location back
to the procurement record's `vendor_program_records` array.

---

## Phase 3 — Position (server mechanics)

Mapping file:

```
governance/arc/orgpath-mapping.csv
```

with columns: `ServerName`, `SerialNumber`, `OrgPath`, `OrgNodeId`,
`Source`, `AssignmentType`, `OperatingTeamUPN`, `OS`,
`HostingEnvironment`, `ArcResourceGroup`, `ArcSubscription`.

Server-specific dry-run validation:

1. The pipeline validates the Arc onboarding script content by parsing
   it and confirming:
   - Tenant ID, subscription ID, resource group match the procurement
     record
   - Resource tags include `OrgPath` and `OrgNodeId` matching
     procurement
   - Onboarding service principal credentials are non-expired
2. The pipeline validates the target resource group exists, has the
   required RBAC, and has the required tags
3. The pipeline validates the OS version is permitted (Windows Server
   2025+ for full Intune-first; Windows Server 2019/2022 trigger
   exception path C; Linux always triggers exception path B if
   intended for endpoint use, otherwise standard Arc path)

---

## Phase 4 — Provision (Arc onboarding execution)

### 4.1 — Server power-on and OS installation

The server is racked, powered on, and the OS is installed per
standard build procedures. For server build, this is typically:

- Windows Server: ISO-based install, MDT/Configuration Manager build,
  or vendor pre-installed image
- Linux: PXE / kickstart / cloud-init / ignition

The OS install does not include AD domain-join. For Windows Server,
the install completes with the server in a **WORKGROUP** state.
This is the doctrinal precondition for Arc onboarding (per ADR-002).

### 4.2 — Arc onboarding script execution

The deployment team retrieves the Arc onboarding script from the
secure handoff location and executes it on the server. The script:

1. Installs the `azcmagent` package
2. Connects the server to Azure Arc using the embedded service
   principal credentials
3. Writes the resource tags (including `OrgPath` and `OrgNodeId`) to
   the Arc-enabled machine resource
4. Reports successful onboarding via the Arc service callback

### 4.3 — Entra-join via AADLoginForWindows extension

For Windows Server 2025+:

The procurement system's post-Arc-onboarding job (Azure Function or
Logic App) detects the new Arc-enabled machine resource. The job:

1. Verifies the server is in WORKGROUP state (per ADR-002 — must not
   be domain-joined)
2. Installs the AADLoginForWindows extension on the Arc-enabled
   machine via Azure Resource Manager
3. The extension joins the server to Entra ID and configures
   Entra ID-based RDP authentication

For Windows Server 2019 / 2022 (exception path C):

AADLoginForWindows is not available. The server remains Arc-managed-
only. Local administrator access uses the legacy mechanism (LAPS
where available, or standard local admin per organizational policy)
until OS upgrade.

For Linux servers:

The Arc agent provides Azure-managed identity to the server. SSH
access via Entra ID-issued SSH certificates is configured via the
AADLoginForLinux Arc extension (where supported by the Linux
distribution). The Arc Connected Machine agent reports OS posture
and policy compliance.

### 4.4 — OrgPath stamping (server-specific)

Servers don't have an Entra ID device object in the same way
endpoints do — the Entra-join via AADLoginForWindows produces a
device object, but the canonical OrgPath carrier for an Arc-enabled
server is the **Azure resource tag** on the Arc-enabled machine
resource.

The OrgPath stamping flow:

1. Arc onboarding writes resource tags including `OrgPath` and
   `OrgNodeId` to the Arc-enabled machine resource (Phase 4.2 step 3)
2. For Entra-joined Windows Server 2025+, the AADLoginForWindows
   extension creates an Entra device object; the post-onboarding job
   writes the OrgPath extension attribute to that device object as
   well (mirror with the resource tag)
3. The governance pipeline treats the resource tag as the source of
   truth for Arc-managed servers; the Entra device object's OrgPath
   attribute is a mirror for cross-referencing with endpoint
   compliance dashboards

The dual carrier (resource tag AND device object attribute) is
specific to Entra-joined servers. For non-Entra-joined servers
(Linux, Windows Server 2019/2022), only the resource tag is used.

### 4.5 — Policy delivery

Policy delivery for Arc-enabled servers uses **Azure Policy Guest
Configuration** rather than Intune Settings Catalog (which has
limited Arc coverage as of 2026):

- Azure Policy assignments target the Arc resource group or
  individual Arc resources by tag (the OrgPath tag)
- Guest Configuration definitions deliver DSC-based desired state
  configuration to the server
- Compliance is reported back to Azure Policy

Where Intune Settings Catalog supports Arc-enabled servers (a
growing surface as Microsoft expands Settings Catalog to Arc), the
catalog policy is the preferred delivery mechanism. Today the
default for net-new Arc onboarding is Guest Configuration with
catalog as opt-in for specific policies.

### 4.6 — First compliance evaluation

Compliance evaluation for Arc-enabled servers happens via:

- Azure Policy compliance state — for Guest Configuration-delivered
  policies, evaluated on the server check-in interval (default 15
  minutes)
- Microsoft Defender for Servers — for security posture assessment,
  evaluated continuously
- The OrgPath drift detection for resource tag drift — evaluated by
  the governance pipeline

A server is "compliant" when its Azure Policy compliance state for
the assigned policy initiative is `Compliant` or `Exempt`.

---

## Phase 5 — Validate (server-specific checks)

The full validation checklist is in
[`../validation-and-evidence.md`](../validation-and-evidence.md).
Server-specific items:

- [ ] Server is in WORKGROUP state (Windows) — `(Get-WmiObject
      Win32_ComputerSystem).PartOfDomain` returns `False`
- [ ] Arc-enabled machine resource exists in the procurement-
      designated resource group
- [ ] Arc-enabled machine resource carries `OrgPath` and `OrgNodeId`
      tags matching procurement record
- [ ] (Windows Server 2025+) AADLoginForWindows extension is
      installed and the server is Entra-joined; the Entra device
      object carries the OrgPath extension attribute
- [ ] (Windows Server 2019/2022) Exception path C grant exists in
      the governance audit log
- [ ] (Linux) Arc Connected Machine agent reports compliant agent
      version
- [ ] Azure Policy initiative for the server's OrgPath segment is
      assigned and reports `Compliant` or `Exempt`
- [ ] Microsoft Defender for Servers is enabled in the resource
      group's subscription
- [ ] No legacy AD domain-join artifacts present

---

## Anti-patterns explicitly forbidden

- **Domain-joining the server** before or after Arc onboarding.
  Forbidden by ADR-002.
- **Hybrid identity** — server in workgroup state per ADR-002, but
  also added to Entra Domain Services. ADR-002 §Decision explicitly
  forbids this.
- **AADLoginForWindows on Windows Server 2019 / 2022.** Not
  supported; ADR-002 §Negative item 4.
- **Bypassing Arc onboarding** in favor of direct Azure Policy
  Guest Configuration with on-prem-installed agent. The Arc
  onboarding is the canonical entry point for non-Azure servers
  into the governance plane.
- **Net-new server in an Azure-VM hosting environment using Arc.**
  Azure VMs are governed by native Azure mechanisms; Arc onboarding
  for Azure VMs is supported but operationally unnecessary.
- **Local administrator account creation outside the procurement-
  recorded `OperatingTeamUPN`** — for Entra-joined servers, RDP
  access uses Azure RBAC; legacy local admin accounts proliferate
  the AD-era pattern of standing privilege.

---

## Hosting-environment-specific notes

### On-prem datacenter / colo

Arc onboarding requires outbound HTTPS connectivity to Azure
endpoints (`*.servicebus.windows.net`, `*.azuredatabricks.net`,
`management.azure.com`, etc.). For on-prem datacenters with
egress restrictions, the network team must allow these endpoints
or configure an Arc Private Link.

### Non-Azure cloud (AWS / GCP)

Arc supports onboarding from AWS EC2 and GCP Compute Engine
instances. Onboarding mechanics are the same as on-prem, with
network connectivity provided by the cloud provider's VPC.

### Azure Stack HCI / Edge

Arc onboarding from Azure Stack HCI follows the same pattern. Edge
deployments may require Arc Private Link if network access to
public Azure endpoints is restricted.

---

## Differences from endpoint platforms

| Aspect | Endpoints (Win/Mac/iOS/Android) | Servers (Arc) |
|---|---|---|
| Vendor enrollment program | Autopilot / ABM / Zero-Touch / KME | Arc onboarding script |
| OrgPath carrier | Vendor program record (Group Tag, device note, custom JSON) | Azure resource tag on Arc machine resource |
| Trust elevation state | Entra Join (Windows) / Supervised (Apple) / Device Owner (Android) | WORKGROUP + Arc-onboarded; AADLoginForWindows extension if Windows Server 2025+ |
| Policy delivery | Intune Settings Catalog / configuration profiles | Azure Policy Guest Configuration; Settings Catalog opt-in |
| Compliance evaluation | Intune compliance policies | Azure Policy compliance + Defender for Servers |
| Initial state | OOBE / Setup Assistant / Setup Wizard | OS install + Arc onboarding script execution |
| OrgPath stamping | Runtime script (Windows) / Intune-side function (Apple/Android) | Resource tag at Arc onboarding (always) + Entra device object (Server 2025+ only) |
| Identity-plane integration | Entra ID device object | Arc machine resource ± Entra device object (Server 2025+ only) |

---

## References

- [ADR-002 — Arc-Enabled Servers Require Non-Domain-Joined](../../../canon/adr/adr-002-arc-entra-join-no-domain-join.md) (controlling precedent for server identity)
- [Microsoft Learn — Azure Arc-enabled servers overview](https://learn.microsoft.com/en-us/azure/azure-arc/servers/overview)
- [Microsoft Learn — Azure Arc onboarding methods](https://learn.microsoft.com/en-us/azure/azure-arc/servers/onboard-portal)
- [Microsoft Learn — Microsoft Entra ID authentication for Azure Arc-enabled servers](https://learn.microsoft.com/en-us/azure/azure-arc/servers/ssh-arc-overview)
- [Microsoft Learn — Azure Policy Guest Configuration overview](https://learn.microsoft.com/en-us/azure/governance/machine-configuration/overview)
