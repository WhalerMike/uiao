# ================================================
# import-batch1.ps1
# Creates 15 Gold Standard control YAML files
# Then commits and pushes them
# ================================================

Set-Location "C:\Users\whale\uiao-core"

$path = "data\control-library"
if (-not (Test-Path $path)) {
    New-Item -Path $path -ItemType Directory -Force | Out-Null
}

Write-Host "Creating Batch 1 of 15 Gold Standard controls..." -ForegroundColor Cyan

$controls = @(
    @{
        id = "AC-2"
        title = "Account Management"
        narrative = @"
{{ organization.name }} manages system accounts through a centralized and automated process using the Identity Provider.

**Account Provisioning**
New accounts are automatically created within {{ parameters.account-creation-window }} of receiving a validated HR feed via SCIM.

**Account Deprovisioning**
Terminated accounts are disabled within {{ parameters.termination-window }} of the HR separation event.

**Periodic Review**
All accounts undergo automated monthly reviews to identify and disable dormant accounts exceeding {{ parameters.inactivity-timeout }} of inactivity.
"@
        implemented_by = @("IdentityProvider", "HRSystem")
        parameters = @{ "account-creation-window" = "24 hours"; "termination-window" = "1 hour"; "inactivity-timeout" = "30 days" }
    },

    @{
        id = "AC-3"
        title = "Access Enforcement"
        narrative = @"
{{ organization.name }} enforces logical access to information and system resources through policy-based mechanisms.

**Conditional Access Enforcement**
All access requests are evaluated in real-time using Conditional Access policies that consider user role, device compliance, location, and risk signals.

**Least Privilege Enforcement**
Access is granted only to the minimum resources required, with explicit deny-by-default rules.
"@
        implemented_by = @("IdentityProvider", "PolicyEnforcementPoint")
        parameters = @{ "session-timeout" = "15 minutes" }
    },

    @{
        id = "AC-6"
        title = "Least Privilege"
        narrative = @"
{{ organization.name }} enforces the principle of least privilege across all systems and applications.

**Role-Based Access**
Users are assigned the minimum permissions necessary to perform their job functions through role-based access control and just-in-time privileged access.

**Privileged Access Management**
Elevated permissions are granted only for the duration of the approved task and are automatically revoked upon completion or timeout.

**Periodic Review**
All privileged accounts and permissions are reviewed every {{ parameters.privilege-review-frequency }} to ensure continued necessity.
"@
        implemented_by = @("PrivilegedAccessManagement", "IdentityProvider")
        parameters = @{ "privilege-review-frequency" = "90 days" }
    },

    @{
        id = "IA-2"
        title = "Identification and Authentication"
        narrative = @"
{{ organization.name }} requires unique identification and authentication for all users, processes, and devices.

**Primary Authentication**
All users authenticate using phishing-resistant multi-factor authentication via the Identity Provider.

**Non-Organizational Users**
Guests and contractors are required to use the same authentication standards with additional sponsor approval.

**Device Authentication**
Managed devices are identified and authenticated using device certificates and compliance checks.
"@
        implemented_by = @("IdentityProvider", "Intune")
        parameters = @{ }
    },

    @{
        id = "IA-5"
        title = "Authenticator Management"
        narrative = @"
{{ organization.name }} manages authenticators using phishing-resistant technologies.

**Authenticator Types**
Primary authenticators are FIDO2/WebAuthn or PIV/CAC.

**Issuance and Revocation**
Authenticators are issued through automated workflows and revoked within {{ parameters.auth-revocation-window }} of compromise or loss.

**Storage**
Cryptographic authenticators are stored in hardware security modules with FIPS 140-3 validation.
"@
        implemented_by = @("IdentityProvider")
        parameters = @{ "auth-revocation-window" = "2 hours" }
    },

    @{
        id = "SC-7"
        title = "Boundary Protection"
        narrative = @"
{{ organization.name }} protects system boundaries using a defense-in-depth approach.

**Edge Protection**
All external traffic is routed through Azure Front Door with Web Application Firewall enabled.

**Internal Segmentation**
Micro-segmentation and Network Security Groups enforce deny-by-default policies between application tiers.

**Monitoring**
All boundary traffic is logged and monitored in real-time by the Telemetry Plane.
"@
        implemented_by = @("AzureFrontDoor", "NetworkSecurityGroups")
        parameters = @{ }
    },

    @{
        id = "SC-12"
        title = "Cryptographic Key Establishment and Management"
        narrative = @"
{{ organization.name }} establishes and manages cryptographic keys using approved cryptographic modules.

**Key Management**
Cryptographic keys are generated, distributed, stored, and destroyed using FIPS 140-3 validated modules.

**Certificate Management**
Digital certificates are managed through an enterprise PKI with automated renewal and revocation processes.
"@
        implemented_by = @("KeyVault", "AzureAD")
        parameters = @{ }
    },

    @{
        id = "SI-2"
        title = "Flaw Remediation"
        narrative = @"
{{ organization.name }} identifies, reports, and corrects information system flaws in a timely manner.

**Vulnerability Management**
Automated vulnerability scanning is performed weekly on all systems, with critical findings remediated within {{ parameters.critical-remediation-window }}.

**Patch Management**
Security patches are applied through automated processes with testing in a non-production environment prior to deployment.
"@
        implemented_by = @("MicrosoftDefenderForCloud", "AzureUpdateManagement")
        parameters = @{ "critical-remediation-window" = "48 hours" }
    }
)

foreach ($c in $controls) {
    $yaml = "control-id: $($c.id)`n"
    $yaml += "title: $($c.title)`n"
    $yaml += "narrative: |`n$($c.narrative)`n"
    $yaml += "implemented-by:`n"
    foreach ($comp in $c.implemented_by) {
        $yaml += "  - $comp`n"
    }
    $yaml += "status: implemented`n"
    if ($c.parameters.Count -gt 0) {
        $yaml += "parameters:`n"
        foreach ($key in $c.parameters.Keys) {
            $yaml += "  $($key): `"$($c.parameters[$key])`"`n"
        }
    }
    $yaml += "evidence:`n  - type: audit-log`n    ref: $($c.id)-logs`n"
    $yaml += "related_controls:`n  - AC-2`n  - AC-3`n"

    $file = "$path\$($c.id).yml"
    Set-Content -Path $file -Value $yaml -Encoding UTF8
    Write-Host "Created: $($c.id).yml" -ForegroundColor Green
}

Write-Host "`nBatch 1 complete. Committing and pushing..." -ForegroundColor Cyan

git add data/control-library/
git commit -m "feat(control-library): add Batch 1 of 15 Gold Standard control narratives"
git push

Write-Host "`n✅ Batch 1 pushed to GitHub." -ForegroundColor Green