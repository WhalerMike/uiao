# `scripts/uiao-env-pack/` — PowerShell Environment Replication Pack

Deterministic export / replicate / drift-check of the PowerShell
substrate on a UIAO operator workstation. Three CSV ledgers describe
the substrate completely:

| Ledger | Source command | Captures |
|---|---|---|
| `packages.csv` | `Get-Package` | PackageManagement packages (NuGet, Chocolatey, etc.) |
| `modules.csv` | `Get-InstalledModule` | PowerShell modules from PSGallery / private repos |
| `devmodules.csv` | `Get-InstalledDevModule` | Local / Git path modules registered via PoShDevModules |

## Constraints honored

These scripts follow UIAO substrate authoring rules:

- no backticks
- no line-continuation characters
- no heredocs
- line-by-line, deterministic, machine-trackable
- rows sorted before export so CSVs diff cleanly across runs

## Edition note

PowerShell 7 (Core) and Windows PowerShell 5.1 (Desktop) have
separate module paths and separate `Get-Package` provider
populations. Export from whichever edition is your daily driver:

| Edition | Module path | Typical `Get-Package` |
|---|---|---|
| pwsh 7 (`pwsh.exe`) | `~\Documents\PowerShell\Modules` | small — PowerShellGet / NuGet only |
| Windows PowerShell 5.1 (`powershell.exe`) | `~\Documents\WindowsPowerShell\Modules` | huge — adds msu / msi / Programs (1000+ rows on a typical workstation) |

The default provider allowlist (`PowerShellGet`, `NuGet`,
`Chocolatey`) drops the 5.1 system firehose so both editions
produce comparable ledgers. Use `-IncludeSystemProviders` if you
need the firehose for audit/governance (it is **not** replicable).

## Scripts

| Script | Purpose |
|---|---|
| `Export-UIAOEnvironment.ps1` | Capture current host state to `packages.csv`, `modules.csv`, `devmodules.csv` |
| `Import-UIAOEnvironment.ps1` | Replay ledgers on a new host: bootstrap NuGet + PowerShellGet, install packages/modules, re-bind dev modules, emit drift report |
| `Compare-UIAOEnvironment.ps1` | Standalone drift detection — capture current state to `*.current.csv` and diff against source ledgers into `*.drift.csv`, without re-installing |

`Import-UIAOEnvironment.ps1` runs the drift report inline after
replication. Use `-SkipDriftReport` plus a separate
`Compare-UIAOEnvironment.ps1` invocation when you want to control
the two stages independently.

## Canonical workflow

### 1. Export from the source workstation

```powershell
mkdir C:\uiao-env-ledger
Set-Location C:\uiao-env-ledger
& C:\Users\whale\git\uiao\scripts\uiao-env-pack\Export-UIAOEnvironment.ps1 -OutputDirectory .
```

Produces:

```
packages.csv
modules.csv
devmodules.csv
```

### 2. Replicate on the target workstation

Copy the three CSVs to the target, then:

```powershell
Set-Location C:\uiao-env-ledger
& C:\Users\whale\git\uiao\scripts\uiao-env-pack\Import-UIAOEnvironment.ps1 -InputDirectory .
```

Steps run in order: 01 ingest ledgers → 02 bootstrap NuGet +
PowerShellGet → 03 install packages → 04 install modules → 05
re-bind dev modules → 06 capture current state → 07 emit drift CSVs.

### 3. Drift check on demand

To check drift at any later time, without re-installing:

```powershell
& C:\Users\whale\git\uiao\scripts\uiao-env-pack\Compare-UIAOEnvironment.ps1 -InputDirectory C:\uiao-env-ledger
```

## Ledgers produced

| File | Written by | Meaning |
|---|---|---|
| `packages.csv` | Export | Source state — PackageManagement packages |
| `modules.csv` | Export | Source state — gallery modules |
| `devmodules.csv` | Export | Source state — PoShDevModules dev modules |
| `packages.current.csv` | Import / Compare | Observed state on target host |
| `modules.current.csv` | Import / Compare | Observed state on target host |
| `devmodules.current.csv` | Import / Compare | Observed state on target host |
| `packages.drift.csv` | Import / Compare | `Compare-Object` delta on `Name, Version, ProviderName` |
| `modules.drift.csv` | Import / Compare | `Compare-Object` delta on `Name, Version` |
| `devmodules.drift.csv` | Import / Compare | `Compare-Object` delta on `Name, Path` |

## Reading the drift ledgers

The drift CSVs come from `Compare-Object`. The `SideIndicator`
column tells you which side an entry is on:

| SideIndicator | Meaning |
|---|---|
| `<=` | Present in source ledger, missing on target — replication gap |
| `=>` | Present on target, missing from source ledger — target carries extras |

A clean replication shows **zero rows** in all three `*.drift.csv` files.

## Failure semantics

`Import-UIAOEnvironment.ps1` runs with
`$ErrorActionPreference = "Continue"` inside the install loops so a
single failed package or module does not abort the run. Each row
logs `OK`, `FAIL`, or `SKIP` with context:

| Status | Meaning |
|---|---|
| `OK` | `Install-Package` / `Install-Module` / `Install-DevModule` succeeded |
| `FAIL` | Replicable-provider row but install threw — exception message logged |
| `SKIP` | Row whose `ProviderName` is outside the `-ReplicableProviders` allowlist (msu, msi, Programs from a firehose export) |

The drift ledger captures whatever was actually installed, so the
post-run CSV is the ground truth even when individual installs
failed.

`Export-UIAOEnvironment.ps1` and `Compare-UIAOEnvironment.ps1` use
`Stop` semantics — they should run cleanly or be investigated.

## Provider filtering

All three scripts share the same default replicable-provider
allowlist:

```
PowerShellGet
NuGet
Chocolatey
```

Override via `-ReplicableProviders` (string array). Bypass entirely
via `-IncludeSystemProviders` (capture every provider — useful for
audit, not for replication).

## Bootstrapping a host with no PoShDevModules

If `devmodules.csv` has entries but the target host lacks
PoShDevModules, `Import-UIAOEnvironment.ps1` step 05 will install
it from PSGallery before processing the dev-module rows. If the
PSGallery bootstrap itself fails, the dev-module rows are reported
as `FAIL` and the drift ledger shows them as `<=` (missing on
target). Re-run after fixing connectivity / PSGallery trust.
