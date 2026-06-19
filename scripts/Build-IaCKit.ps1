<#
.SYNOPSIS
    Build-IaCKit.ps1
    Assembles the UIAO Cloud SaaS IaC Kit zip.

.DESCRIPTION
    Gathers the infrastructure-as-code for deploying the multi-tenant UIAO SaaS
    plane on either cloud — the Azure Bicep templates (deploy/azure) and the AWS
    CDK app (deploy/aws) — plus a cross-cloud DEPLOY runbook, into a single zip
    an operator can download, verify, and deploy from. This is the offline /
    air-gapped / hand-off companion to the in-repo deploy directories.

    Cross-platform: runs under PowerShell 7 (pwsh) on Linux or Windows, so the
    CI build (iac-kit-build.yml) runs it on ubuntu-latest.

    Output: dist/uiao-iac-kit-<version>.zip

.PARAMETER Version
    Version string to embed in the zip filename (default: reads from
    src/uiao/__version__.py).

.PARAMETER OutDir
    Output directory for the zip (default: dist/).

.EXAMPLE
    pwsh ./scripts/Build-IaCKit.ps1
    pwsh ./scripts/Build-IaCKit.ps1 -Version "1.0.0" -OutDir dist
#>
[CmdletBinding()]
param(
    [string]$Version = "",
    [string]$OutDir  = "dist"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# Resolve version from __version__.py if not supplied.
if (-not $Version) {
    $verFile = Join-Path $RepoRoot "src/uiao/__version__.py"
    if (Test-Path $verFile) {
        $line = (Get-Content $verFile) | Where-Object { $_ -match '__version__' } | Select-Object -First 1
        if ($line -match '"([^"]+)"') { $Version = $Matches[1] }
    }
    if (-not $Version) { $Version = "0.0.0" }
}

Write-Host "Building UIAO Cloud SaaS IaC Kit v$Version" -ForegroundColor Cyan

# Staging directory.
$Stage = Join-Path ([System.IO.Path]::GetTempPath()) "uiao-iac-kit-$Version"
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Path $Stage | Out-Null

# ── Azure (Bicep) ───────────────────────────────────────────────────────────
$AzureSrc = Join-Path $RepoRoot "deploy/azure"
$AzureDst = Join-Path $Stage "azure"
if (Test-Path $AzureSrc) {
    Copy-Item $AzureSrc -Destination $AzureDst -Recurse
    Write-Host "  + azure/ (Bicep templates + Dockerfile + README)" -ForegroundColor DarkGray
} else {
    Write-Warning "  ! deploy/azure not found"
}

# ── AWS (CDK) ───────────────────────────────────────────────────────────────
$AwsSrc = Join-Path $RepoRoot "deploy/aws"
$AwsDst = Join-Path $Stage "aws"
if (Test-Path $AwsSrc) {
    Copy-Item $AwsSrc -Destination $AwsDst -Recurse
    # Drop any local CDK build artefacts that should never ship in the kit.
    foreach ($junk in @("cdk.out", ".venv", "__pycache__")) {
        Get-ChildItem $AwsDst -Recurse -Force -Filter $junk -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  + aws/ (CDK app + README)" -ForegroundColor DarkGray
} else {
    Write-Warning "  ! deploy/aws not found"
}

# ── Cross-cloud DEPLOY runbook ──────────────────────────────────────────────
$DeployMd = Join-Path $Stage "DEPLOY.md"
[System.IO.File]::WriteAllText($DeployMd, @"
# UIAO Cloud SaaS — Deployment Runbook (v$Version)

The multi-tenant UIAO SaaS plane runs the same application on either cloud.
Pick one. Both deployments are **passwordless** at the data tier — the workload's
own identity authenticates to the database; there is no database password to
manage.

## Azure (Container Apps + PostgreSQL)

    cd azure
    # 1. Stamp infrastructure (passwordless Postgres — no DB password to pass)
    az deployment group create -g <rg> \
      -f bicep/main.bicep -p bicep/main.bicepparam
    # 2. Build + push the image
    az acr build --registry <acr> --image uiao-saas:latest --file Dockerfile .
    # 3. Re-deploy at the pushed image
    az deployment group create -g <rg> -f bicep/main.bicep \
      -p bicep/main.bicepparam -p containerImage="<acr>.azurecr.io/uiao-saas:latest"

Full guide: https://whalermike.github.io/uiao/customer-documents/platform/azure-saas.html

## AWS (ECS Fargate + RDS)

    cd aws
    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    npm install -g aws-cdk@2
    cdk synth -c environmentName=dev          # validate (no account needed)
    cdk bootstrap                             # once per account/region
    cdk deploy -c environmentName=dev \
      -c imageUri=<acct>.dkr.ecr.<region>.amazonaws.com/uiao-saas:latest

After the first AWS deploy, run the one-time DB role bootstrap in aws/README.md
(CREATE USER uiao_app; GRANT rds_iam TO uiao_app;).

Full guide: https://whalermike.github.io/uiao/customer-documents/platform/aws-saas.html

License: Apache-2.0. See https://github.com/WhalerMike/uiao
"@, [System.Text.UTF8Encoding]::new($false))
Write-Host "  + DEPLOY.md" -ForegroundColor DarkGray

# ── README ──────────────────────────────────────────────────────────────────
$ReadmePath = Join-Path $Stage "README.txt"
[System.IO.File]::WriteAllText($ReadmePath, @"
UIAO Cloud SaaS IaC Kit v$Version
=================================

The infrastructure-as-code to deploy the multi-tenant UIAO SaaS governance
plane on Azure or AWS. The application is identical on both clouds; only the
deployment substrate differs.

Contents
--------
  azure/        - Azure Bicep templates (main.bicep + modules), Dockerfile,
                  bicepparam, and the Azure operator README. Deploys Container
                  Apps + PostgreSQL Flexible Server (passwordless Entra auth) +
                  Key Vault + Storage + managed identity.
  aws/          - AWS CDK app (app.py, uiao_saas_stack.py, cdk.json,
                  requirements.txt) and the AWS operator README. Deploys ECS
                  Fargate + ALB + RDS PostgreSQL (passwordless IAM auth) + S3 +
                  IAM task role.
  DEPLOY.md     - Cross-cloud quick-deploy runbook for both targets.

Quick start
-----------
  See DEPLOY.md. Both data tiers are passwordless — no database password.

Governing decisions
-------------------
  ADR-096 (Azure SaaS architecture), ADR-115 (production-readiness),
  ADR-116 (Azure passwordless Postgres), ADR-117 (AWS SaaS surface).

Verify this zip
---------------
  pwsh:        Get-FileHash .\uiao-iac-kit-$Version.zip -Algorithm SHA256
  Linux/macOS: sha256sum uiao-iac-kit-$Version.zip

License: Apache-2.0. See https://github.com/WhalerMike/uiao
"@, [System.Text.UTF8Encoding]::new($false))
Write-Host "  + README.txt" -ForegroundColor DarkGray

# ── Zip ─────────────────────────────────────────────────────────────────────
$OutPath = Join-Path $RepoRoot $OutDir
if (-not (Test-Path $OutPath)) { New-Item -ItemType Directory -Path $OutPath | Out-Null }
$ZipName = "uiao-iac-kit-$Version.zip"
$ZipPath = Join-Path $OutPath $ZipName

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path "$Stage/*" -DestinationPath $ZipPath
$Hash = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLower()

Write-Host ""
Write-Host "Kit: $ZipPath" -ForegroundColor Green
Write-Host "SHA-256: $Hash" -ForegroundColor Green

# Clean up staging.
Remove-Item $Stage -Recurse -Force
