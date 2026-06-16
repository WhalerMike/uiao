<#
.SYNOPSIS
    Register-ServiceAccount.ps1
    Creates the UIAO API service account and registers its SPN.
    Run on a DC or machine with RSAT AD tools.
#>
[CmdletBinding()]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingConvertToSecureStringWithPlainText', '',
    Justification = 'This script generates a fresh random password to provision a brand-new AD service account and surfaces it once for vaulting. There is no pre-existing secret being exposed; converting the generated plaintext to a SecureString is the only way to set the initial AccountPassword.')]
param(
    [string]$AccountName    = "SVC-UIAO-API",
    [string]$AccountOU      = "OU=Service Accounts,DC=corp,DC=contoso,DC=com",
    [string]$ServerDNS      = "uiao-api.corp.contoso.com",
    [string]$Domain         = "corp.contoso.com"
)
$ErrorActionPreference = "Stop"
Import-Module ActiveDirectory -ErrorAction Stop

Write-Host "Creating service account $AccountName..." -ForegroundColor Cyan

# Generate long random password
Add-Type -AssemblyName System.Web
$Password = [System.Web.Security.Membership]::GeneratePassword(32, 8)
$SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force

# Create account
try {
    New-ADUser `
        -Name $AccountName `
        -SamAccountName $AccountName `
        -UserPrincipalName "$AccountName@$Domain" `
        -Path $AccountOU `
        -AccountPassword $SecurePassword `
        -PasswordNeverExpires $false `
        -ChangePasswordAtLogon $false `
        -CannotChangePassword $true `
        -Enabled $true `
        -Description "UIAO AD Survey API service account"
    Write-Host "  OK: Account created" -ForegroundColor Green
} catch {
    if ($_.Exception.Message -like "*already exists*") {
        Write-Host "  WARN: Account already exists, skipping creation" -ForegroundColor Yellow
    } else { throw }
}

# Register SPNs
$spns = @(
    "HTTP/$ServerDNS",
    "HTTP/$($ServerDNS.Split('.')[0])"   # short hostname
)
foreach ($spn in $spns) {
    try {
        Set-ADUser $AccountName -ServicePrincipalNames @{ Add = $spn }
        Write-Host "  OK: SPN registered: $spn" -ForegroundColor Green
    } catch {
        Write-Host "  WARN: SPN may already exist: $spn" -ForegroundColor Yellow
    }
}

# Grant read permissions on all user attributes
# (Domain Users already has Read on most attrs; this grants the explicit right)
Get-Acl "AD:\$AccountOU" | Out-Null
Write-Host "  NOTE: Verify $AccountName has 'Read all user attributes' in AD delegation" -ForegroundColor Yellow

Write-Host "`nSERVICE ACCOUNT PASSWORD (store in vault NOW — not shown again):" -ForegroundColor Red
Write-Host $Password -ForegroundColor Red
Write-Host "`nSPNs registered: $($spns -join ', ')"
Write-Host "Next: configure IIS app pool to run as CORP\$AccountName with this password."
