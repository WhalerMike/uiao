# OrgTreeValidation (PowerShell module)

Companion to canon **UIAO_159** ("OrgTree PowerShell Validation Module").
Implements the seven cmdlets described in UIAO_159 against M365
GCC-Moderate tenants via the Microsoft Graph PowerShell SDK.

> **Authority model.** Python is the canonical implementation of
> OrgTree validation logic
> (`src/uiao/modernization/orgtree/*.py`, exposed through
> `uiao orgtree validate ...`). This PowerShell module is the
> **M365-admin UX layer** — pwsh-native cmdlets for tenant-side work
> that genuinely benefits from the Graph PowerShell SDK (paging,
> `Connect-MgGraph` flow). Where logic overlaps, the .psm1 either
> calls back to the Python CLI (`Invoke-UiaoOrgTreeValidate`) or uses
> a small offline implementation that is parity-tested against the
> Python source-of-truth (the canonical OrgPath regex from UIAO_151).

## Cmdlets

| Cmdlet | Tenant-scope? | Pester-tested? | Canon |
|---|---|---|---|
| `Test-OrgPathFormat` | offline | ✓ | UIAO_151 §regex |
| `Test-OrgPathHierarchy` | offline | ✓ | UIAO_151 §hierarchy |
| `Get-OrgTreeValidationReport` | live tenant | manual | UIAO_159 §F3 |
| `Test-DynamicGroupAlignment` | live tenant | manual | UIAO_152 / UIAO_159 §F4 |
| `Export-OrgTreeSnapshot` | live tenant | manual | UIAO_159 §F5 |
| `Compare-OrgTreeSnapshots` | offline | ✓ | UIAO_159 §F6 |
| `Invoke-UiaoOrgTreeValidate` | wrapper | (CLI is tested) | bridges to Python |

## Install

```powershell
# Once: enable PSGallery dependency
Install-Module Microsoft.Graph -Scope CurrentUser

# Per-clone: load the module from the repo
Import-Module ./tools/powershell/OrgTreeValidation/OrgTreeValidation.psm1
```

## Run Pester locally

```powershell
Invoke-Pester ./tools/powershell/OrgTreeValidation/tests
```

CI runs the same suite on `ubuntu-latest` with `pwsh` preinstalled
(see `.github/workflows/pester.yml`).

## Examples

Aggregate offline corpus check (delegates to the Python CLI):

```powershell
$result = Invoke-UiaoOrgTreeValidate
$result.Passed   # -> $true
```

Tenant-side OrgPath audit (live):

```powershell
$report = Get-OrgTreeValidationReport `
    -TenantId  $env:TENANT_ID `
    -CodebookPath ./codebook.json
$report.DriftDetected   # -> $true / $false
```

Diff two snapshots offline:

```powershell
$drift = Compare-OrgTreeSnapshots `
    -BaselinePath ./baseline.json `
    -CurrentPath  ./current.json
$drift | Format-Table
```

## Boundary

GCC-Moderate (M365 SaaS only). All Graph calls use scopes documented
inline; no Azure Resource Manager calls; no commercial-cloud APIs.
