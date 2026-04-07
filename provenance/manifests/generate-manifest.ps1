param(
    [Parameter(Mandatory = $true)]
    [string] $RawFilePath,
    [Parameter(Mandatory = $true)]
    [string] $NormalizedFilePath,
    [Parameter(Mandatory = $true)]
    [string] $ReportFilePath,
    [Parameter(Mandatory = $true)]
    [string] $OutputDirectory,
    [string] $AdapterVersion = "1.0",
    [string] $RulesetVersion = "1.0"
)

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

function Get-FileHashString {
    param([string] $Path)
    if (Test-Path $Path) {
        return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash
    }
    return $null
}

$manifestId = "prov-scuba-{0:yyyyMMdd-HHmmss}" -f (Get-Date)

$manifest = [pscustomobject]@{
    manifest_id     = $manifestId
    generated_at    = (Get-Date).ToString("o")
    adapter_version = $AdapterVersion
    ruleset_version = $RulesetVersion
    source_files    = @(
        (Split-Path $RawFilePath -Leaf),
        (Split-Path $NormalizedFilePath -Leaf),
        (Split-Path $ReportFilePath -Leaf)
    )
    hashes = @{
        raw        = Get-FileHashString -Path $RawFilePath
        normalized = Get-FileHashString -Path $NormalizedFilePath
        report     = Get-FileHashString -Path $ReportFilePath
    }
    lineage = @{
        scuba_run_id      = (Split-Path $RawFilePath -Leaf)
        normalization_id  = (Split-Path $NormalizedFilePath -Leaf)
        ksi_evaluation_id = (Split-Path $ReportFilePath -Leaf)
    }
    environment = @{
        host               = $env:COMPUTERNAME
        user               = $env:USERNAME
        os_version         = (Get-CimInstance Win32_OperatingSystem).Caption
        powershell_version = $PSVersionTable.PSVersion.ToString()
    }
}

$manifestPath = Join-Path $OutputDirectory "$manifestId.json"
$manifest | ConvertTo-Json -Depth 6 | Out-File $manifestPath -Encoding UTF8

Write-Host "Provenance manifest generated: $manifestPath"
