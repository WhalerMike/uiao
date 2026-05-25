# `scripts/uiao-env-pack/` — UIAO PowerShell Pack

Offline-installable, downloadable bundle of the PowerShell 7 runtime
plus a curated set of modules and third-party tools, built to drop
onto a UIAO operator workstation with no internet / no PSGallery
access required at install time.

The pack is built locally from a manifest, uploaded to GitHub
Releases as a single zip, and installed offline by the bundled
`Install-UIAOPack.ps1`.

## Pack contents

Defined in [`manifest.json`](./manifest.json):

| Section | What it carries | Install action |
|---|---|---|
| `runtime.powershell` | PowerShell 7 MSI from PowerShell/PowerShell releases | `msiexec /i ... /quiet` |
| `modules[]` | PSGallery modules fetched via `Save-Module` | Copy into `$PSModulePath` target |
| `dev_modules[]` | Local-path or Git-source modules | Re-bind via `Install-DevModule` (PoShDevModules) or file copy |
| `tools[]` | Third-party installers (git, gh, etc.) | Silent MSI / EXE install per `silent_args` |

Every downloaded artifact has its SHA256 recorded in the resolved
manifest inside the zip. The offline installer verifies hashes
before executing.

## Constraints honored

These scripts follow UIAO substrate authoring rules:

- no backticks
- no line-continuation characters
- no heredocs
- line-by-line, deterministic, machine-trackable
- offline installer has zero PowerShell module dependencies (uses built-in `ConvertFrom-Json`)

## Scripts

| Script | Role | Where it runs |
|---|---|---|
| [`Build-UIAOPack.ps1`](./Build-UIAOPack.ps1) | Read manifest, download pwsh MSI + `Save-Module` everything + download tool installers, compute SHA256s, write resolved manifest, zip the stage tree | Developer workstation (online) |
| [`Install-UIAOPack.ps1`](./Install-UIAOPack.ps1) | Read bundled manifest, verify hashes, install pwsh silently, copy modules into `$PSModulePath`, install tools silently | Target operator workstation (offline) |
| [`Export-UIAOEnvironment.ps1`](./Export-UIAOEnvironment.ps1) | Capture current host's PowerShell substrate to CSV ledgers | Verification helper |
| [`Import-UIAOEnvironment.ps1`](./Import-UIAOEnvironment.ps1) | Replay CSV ledgers via online `Install-Module` | Verification helper |
| [`Compare-UIAOEnvironment.ps1`](./Compare-UIAOEnvironment.ps1) | Diff current host state against ledger CSVs | Verification helper |

The `Export` / `Import` / `Compare` trio is the original inventory
pipeline — kept around because it's the cleanest way to audit "what
actually got installed on this host" after running the pack.

## Build → Release → Install flow

### 1. Edit `manifest.json`

Bump `pack.version` (patch by default — third digit), pin module
versions, update runtime / tool URLs as upstream releases new
versions.

### 2. Build the pack locally

```powershell
& C:\Users\whale\git\uiao\scripts\uiao-env-pack\Build-UIAOPack.ps1
```

Produces:

```
scripts/uiao-env-pack/build/
    uiao-pwsh-pack-<version>/      (staged tree)
    uiao-pwsh-pack-<version>.zip   (release artifact)
```

`build/` and `*.zip` are gitignored — never committed.

### 3. Upload to GitHub Releases

```powershell
gh release create v<version> .\build\uiao-pwsh-pack-<version>.zip --title "UIAO PowerShell Pack v<version>" --notes "See README.md inside the zip"
```

Operators download the zip from the release page.

### 4. Install on a target operator workstation

```powershell
Expand-Archive .\uiao-pwsh-pack-<version>.zip -DestinationPath C:\uiao-pack
& C:\uiao-pack\uiao-pwsh-pack-<version>\Install-UIAOPack.ps1
```

Runs Step 01–05: pwsh runtime, modules, dev modules, tools, verify.
Use `-ModuleScope Machine` to install modules system-wide instead
of the default user scope. Use `-SkipRuntime` / `-SkipTools` to
narrow the install.

## Manifest schema

```json
{
  "schema_version": 1,
  "pack": { "name": "...", "version": "X.Y.Z", "description": "..." },
  "runtime": {
    "powershell": {
      "version": "...", "url": "...", "filename": "...",
      "sha256": null,
      "silent_args": ["/quiet", "/norestart", "..."]
    }
  },
  "modules": [
    { "name": "...", "version": "latest|X.Y.Z", "source": "psgallery" }
  ],
  "dev_modules": [
    { "name": "...", "source": "git", "url": "https://..." },
    { "name": "...", "source": "path", "path": "C:\\..." }
  ],
  "tools": [
    {
      "name": "...", "version": "...", "url": "...", "filename": "...",
      "sha256": null,
      "silent_args": ["..."]
    }
  ]
}
```

`sha256` fields are `null` in the source manifest; `Build-UIAOPack.ps1`
fills them in the resolved manifest written into the zip.

## Verification helpers (inventory pipeline)

For auditing a target host after install, or capturing a known-good
substrate to seed a new manifest:

### Capture this host's state

```powershell
& C:\Users\whale\git\uiao\scripts\uiao-env-pack\Export-UIAOEnvironment.ps1 -OutputDirectory C:\uiao-env-ledger
```

Produces `packages.csv`, `modules.csv`, `devmodules.csv`.

### Compare against a reference ledger

```powershell
& C:\Users\whale\git\uiao\scripts\uiao-env-pack\Compare-UIAOEnvironment.ps1 -InputDirectory C:\uiao-env-ledger
```

Emits `*.current.csv` and `*.drift.csv`. Clean install = zero drift rows.

### Online replay (alternative to offline pack)

```powershell
& C:\Users\whale\git\uiao\scripts\uiao-env-pack\Import-UIAOEnvironment.ps1 -InputDirectory C:\uiao-env-ledger
```

Uses `Install-Module` against PSGallery. Requires internet. The
offline pack is the preferred path for restricted environments.

## Edition note

PowerShell 7 (Core) and Windows PowerShell 5.1 (Desktop) have
separate module paths. The pack installs pwsh 7 and targets pwsh 7
module paths (`Documents\PowerShell\Modules`). After installing the
pack, switch your terminal default to `pwsh.exe` so the modules
are visible.

Verification helper export honors the edition allowlist
(`-ReplicableProviders`, default `PowerShellGet, NuGet, Chocolatey`)
so a 5.1 export does not pull the 1000+ msu/msi/Programs firehose.
Use `-IncludeSystemProviders` only for audit, not for replication.

## Failure semantics

`Install-UIAOPack.ps1` runs with `Continue` semantics by default —
per-item failures log `FAIL` and the install proceeds. Use
`-StrictInstall` to abort on the first failure. `Build-UIAOPack.ps1`
runs with `Stop` semantics — any download or `Save-Module` failure
aborts the build so a half-built pack is never produced.
