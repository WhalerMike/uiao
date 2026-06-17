# UIAO Addressing-Plane Drift Collector

DNS and namespace governance tools for the UIAO addressing plane.
Canon: [UIAO_195](../canon/UIAO_195_Addressing_Plane_Drift_Taxonomy.md) · [ADR-108](../canon/adr/adr-108-addressing-plane-drift-gate.md)

---

## Getting a test environment (no existing tenant)

If you don't have an Azure subscription or Entra tenant yet, the fastest path
is a **standalone Entra ID P2 trial** (30 days, no credit card required for
the identity features alone):

1. Go to `https://entra.microsoft.com` → sign in with any Microsoft account
2. **Identity** → **Billing** → **Licenses** → **Try / Buy** → **Microsoft Entra ID P2** → **Free trial** → **Activate**
3. For a full Azure subscription (needed to create DNS zones): sign up at
   `https://azure.microsoft.com/free` — includes $200 credit and a real tenant

Once you have a subscription, seed it with realistic test zones:

```powershell
az login
.\Initialize-EntraTestEnvironment.ps1   # creates zones + my_bindings.json in .\test-env\

# Then run the full audit against the seeded environment:
.\Invoke-AddressingAudit.ps1 `
    -IntendedBindingsPath .\test-env\my_bindings.json `
    -OutputDirectory      .\test-env\audit
```

The init script seeds intentional drift (DRIFT-DANGLING, DRIFT-CONFLICT, DRIFT-SRV,
DRIFT-SHADOW, DRIFT-ORPHAN) so the audit gate returns HALT — confirming the full
pipeline is working before you point it at a real subscription.

---

## Quick start — Azure DNS (no AD/DC required)

```powershell
# 1. Log in to Azure CLI
az login                                  # interactive browser
az login --use-device-code                # headless / jump box

# GCC-Moderate = commercial infra — no cloud switch needed (AzureCloud is default)
# Azure Government workloads:
#   az cloud set --name AzureUSGovernment

# 2. Copy and populate the SSOT manifest
Copy-Item sample\intended_bindings.json .\my_bindings.json
# Edit my_bindings.json — replace sample names with your agency's governed names,
# targets, and boundary_intent ("private" | "gcc-moderate" | "any")

# 3. Run the full audit
.\Invoke-AddressingAudit.ps1 `
    -IntendedBindingsPath .\my_bindings.json `
    -PrivateResolverIP 10.x.x.x `          # your Private Resolver inbound endpoint IP
    -OutputDirectory C:\Temp\dns-audit-$(Get-Date -Format 'yyyy-MM-dd')
```

Output files written to `-OutputDirectory`:

| File | Contents |
|---|---|
| `observed_zone.json` | All DNS records exported from Azure |
| `resources.json` | Live IP/host inventory (auto-derived from A/AAAA records) |
| `zone_manifest.json` | Zone metadata (name, type, RG, subscription) |
| `findings.json` | Drift-classifier findings (P1/P2/P3, drift_core format) |
| `horizon_findings.json` | DRIFT-HORIZON findings (Private Link bypass, boundary leaks) |
| `horizon_report.txt` | Human-readable forwarder chain status per privatelink.* zone |
| `audit_summary.txt` | Overall gate decision + remediation guidance |

---

## GCC-Moderate dual-cloud pattern

GCC-Moderate runs M365 on **commercial** Azure infrastructure and may have
Azure Government workloads on a **separate** subscription/cloud.
Run the exporter twice and merge:

```powershell
# Commercial (M365 / GCC-M Azure)
.\dns_zone_export_azure.ps1 -OutputDirectory .\audit-commercial

# Azure Government workloads
.\dns_zone_export_azure.ps1 `
    -AzureCloud AzureUSGovernment `
    -SubscriptionId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" `
    -OutputDirectory .\audit-gov

# Merge zone files (simple concat — collector handles duplicates by name)
$zones = (Get-Content .\audit-commercial\observed_zone.json | ConvertFrom-Json) +
         (Get-Content .\audit-gov\observed_zone.json        | ConvertFrom-Json)
$zones | ConvertTo-Json -Depth 5 | Set-Content .\audit-merged\observed_zone.json

# Then run classifier against merged output
python addressing_collector.py `
    --intended my_bindings.json `
    --zone     .\audit-merged\observed_zone.json `
    --resources .\audit-commercial\resources.json `
    --output   .\audit-merged\findings.json
```

---

## AD/DC mode (if you gain DC access later)

```powershell
.\Invoke-AddressingAudit.ps1 `
    -UseAdDnsExport `
    -ZoneName "agency.gov" `
    -IntendedBindingsPath .\my_bindings.json `
    -OutputDirectory .\dns-audit
```

---

## Running the drift classifier standalone

```powershell
python addressing_collector.py `
    --intended intended_bindings.json `
    --zone     observed_zone.json `
    --resources resources.json `
    --output   findings.json
```

Gate: exits 0 on PASS, 1 on HALT (any P1 finding).

---

## Populating `intended_bindings.json`

Use `sample/intended_bindings.json` as the template.

Key fields per binding:

| Field | Required | Notes |
|---|---|---|
| `type` | yes | A / AAAA / CNAME |
| `target` | yes | Expected resolved value |
| `boundary_intent` | recommended | `private` · `gcc-moderate` · `any` |
| `requires_fcrdns` | no | `true` for mail servers, logging endpoints |

`boundary_intent` drives DRIFT-HORIZON severity:
- `private` — name must NOT resolve from external vantage (P1 if it does)
- `gcc-moderate` — resolves from any vantage but must land on correct IP
- `any` — split-horizon acceptable; divergent answers are P2 for review

---

## Drift classes

| Class | Severity | Description |
|---|---|---|
| DRIFT-BINDING | P1/P2 | Governed name resolves to wrong target |
| DRIFT-DANGLING | P1 | Ungoverned record → absent resource (takeover exposure) |
| DRIFT-SHADOW | P1/P2 | Record in zone but not in SSOT |
| DRIFT-SRV | P1 | Missing or dead Kerberos/LDAP/GC locator |
| DRIFT-CONFLICT | P1 | CNAME coexists with other record types (RFC violation) |
| DRIFT-WILDCARD | P2 | Wildcard masks intended-explicit name |
| DRIFT-ORPHAN | P3 | Zone with zero referencing bindings |
| DRIFT-PTR | P2 | FCrDNS required but PTR absent |
| DRIFT-HORIZON | P1/P2 | Private Link bypass / split-horizon boundary leak |
| DRIFT-CAA/TLSA | P1 | Wrong cert issuer (deferred — requires cert inspection) |
| DRIFT-DELEGATION | P1/P2 | NS delegation mismatch (deferred — requires NS walk) |
